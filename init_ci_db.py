import duckdb
import os

# Paths matching backend/db.py
DATA_DIR = "data"
DB_FILE = "mexico_city.duckdb"
PARQUET_FILE = "mexico_city.cleaned.3857.geoparquet"

db_path = os.path.join(DATA_DIR, DB_FILE)
parquet_path = os.path.join(DATA_DIR, PARQUET_FILE)

print(f"Initializing CI database at {db_path}...")
print(f"Reading from {parquet_path}...")

con = duckdb.connect(db_path)
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

con.execute(f"CREATE OR REPLACE TABLE mexico_city AS SELECT * FROM read_parquet('{parquet_path}');")
con.execute("CREATE INDEX IF NOT EXISTS idx_geometry ON mexico_city USING RTREE (geometry);")

print("Database initialized successfully.")
con.close()
