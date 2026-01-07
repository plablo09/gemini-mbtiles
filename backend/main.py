from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
from starlette.middleware.gzip import GZipMiddleware # Import GZipMiddleware
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

app.add_middleware(GZipMiddleware, minimum_size=1000) # Add GZipMiddleware

# --- Constants ---
# The name of the layer in the MVT tile
LAYER_NAME = "cadastre"
# The minimum and maximum zoom levels this server will generate tiles for
MIN_ZOOM = 8
MAX_ZOOM = 22 # A high value to allow deep zooming

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

    db_con = get_db_connection()

    try:
        # The core MVT generation query
        # This query follows the pattern described in GeneralSpecs.md
        query = f"""
            WITH
            bounds_geom AS (
                -- 1. Calculate the tile envelope as a GEOMETRY
                SELECT ST_TileEnvelope({z}, {x}, {y}) AS geom
            ),
            bounds_box AS (
                -- 2. Manually create a BOX_2D from the envelope's coordinates
                --    This is the crucial step to ensure the correct type is passed to ST_AsMVTGeom
                SELECT ST_MakeBox2D(
                    ST_Point(ST_XMin(geom), ST_YMin(geom)),
                    ST_Point(ST_XMax(geom), ST_YMax(geom))
                ) AS box
                FROM bounds_geom
            ),
            features AS (
                -- 3. Select features that intersect with the tile envelope
                SELECT
                    t.gid,
                    t.clave,
                    t.uso_suelo,
                    -- 4. Use the full ST_AsMVTGeom signature for robustness, passing the BOX_2D
                    ST_AsMVTGeom(
                        ST_Transform(t.geometry, 'EPSG:4326', 'EPSG:3857'), -- Project to Web Mercator
                        (SELECT box FROM bounds_box), -- Pass the pre-calculated BOX_2D
                        4096, -- Extent
                        256,  -- Buffer
                        true  -- Clip Geom
                    ) AS mvt_geom
                FROM {TABLE_NAME} t, bounds_geom
                WHERE ST_Intersects(ST_Transform(t.geometry, 'EPSG:4326', 'EPSG:3857'), bounds_geom.geom)
            )
            -- 5. Aggregate the clipped geometries into a single MVT layer
            SELECT ST_AsMVT(sub, '{LAYER_NAME}')
            FROM (
                SELECT gid, clave, uso_suelo, mvt_geom FROM features
            ) AS sub
            WHERE mvt_geom IS NOT NULL;
        """

        # Execute the query
        result = db_con.execute(query).fetchone()
        
        if not result or not result[0]:
            # If no features are in this tile, return an empty response with a 204 status
            return Response(status_code=204)

        # The result is a bytes object containing the MVT data (not gzipped by DuckDB)
        raw_tile_data = result[0]
        
        # FastAPI's GZipMiddleware will handle the gzipping and Content-Encoding header
        return Response(
            content=raw_tile_data,
            media_type="application/vnd.mapbox-vector-tile"
            # No manual Content-Encoding: gzip header here, GZipMiddleware handles it
        )

    except Exception as e:
        # Log the error and return an internal server error
        print(f"Error generating tile for z={z}, x={x}, y={y}: {e}")
        return Response(status_code=500, content=f"An internal error occurred: {e}")