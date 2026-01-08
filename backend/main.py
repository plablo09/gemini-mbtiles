from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.gzip import GZipMiddleware # Import GZipMiddleware
from functools import lru_cache
from typing import Optional
from .db import init_db, close_db, get_db_connection, TABLE_NAME

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
def generate_tile_content(z: int, x: int, y: int) -> Optional[bytes]:
    """
    Cached function to generate MVT data.
    """
    db_con = get_db_connection()
    simplification_tolerance = get_simplification_tolerance(z)

    try:
        # The core MVT generation query
        # We removed the area filter to ensure full coverage
        query = f"""
            WITH
            bounds_box AS (
                -- 1. Use Web Mercator tile bounds (EPSG:3857)
                -- We compute both the geometry (for intersection) and the box (for MVT encoding)
                SELECT
                    ST_TileEnvelope({z}, {x}, {y}) AS geom,
                    ST_Extent(ST_TileEnvelope({z}, {x}, {y})) AS box
            ),
            features AS (
                -- 2. Select features that intersect with the tile bounds
                SELECT
                    t.gid,
                    t.clave,
                    t.uso_suelo,
                    -- 3. Use the full ST_AsMVTGeom signature for robustness
                    ST_AsMVTGeom(
                        ST_Simplify(t.geometry, {simplification_tolerance}),
                        (SELECT box FROM bounds_box),
                        4096, -- Extent
                        256,  -- Buffer
                        true  -- Clip Geom
                    ) AS mvt_geom
                FROM {TABLE_NAME} t, bounds_box
                WHERE ST_Intersects(t.geometry, bounds_box.geom)
            )
            -- 5. Aggregate the clipped geometries into a single MVT layer
            SELECT
                CASE
                    WHEN COUNT(*) = 0 THEN NULL
                    ELSE ST_AsMVT(sub, '{LAYER_NAME}')
                END AS tile
            FROM (
                SELECT gid, clave, uso_suelo, mvt_geom FROM features
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

@app.get("/")
def read_root():
    """Returns a welcome message."""
    return {"message": "Welcome to the Mexico City Cadastral Map Tile Server!"}

@app.get("/health")
def health_check():
    """
    Performs a health check on the database connection and returns the status.
    """
    try:
        # A simple check to ensure the connection is alive and can execute a query
        con = get_db_connection()
        con.execute("SELECT 1;").fetchone()
        return {"status": "ok", "message": "Database connection is healthy."}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {e}"}

@app.get("/tiles/{z}/{x}/{y}.pbf", response_class=Response)
def get_tile(z: int, x: int, y: int):
    """
    Generates and returns a Mapbox Vector Tile (MVT) for the given zoom, x, and y coordinates.
    """
    if not (MIN_ZOOM <= z <= MAX_ZOOM):
        return Response(status_code=404, content=f"Zoom level {z} is outside the supported range [{MIN_ZOOM}, {MAX_ZOOM}].")

    raw_tile_data = generate_tile_content(z, x, y)
    
    if raw_tile_data is None:
         # If no features are in this tile, return an empty response with a 204 status
        return Response(status_code=204)

    # FastAPI's GZipMiddleware will handle the gzipping and Content-Encoding header
    return Response(
        content=raw_tile_data,
        media_type="application/vnd.mapbox-vector-tile"
        # No manual Content-Encoding: gzip header here, GZipMiddleware handles it
    )
