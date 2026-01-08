import duckdb
import math
import os
import time

# Define the path to the GeoParquet file
GEOPARQUET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "mexico_city.cleaned.3857.geoparquet"))
TABLE_NAME = "mexico_city"
SAMPLE_ZOOMS = [14, 16, 18]
SAMPLE_TILES = 3
RANDOM_SEED = 0.42
LAYER_NAME = "cadastre_layer"

WEB_MERCATOR_HALF_WORLD = 20037508.342789244

def mercator_to_tile(x: float, y: float, z: int):
    n = 2 ** z
    tile_x = int((x + WEB_MERCATOR_HALF_WORLD) / (2 * WEB_MERCATOR_HALF_WORLD) * n)
    tile_y = int((WEB_MERCATOR_HALF_WORLD - y) / (2 * WEB_MERCATOR_HALF_WORLD) * n)
    return tile_x, tile_y

def get_simplification_tolerance(z: int):
    circumference = 40075016.68
    tile_size = 256
    resolution = circumference / (tile_size * (2 ** z))
    return resolution * 0.5

def explain_tile_query(conn: duckdb.DuckDBPyConnection, z: int, x: int, y: int):
    variants = [
        (
            "cte_intersects",
            f"""
                EXPLAIN ANALYZE
                WITH bounds_box AS (
                    SELECT ST_TileEnvelope({z}, {x}, {y}) AS geom
                )
                SELECT t.gid
                FROM {TABLE_NAME} t, bounds_box
                WHERE ST_Intersects(t.geometry, bounds_box.geom);
            """
        ),
        (
            "inline_intersects",
            f"""
                EXPLAIN ANALYZE
                SELECT t.gid
                FROM {TABLE_NAME} t
                WHERE ST_Intersects(t.geometry, ST_TileEnvelope({z}, {x}, {y}));
            """
        ),
        (
            "swap_intersects",
            f"""
                EXPLAIN ANALYZE
                WITH bounds_box AS (
                    SELECT ST_TileEnvelope({z}, {x}, {y}) AS geom
                )
                SELECT t.gid
                FROM {TABLE_NAME} t, bounds_box
                WHERE ST_Intersects(bounds_box.geom, t.geometry);
            """
        ),
    ]

    print(f"\n--- EXPLAIN ANALYZE z={z} x={x} y={y} ---")
    for label, explain_query in variants:
        print(f"\nVariant: {label}")
        for row in conn.execute(explain_query).fetchall():
            if len(row) == 2:
                print(f"{row[0]}:\n{row[1]}")
            else:
                print(row)

def time_tile_query(conn: duckdb.DuckDBPyConnection, z: int, x: int, y: int, use_simplify: bool):
    simplification_tolerance = get_simplification_tolerance(z)
    geom_expr = "t.geometry"
    if use_simplify:
        geom_expr = f"ST_Simplify(t.geometry, {simplification_tolerance})"
    queries = [
        (
            "full_cte_intersects",
            f"""
                WITH
                bounds_box AS (
                    SELECT
                        ST_TileEnvelope({z}, {x}, {y}) AS geom,
                        ST_Extent(ST_TileEnvelope({z}, {x}, {y})) AS box
                ),
                features AS (
                    SELECT
                        t.gid,
                        t.clave,
                        t.uso_suelo,
                        ST_AsMVTGeom(
                            {geom_expr},
                            (SELECT box FROM bounds_box),
                            4096,
                            256,
                            true
                        ) AS mvt_geom
                    FROM {TABLE_NAME} t, bounds_box
                    WHERE ST_Intersects(t.geometry, bounds_box.geom)
                )
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN NULL
                        ELSE ST_AsMVT(sub, '{LAYER_NAME}')
                    END AS tile
                FROM (
                    SELECT gid, clave, uso_suelo, mvt_geom FROM features
                    WHERE mvt_geom IS NOT NULL
                ) AS sub;
            """
        ),
        (
            "full_inline_intersects",
            f"""
                WITH
                bounds_box AS (
                    SELECT
                        ST_TileEnvelope({z}, {x}, {y}) AS geom,
                        ST_Extent(ST_TileEnvelope({z}, {x}, {y})) AS box
                ),
                features AS (
                    SELECT
                        t.gid,
                        t.clave,
                        t.uso_suelo,
                        ST_AsMVTGeom(
                            {geom_expr},
                            (SELECT box FROM bounds_box),
                            4096,
                            256,
                            true
                        ) AS mvt_geom
                    FROM {TABLE_NAME} t
                    WHERE ST_Intersects(t.geometry, ST_TileEnvelope({z}, {x}, {y}))
                )
                SELECT
                    CASE
                        WHEN COUNT(*) = 0 THEN NULL
                        ELSE ST_AsMVT(sub, '{LAYER_NAME}')
                    END AS tile
                FROM (
                    SELECT gid, clave, uso_suelo, mvt_geom FROM features
                    WHERE mvt_geom IS NOT NULL
                ) AS sub;
            """
        ),
    ]

    simplify_label = "simplify_on" if use_simplify else "simplify_off"
    print(f"\n--- TIMINGS z={z} x={x} y={y} {simplify_label} ---")
    for label, query in queries:
        start = time.perf_counter()
        conn.execute(query).fetchone()
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"{label}: {elapsed_ms:.2f} ms")

