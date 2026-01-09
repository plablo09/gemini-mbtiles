from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.gzip import GZipMiddleware # Import GZipMiddleware
from functools import lru_cache
import os
from typing import Optional
from .db import init_db, close_db, db_connection, TABLE_NAME

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    print("Starting up the application...")
    init_db()
    yield
    # Shutdown event
    print("Shutting down the application...")
    close_db()

app = FastAPI(
    title="Mexico City Cadastral Map Tile Server",
    lifespan=lifespan,
    description="Serves vector tiles of the Mexico City cadastral map.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000) # Add GZipMiddleware

# --- Constants ---
# The name of the layer in the MVT tile
LAYER_NAME = "cadastre_layer"
# The minimum and maximum zoom levels this server will generate tiles for
MIN_ZOOM = 14
MAX_ZOOM = 18 # Matches frontend maxzoom
# Cache version used to bust the in-process tile cache when schema changes
CACHE_VERSION = os.getenv("TILE_CACHE_VERSION", "1")

def get_simplification_tolerance(z: int):
    """
    Returns the simplification tolerance based on the zoom level.
    """
    # Earth circumference in meters (Web Mercator)
    circumference = 40075016.68
    tile_size = 256
    
    # Resolution in meters per pixel
    resolution = circumference / (tile_size * (2 ** z))
    
    # Simplification tolerance: 0.5 pixel
    return resolution * 0.5

@lru_cache(maxsize=2048)
def generate_tile_content(z: int, x: int, y: int, cache_version: str) -> Optional[bytes]:
    """
    Cached function to generate MVT data.
    """
    simplification_tolerance = get_simplification_tolerance(z)

    try:
        with db_connection() as db_con:
            # The core MVT generation query
            # We removed the area filter to ensure full coverage
            query = f"""
                WITH
                bounds_box AS (
                    -- 1. Use Web Mercator tile bounds (EPSG:3857)
                    -- Compute a Box2D for MVT encoding; keep the intersects predicate inline to hit RTREE.
                    SELECT
                        ST_Extent(ST_TileEnvelope({z}, {x}, {y})) AS box
                ),
                features AS (
                    -- 2. Select features that intersect with the tile bounds
                    SELECT
                        t.gid,
                        t.clave,
                        t.uso_suelo,
                        COALESCE(CAST(t.no_niveles AS INTEGER), 0) AS no_niveles, -- Force non-null
                        -- 3. Use the full ST_AsMVTGeom signature for robustness
                        ST_AsMVTGeom(
                            ST_Simplify(t.geometry, {simplification_tolerance}),
                            (SELECT box FROM bounds_box),
                            4096, -- Extent
                            256,  -- Buffer
                            true  -- Clip Geom
                        ) AS mvt_geom
                    FROM {TABLE_NAME} t
                    WHERE ST_Intersects(t.geometry, ST_TileEnvelope({z}, {x}, {y}))
                )
                -- 5. Aggregate the clipped geometries into a single MVT layer
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN NULL
                        ELSE ST_AsMVT(sub, '{LAYER_NAME}')
                    END AS tile
                FROM (
                    SELECT gid, clave, uso_suelo, no_niveles, mvt_geom FROM features
                    WHERE mvt_geom IS NOT NULL
                ) AS sub;
            """

            # Execute the query
            result = db_con.execute(query).fetchone()
        
        if not result or not result[0]:
            return None

        return result[0]

    except Exception as e:
        print(f"Error generating tile for z={z}, x={x}, y={y}: {e}")
        return None

@app.get("/health")
def health_check():
    """
    Performs a health check on the database connection and returns the status.
    """
    try:
        # A simple check to ensure a pooled connection is alive and can execute a query
        with db_connection() as con:
            con.execute("SELECT 1;").fetchone()
        return {"status": "ok", "message": "Database connection is healthy."}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {e}"}

@app.get("/tiles/{z}/{x}/{y}.pbf", response_class=Response)
def get_tile(z: int, x: int, y: int, v: Optional[str] = None):
    """
    Generates and returns a Mapbox Vector Tile (MVT) for the given zoom, x, and y coordinates.
    """
    cache_version = v or CACHE_VERSION
    headers = {
        "X-Tile-Cache-Version": cache_version,
        "X-Tile-Cache-Key": f"{z}/{x}/{y}/{cache_version}",
        "X-Tile-Server": "fastapi",
    }

    if not (MIN_ZOOM <= z <= MAX_ZOOM):
        return Response(
            status_code=404,
            content=f"Zoom level {z} is outside the supported range [{MIN_ZOOM}, {MAX_ZOOM}].",
            headers=headers,
        )

    raw_tile_data = generate_tile_content(z, x, y, cache_version)
    
    if raw_tile_data is None:
         # If no features are in this tile, return an empty response with a 204 status
        return Response(status_code=204, headers=headers)

    # Add Cache-Control header
    # We cache tiles for 1 day (86400 seconds) because they are static
    headers["Cache-Control"] = "public, max-age=86400"

    # FastAPI's GZipMiddleware will handle the gzipping and Content-Encoding header
    return Response(
        content=raw_tile_data,
        media_type="application/vnd.mapbox-vector-tile",
        headers=headers,
        # No manual Content-Encoding: gzip header here, GZipMiddleware handles it
    )

# Mount the frontend directory to serve static files
# We mount this last so that specific API routes defined above (like /tiles and /health) take precedence.
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
