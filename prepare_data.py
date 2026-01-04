import geopandas as gpd
import os

# Define the input and output file paths relative to the script location
DATA_DIR = "data"
# The zip extraction created a subdirectory, so we point to it
INPUT_SUBDIR = "CATASTRO"
SHAPEFILE_NAME = "catastro_cdmx.shp"
OUTPUT_PARQUET_FILE = "mexico_city.geoparquet"

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

    # Write the GeoDataFrame to a GeoParquet file
    print(f"Writing data to: {output_parquet_path}")
    gdf.to_parquet(output_parquet_path)

    print("\nConversion successful!")
    print(f"Output file created at: {output_parquet_path}")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please check the following:")
    print(f"1. Ensure the file '{input_shapefile_path}' exists.")
