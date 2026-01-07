import geopandas as gpd
from shapely import make_valid
import os

# Define the input and output file paths relative to the script location
DATA_DIR = "data"
# The zip extraction created a subdirectory, so we point to it
INPUT_SUBDIR = "CATASTRO"
SHAPEFILE_NAME = "catastro_cdmx.shp"
OUTPUT_PARQUET_FILE = "mexico_city.cleaned.3857.geoparquet"

# Construct full paths
input_shapefile_path = os.path.join(DATA_DIR, INPUT_SUBDIR, SHAPEFILE_NAME)
output_parquet_path = os.path.join(DATA_DIR, OUTPUT_PARQUET_FILE)

print(f"Reading shapefile from: {input_shapefile_path}")

try:
    # Read the shapefile directly
    gdf = gpd.read_file(input_shapefile_path)

    print(f"Successfully read {len(gdf)} features.")
    print("Columns found:", gdf.columns.tolist())
    print("CRS:", gdf.crs)

    # Fix invalid geometries once before writing output
    gdf["geometry"] = gdf["geometry"].apply(
        lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
    )

    # Reproject to Web Mercator for tile serving
    gdf = gdf.to_crs("EPSG:3857")
    # Reprojection can introduce minor topology issues; repair again
    gdf["geometry"] = gdf["geometry"].apply(
        lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
    )

    # Write the GeoDataFrame to a GeoParquet file
    print(f"Writing data to: {output_parquet_path}")
    gdf.to_parquet(output_parquet_path)

    print("\nConversion successful!")
    print(f"Output file created at: {output_parquet_path}")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please check the following:")
    print(f"1. Ensure the file '{input_shapefile_path}' exists.")
