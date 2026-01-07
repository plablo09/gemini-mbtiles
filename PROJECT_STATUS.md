# Project Status: Mexico City Cadastral Map

This document tracks the execution plan, progress, and key technical solutions for this project. Its purpose is to provide context for resuming work in new sessions.

---

## 1. Execution Plan

### Phase 1: Local Development & Core Functionality
-   [x] **Step 1: Project Scaffolding & Version Control**
-   [x] **Step 2: Data Acquisition and Preparation**
-   [~] **Step 3: Backend: The DuckDB Tile Server** (Working with a 4326 fallback; see Troubleshooting)
-   [~] **Step 4: Frontend: The MapLibre GL JS Viewer** (Rendering, but incomplete coverage/perf)
-   [ ] **Step 5: Containerization**

### Phase 2: Deployment to Google Cloud with CI/CD
-   [ ] **Step 6: Google Cloud Project Setup**
-   [ ] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

---

## 2. Current Status

- Backend tests pass (`pytest`), and tiles render in MapLibre.
- Tile generation is using an EPSG:4326 envelope workaround because `ST_Transform(..., 'EPSG:4326', 'EPSG:3857')` returns `Infinity` in this environment.
- CORS is enabled for local testing (`allow_origins=["*"]`) so tiles load from the frontend server or file://.
- Rendering is slow and coverage appears partial (only NW quadrant reported); some tiles return `204` or `500` due to invalid geometry topology.
- Requirements were simplified to install cleanly in the virtualenv.

**Next Step:** Fix projection/tiling correctness and performance; address invalid geometries and caching.

---

## 3. Key Technical Notes & Troubleshooting

This section documents important solutions to issues encountered during setup.



### c. Data Preparation Script

-   **Problem:** The initial script to read a shapefile from within a `.zip` archive using a `zip://` URI failed with a pathing error, even with absolute paths.
-   **Solution:**
    1.  Unzipped the `CATASTRO.zip` file into the `data/` directory using the `unzip` command.
    2.  Modified `prepare_data.py` to read the `.shp` file directly from the filesystem, which worked successfully.

### d. Uvicorn Background Server Failure (Initial)

-   **Problem:** The FastAPI server ran correctly in the foreground but crashed silently when started as a background process with `&`. Redirecting output to log files also resulted in empty files.
-   **Solution:**
    1.  Used the `nohup` (no hang up) command for more robust background execution.
    2.  The successful command is: `nohup ./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &` run from the repo root. The output is logged to `uvicorn.log`.

### e. DuckDB `gdal` Extension & GeoParquet Reading Issues

-   **Problem:** Persistent `500 Internal Server Error` when the backend attempted to serve tiles.
    -   **Attempt 1 (DuckDB 1.4.3, direct file read):** Failed with `Binder Error: No extension found that is capable of reading the file...`. The `gdal` extension failed to download from DuckDB's extension server for `v1.4.3/osx_arm64`.
    -   **Attempt 2 (DuckDB 1.4.3, `geopandas` in-memory load):** Refactored `main.py` to load GeoParquet into `geopandas` DataFrame at startup and query this in-memory DataFrame with DuckDB. Failed with `Not implemented Error: Data type 'geometry' not recognized`, as DuckDB could not interpret the `geopandas` geometry objects directly.
    -   **Attempt 3 (DuckDB 0.10.3, direct file read):** Downgraded `duckdb` to `0.10.3` (hoping for `gdal` extension availability) and reverted `main.py` to the original direct file-reading logic with `INSTALL gdal; LOAD gdal;`. Still resulted in `HTTP Error: Failed to download extension "gdal"` for `v0.10.3/osx_arm64`.
-   **Current Status:** The core issue is that the DuckDB `gdal` extension for reading GeoParquet files is not reliably available for download on `osx_arm64` via the DuckDB extension server for the versions tested. This prevents direct spatial querying of GeoParquet files by DuckDB in the current setup.

### f. ST_Transform / PROJ database failure (current blocker)

-   **Problem:** `ST_Transform(..., 'EPSG:4326', 'EPSG:3857')` returns `POINT (Infinity Infinity)` even with `PROJ_DATA` / `PROJ_LIB` set.
-   **Impact:** Tile intersection against `ST_TileEnvelope` (3857) fails, producing empty tiles.
-   **Workaround Implemented:** Compute tile bounds in EPSG:4326 in Python and use them for `ST_Intersects` + `ST_AsMVTGeom`. This is less correct for Web Mercator but unblocks local rendering and testing.

### g. Tile rendering limitations (current)

-   **Symptoms:** MapLibre renders tiles, but coverage appears partial (NW quadrant) and some tiles error with `TopologyException`.
-   **Likely Causes:** Mixed coordinate systems, invalid geometries, and per-request MVT generation without caching.
-   **Next Fixes to Explore:**
    1.  Restore proper 3857 transforms once PROJ is fixed (or bundle PROJ data).
    2.  Wrap geometry with `ST_MakeValid` or pre-clean data to avoid topology errors.
    3.  Add caching and/or pre-tiled data to improve performance.
