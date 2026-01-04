from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import duckdb
import os
import math

app = FastAPI()

# Allow CORS for local development (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define the path to your GeoParquet file
# The path is relative to where the backend app is run from (backend/ directory)
# So, from backend/, ../data/mexico_city.geoparquet
GEOPARQUET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mexico_city.geoparquet")
GEOPARQUET_PATH = os.path.abspath(GEOPARQUET_PATH) # Ensure absolute path

# Initialize DuckDB connection
# We'll use a in-memory database for connection, as we are reading external file
# Using a context manager for each request ensures connection is closed properly
def get_duckdb_conn():
    conn = duckdb.connect(database=':memory:')
    conn.execute("INSTALL spatial;")
    conn.execute("LOAD spatial;")
    return conn

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Mexico City Cadastral Tile Server!"}

@app.get("/tiles/{z}/{x}/{y}.pbf")
async def get_vector_tile(z: int, x: int, y: int):
    """
    Serves Mapbox Vector Tiles (MVT) for the cadastral data.
    """
    if not (0 <= z <= 20 and 0 <= x < (1 << z) and 0 <= y < (1 << z)):
        raise HTTPException(status_code=400, detail="Invalid tile coordinates")

    try:
        with get_duckdb_conn() as conn:
            # Construct the SQL query to generate the MVT
            # ST_TileEnvelope(z, x, y) generates the bounding box for the tile in Web Mercator (EPSG:3857)
            # ST_AsMVTGeom clips and transforms geometries to the tile's grid
            # ST_AsMVT encodes the results into a vector tile
            
            # The 'geom' column is assumed to be in EPSG:4326 (WGS84) from the GeoParquet
            # We need to transform it to EPSG:3857 for ST_AsMVTGeom to work correctly
            
            # Note: The spatial index (if any) in the GeoParquet is crucial for performance.
            # DuckDB automatically uses it if present.

            query = f"""
            SELECT ST_AsMVT(
                (SELECT
                    -- Select all attributes you want to include in the tile
                    -- and transform geometry
                    *,
                    ST_AsMVTGeom(
                        ST_Transform(geometry, 'EPSG:4326', 'EPSG:3857'), -- Transform to Web Mercator
                        ST_TileEnvelope({z}, {x}, {y}),
                        4096, -- Tile extent (usually 4096)
                        256,  -- Buffer (usually 256 or 0)
                        true  -- Clip geometries
                    ) AS geometry -- Rename to 'geometry' for MVT convention
                FROM '{GEOPARQUET_PATH}'
                WHERE
                    -- Filter geometries that intersect with the tile's bounding box (in EPSG:4326)
                    ST_Intersects(geometry, ST_Transform(ST_TileEnvelope({z}, {x}, {y}), 'EPSG:3857', 'EPSG:4326'))
                ), 'cadastre_layer', 4096, 'geometry'
            ) AS mvt;
            """
            
            result = conn.execute(query).fetchval()
            
            if result is None:
                # Return an empty PBF if no features are found for the tile
                # This is standard behavior for empty vector tiles
                return Response(content=b'', media_type="application/vnd.mapbox-vector-tile")

            return Response(content=result, media_type="application/vnd.mapbox-vector-tile")

    except Exception as e:
        print(f"Error serving tile {z}/{x}/{y}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing tile: {e}")

