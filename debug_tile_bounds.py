import duckdb
import os

def check_tile_bounds():
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL spatial; LOAD spatial;")
    
    # Path to data
    geoparquet_path = "data/mexico_city.cleaned.3857.geoparquet"
    if not os.path.exists(geoparquet_path):
        print(f"File not found: {geoparquet_path}")
        return

    # Load data
    con.execute(f"CREATE TABLE mexico_city AS SELECT * FROM read_parquet('{geoparquet_path}');")
    
    # Get Data Extent
    data_extent = con.execute("SELECT ST_Extent(geometry) FROM mexico_city").fetchone()[0]
    print(f"Data Extent: {data_extent}")
    
    # Test tile: z=10, x=229, y=456 (Standard XYZ for Mexico City center roughly)
    z, x, y = 10, 229, 456
    print(f"\nChecking bounds for Tile(z={z}, x={x}, y={y})")
    
    # Get the envelope from DuckDB
    tile_env = con.execute(f"SELECT ST_AsText(ST_TileEnvelope({z}, {x}, {y}))").fetchone()[0]
    tile_box = con.execute(f"SELECT ST_Extent(ST_TileEnvelope({z}, {x}, {y}))").fetchone()[0]
    print(f"DuckDB ST_TileEnvelope: {tile_env}")
    print(f"DuckDB ST_Extent: {tile_box}")
    
    # Check intersection count without any simplification/filtering
    count = con.execute(f"""
        SELECT COUNT(*) 
        FROM mexico_city 
        WHERE ST_Intersects(geometry, ST_TileEnvelope({z}, {x}, {y}))
    """).fetchone()[0]
    print(f"\nFeatures intersecting this tile (raw): {count}")
    
    # Check with filter
    # Calculate resolution for z=10
    circumference = 40075016.68
    tile_size = 256
    resolution = circumference / (tile_size * (2 ** z))
    min_area = (resolution * 2) ** 2
    print(f"Resolution at z={z}: {resolution:.2f} m/px")
    print(f"Min Area Filter: {min_area:.2f} sq meters")
    
    count_filtered = con.execute(f"""
        SELECT COUNT(*) 
        FROM mexico_city 
        WHERE ST_Intersects(geometry, ST_TileEnvelope({z}, {x}, {y}))
          AND ST_Area(geometry) > {min_area}
    """).fetchone()[0]
    print(f"Features intersecting this tile (filtered): {count_filtered}")

if __name__ == "__main__":
    check_tile_bounds()
