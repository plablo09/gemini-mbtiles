import geopandas as gpd
from shapely.geometry import Polygon
import os

# Define the output path to match what the backend expects
DATA_DIR = "data"
OUTPUT_PARQUET_FILE = "mexico_city.cleaned.3857.geoparquet"
output_parquet_path = os.path.join(DATA_DIR, OUTPUT_PARQUET_FILE)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

print("Creating synthetic test data...")

# Create a simple square polygon in Web Mercator (EPSG:3857)
# Coordinates roughly corresponding to Mexico City center in 3857
# Mexico City center is roughly -99.1332, 19.4326 (WGS84)
# In 3857: -11035000, 2205000
p1 = Polygon([
    (-11036000, 2204000),
    (-11034000, 2204000),
    (-11034000, 2206000),
    (-11036000, 2206000),
    (-11036000, 2204000)
])

# Create a GeoDataFrame
# We include 'gid', 'clave', and 'uso_suelo' because the backend query explicitly selects them.
gdf = gpd.GeoDataFrame(
    {
        'gid': [1], 
        'clave': ['TEST-CLAVE-001'],
        'uso_suelo': ['H/3/30'],
        'geometry': [p1]
    },
    crs="EPSG:3857"
)

print(f"Created GeoDataFrame with {len(gdf)} feature(s).")
print(f"CRS: {gdf.crs}")

# Write to GeoParquet
print(f"Writing to {output_parquet_path}...")
gdf.to_parquet(output_parquet_path)

print("Test data creation successful!")