def breakdown_tile_query(conn: duckdb.DuckDBPyConnection, z: int, x: int, y: int, use_simplify: bool):
    simplification_tolerance = get_simplification_tolerance(z)
    geom_expr = "t.geometry"
    if use_simplify:
        geom_expr = f"ST_Simplify(t.geometry, {simplification_tolerance})"

    simplify_label = "simplify_on" if use_simplify else "simplify_off"
    print(f"\n--- BREAKDOWN z={z} x={x} y={y} {simplify_label} ---")

    intersect_query = f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME} t
        WHERE ST_Intersects(t.geometry, ST_TileEnvelope({z}, {x}, {y}));
    """
    start = time.perf_counter()
    intersect_count = conn.execute(intersect_query).fetchone()[0]
    intersect_ms = (time.perf_counter() - start) * 1000
    print(f"intersect_count: {intersect_count} ({intersect_ms:.2f} ms)")

    temp_table_name = f"temp_mvt_geom_{z}_{x}_{y}_{'s' if use_simplify else 'r'}"
    create_mvt_geom_query = f"""
        CREATE TEMP TABLE {temp_table_name} AS
        WITH bounds_box AS (
            SELECT ST_Extent(ST_TileEnvelope({z}, {x}, {y})) AS box
        )
        SELECT
            t.gid,
            t.clave,
            t.uso_suelo,
            ST_AsMVTGeom(
                {geom_expr},
                (SELECT box FROM bounds_box),
                4096,
                256,
                true
            ) AS mvt_geom
        FROM {TABLE_NAME} t
        WHERE ST_Intersects(t.geometry, ST_TileEnvelope({z}, {x}, {y}))
          AND ST_AsMVTGeom(
                {geom_expr},
                (SELECT box FROM bounds_box),
                4096,
                256,
                true
            ) IS NOT NULL;
    """
    start = time.perf_counter()
    conn.execute(create_mvt_geom_query)
    mvt_geom_ms = (time.perf_counter() - start) * 1000
    mvt_geom_count = conn.execute(f"SELECT COUNT(*) FROM {temp_table_name};").fetchone()[0]
    print(f"mvt_geom_count: {mvt_geom_count} ({mvt_geom_ms:.2f} ms)")

    mvt_encode_query = f"""
        SELECT
            CASE
                WHEN COUNT(*) = 0 THEN NULL
                ELSE ST_AsMVT(sub, '{LAYER_NAME}')
            END AS tile
        FROM (
            SELECT gid, clave, uso_suelo, mvt_geom FROM {temp_table_name}
        ) AS sub;
    """
    start = time.perf_counter()
    conn.execute(mvt_encode_query).fetchone()
    mvt_encode_ms = (time.perf_counter() - start) * 1000
    print(f"mvt_encode_time: {mvt_encode_ms:.2f} ms")

    conn.execute(f"DROP TABLE {temp_table_name};")

print(f"Testing DuckDB with GeoParquet file: {GEOPARQUET_PATH}")

try:
    with duckdb.connect(database=':memory:') as conn:
        print("Connected to DuckDB.")

        print("Installing spatial extension...")
        conn.execute("INSTALL spatial;")
        print("Loading spatial extension...")
        conn.execute("LOAD spatial;")
        print("Spatial extension loaded.")

        print(f"\nLoading data into table '{TABLE_NAME}'...")
        conn.execute(f"CREATE TABLE {TABLE_NAME} AS SELECT * FROM read_parquet('{GEOPARQUET_PATH}');")
        conn.execute(f"CREATE INDEX idx_geometry ON {TABLE_NAME} USING RTREE (geometry);")

        # Test 1: Count features in the table
        print(f"\nAttempting to count features from: {TABLE_NAME}")
        count_query = f"SELECT count(*) FROM {TABLE_NAME};"
        count_result = conn.execute(count_query).fetchone()[0]
        print(f"Result (count): {count_result} features.")

        if count_result == 0:
            print("WARNING: Count is 0. Data might be empty or file path is wrong.")

        # Test 2: Get geometry type of a feature
        print(f"\nAttempting to get geometry type from: {TABLE_NAME}")
        geom_type_query = f"SELECT ST_GeometryType(geometry) FROM {TABLE_NAME} LIMIT 1;"
        geom_type_result = conn.execute(geom_type_query).fetchone()[0]
        print(f"Result (first geometry type): {geom_type_result}")

        # Test 3: EXPLAIN ANALYZE for sample tiles
        conn.execute(f"SELECT setseed({RANDOM_SEED});")
        sample_points = conn.execute(
            f"""
                SELECT
                    ST_X(ST_Centroid(geometry)) AS x,
                    ST_Y(ST_Centroid(geometry)) AS y
                FROM {TABLE_NAME}
                ORDER BY random()
                LIMIT {SAMPLE_TILES};
            """
        ).fetchall()

        if sample_points:
            for idx, (sample_x, sample_y) in enumerate(sample_points, start=1):
                print(f"\n=== SAMPLE TILE {idx}/{SAMPLE_TILES} ===")
                for zoom in SAMPLE_ZOOMS:
                    tile_x, tile_y = mercator_to_tile(sample_x, sample_y, zoom)
                    explain_tile_query(conn, zoom, tile_x, tile_y)
                    breakdown_tile_query(conn, zoom, tile_x, tile_y, use_simplify=True)
                    breakdown_tile_query(conn, zoom, tile_x, tile_y, use_simplify=False)
                    time_tile_query(conn, zoom, tile_x, tile_y, use_simplify=True)
                    time_tile_query(conn, zoom, tile_x, tile_y, use_simplify=False)
        else:
            print("\nWARNING: Could not find sample geometries to derive tile coordinates.")

        print("\nDuckDB tests completed successfully.")

except Exception as e:
    print(f"\nAn error occurred during DuckDB testing: {e}")
