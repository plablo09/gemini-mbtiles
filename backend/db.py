import duckdb
import os

# --- Constants ---
# Use an in-memory database for this example
# For production, you might want to use a file-backed database
DB_PATH = ":memory:"
GEOPARQUET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mexico_city.geoparquet")
TABLE_NAME = "mexico_city"

# --- Database Connection ---
# A global connection object that will be initialized at startup
con: duckdb.DuckDBPyConnection = None

def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Returns the application-wide DuckDB connection."""
    global con
    if con is None:
        raise RuntimeError("Database connection has not been initialized. Call init_db() at application startup.")
    return con

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


def init_db():
    """
    Initializes the DuckDB connection, loads the spatial extension,
    creates the table from the GeoParquet file, and performs sanity checks.
    This function should be called once at application startup.
    """
    global con
    
    print("Initializing database connection...")
    con = duckdb.connect(database=DB_PATH, read_only=False)
    
    # Install and load the spatial extension
    print("Installing and loading spatial extension...")
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    
    # Perform sanity checks *after* loading the extension
    _perform_sanity_checks(con)

    # Load data from GeoParquet file
    print(f"Loading data from {GEOPARQUET_PATH} into table '{TABLE_NAME}'...")
    if not os.path.exists(GEOPARQUET_PATH):
        raise FileNotFoundError(f"GeoParquet file not found at: {GEOPARQUET_PATH}. Please run prepare_data.py first.")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE {TABLE_NAME} AS
        SELECT * FROM read_parquet('{GEOPARQUET_PATH}');
    """)
    
    # Verify data loading
    count = con.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};").fetchone()[0]
    print(f"Successfully loaded {count} features into '{TABLE_NAME}'.")
    
    print("Database initialization complete.")

def close_db():
    """Closes the database connection. Should be called at application shutdown."""
    global con
    if con:
        print("Closing database connection...")
        con.close()
        con = None
