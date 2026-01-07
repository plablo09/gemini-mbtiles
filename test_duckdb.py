import duckdb
import os

# Define the path to the GeoParquet file
GEOPARQUET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "mexico_city.cleaned.3857.geoparquet"))

print(f"Testing DuckDB with GeoParquet file: {GEOPARQUET_PATH}")

try:
    with duckdb.connect(database=':memory:') as conn:
        print("Connected to DuckDB.")
        
        print("Installing spatial extension...")
        conn.execute("INSTALL spatial;")
        print("Loading spatial extension...")
        conn.execute("LOAD spatial;")
        print("Spatial extension loaded.")
        
        # Test 1: Count features in the GeoParquet file
        print(f"\nAttempting to count features from: read_parquet('{GEOPARQUET_PATH}')")
        count_query = f"SELECT count(*) FROM read_parquet('{GEOPARQUET_PATH}');"
        count_result = conn.execute(count_query).fetchone()[0]
        print(f"Result (count): {count_result} features.")
        
        if count_result == 0:
            print("WARNING: Count is 0. Data might be empty or file path is wrong.")

        # Test 2: Get geometry type of a feature
        print(f"\nAttempting to get geometry type from: read_parquet('{GEOPARQUET_PATH}')")
        geom_type_query = f"SELECT ST_GeometryType(geometry) FROM read_parquet('{GEOPARQUET_PATH}') LIMIT 1;"
        geom_type_result = conn.execute(geom_type_query).fetchone()[0]
        print(f"Result (first geometry type): {geom_type_result}")

        print("\nDuckDB tests completed successfully.")

except Exception as e:
    print(f"\nAn error occurred during DuckDB testing: {e}")
