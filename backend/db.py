import duckdb
import os
import queue
from contextlib import contextmanager

# --- Constants ---
# Use a file-backed database so multiple connections share the same data
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mexico_city.duckdb")
GEOPARQUET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mexico_city.cleaned.3857.geoparquet")
TABLE_NAME = "mexico_city"
POOL_SIZE = 4

# --- Database Connection ---
# A global connection pool initialized at startup
_pool: queue.Queue = None

def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Borrows a DuckDB connection from the pool."""
    global _pool
    if _pool is None:
        raise RuntimeError("Database connection pool has not been initialized. Call init_db() at application startup.")
    return _pool.get()

def release_db_connection(conn: duckdb.DuckDBPyConnection):
    """Returns a DuckDB connection to the pool."""
    global _pool
    if _pool is None:
        raise RuntimeError("Database connection pool has not been initialized. Call init_db() at application startup.")
    _pool.put(conn)

@contextmanager
def db_connection():
    """Context manager for a pooled DuckDB connection."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)

def _perform_sanity_checks(db_con: duckdb.DuckDBPyConnection):
    """
    Performs the startup sanity checks as described in GeneralSpecs.md.
    Raises a RuntimeError if any check fails.
    """
    print("--- Performing database sanity checks ---")
    
    # Level 1: Connection Liveness
    try:
        db_con.execute("SELECT 42;").fetchone()
        print("✅ Level 1: Connection liveness check passed.")
    except Exception as e:
        raise RuntimeError(f"❌ Level 1: Connection liveness check failed: {e}")

    # Level 2 & 3: Spatial Extension Availability and Loaded
    try:
        # This function only exists if the spatial extension is loaded
        db_con.execute("SELECT ST_Point(1, 2);").fetchone()
        print("✅ Level 3: Spatial extension is loaded in this connection.")
    except Exception as e:
        raise RuntimeError(f"❌ Level 3: Spatial extension check failed. Is it installed and loaded? Error: {e}")
        
    # Level 4: Tile Helper Functions
    try:
        # Check if a core tiling function exists
        db_con.execute("SELECT function_name FROM duckdb_functions() WHERE function_name = 'ST_TileEnvelope';").fetchone()
        print("✅ Level 4: Tile helper function (ST_TileEnvelope) is available.")
    except Exception as e:
        raise RuntimeError(f"❌ Level 4: Tile helper function check failed: {e}")

    # Level 5: MVT Encoding Capability
    try:
        # Check for both required MVT functions
        mvt_geom_func = db_con.execute("SELECT function_name FROM duckdb_functions() WHERE function_name = 'ST_AsMVTGeom';").fetchone()
        mvt_func = db_con.execute("SELECT function_name FROM duckdb_functions() WHERE function_name = 'ST_AsMVT';").fetchone()
        if not mvt_geom_func or not mvt_func:
            raise duckdb.InvalidInputException("ST_AsMVTGeom or ST_AsMVT function not found.")
        print("✅ Level 5: MVT encoding functions (ST_AsMVTGeom, ST_AsMVT) are available.")
    except Exception as e:
        raise RuntimeError(f"❌ Level 5: MVT encoding capability check failed: {e}")
        
    print("--- All database sanity checks passed successfully! ---")


def _create_connection() -> duckdb.DuckDBPyConnection:
    """
    Creates a DuckDB connection with spatial extension loaded.
    """
    conn = duckdb.connect(database=DB_PATH, read_only=False)
    conn.execute("INSTALL spatial;")
    conn.execute("LOAD spatial;")
    return conn

def init_db():
    """
    Initializes the DuckDB connection, loads the spatial extension,
    creates the table from the GeoParquet file, and performs sanity checks.
    This function should be called once at application startup.
    """
    global _pool

    print("Initializing database connection...")
    bootstrap_con = _create_connection()

    # Perform sanity checks *after* loading the extension
    _perform_sanity_checks(bootstrap_con)

    # Load data from GeoParquet file
    print(f"Loading data from {GEOPARQUET_PATH} into table '{TABLE_NAME}'...")
    if not os.path.exists(GEOPARQUET_PATH):
        raise FileNotFoundError(f"GeoParquet file not found at: {GEOPARQUET_PATH}. Please run prepare_data.py first.")
    
    bootstrap_con.execute(f"""
        CREATE OR REPLACE TABLE {TABLE_NAME} AS
        SELECT * FROM read_parquet('{GEOPARQUET_PATH}');
    """)

    # Create spatial index
    print("Creating spatial index...")
    bootstrap_con.execute(f"CREATE INDEX IF NOT EXISTS idx_geometry ON {TABLE_NAME} USING RTREE (geometry);")
    
    # Verify data loading
    count = bootstrap_con.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};").fetchone()[0]
    print(f"Successfully loaded {count} features into '{TABLE_NAME}'.")

    print("Database initialization complete.")
    bootstrap_con.close()

    print(f"Creating connection pool with size {POOL_SIZE}...")
    _pool = queue.Queue(maxsize=POOL_SIZE)
    for _ in range(POOL_SIZE):
        conn = _create_connection()
        _perform_sanity_checks(conn)
        _pool.put(conn)

def close_db():
    """Closes the database connection. Should be called at application shutdown."""
    global _pool
    if _pool:
        print("Closing database connection pool...")
        while not _pool.empty():
            conn = _pool.get()
            conn.close()
        _pool = None
