# Project Status: Mexico City Cadastral Map

This document tracks the execution plan, progress, and key technical solutions for this project. Its purpose is to provide context for resuming work in new sessions.

---

## 1. Execution Plan

### Phase 1: Local Development & Core Functionality
-   [x] **Step 1: Project Scaffolding & Version Control**
-   [x] **Step 2: Data Acquisition and Preparation**
-   [~] **Step 3: Backend: The DuckDB Tile Server** (Now using 3857 data + ST_TileEnvelope; performance tuning pending)
-   [~] **Step 4: Frontend: The MapLibre GL JS Viewer** (Rendering, but incomplete coverage/perf)
-   [ ] **Step 5: Containerization**

### Phase 2: Deployment to Google Cloud with CI/CD
-   [ ] **Step 6: Google Cloud Project Setup**
-   [ ] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

---

## 2. Current Status

- Backend tests pass (`pytest`), and tiles render in MapLibre.
- GeoParquet data is cleaned and preprojected to EPSG:3857 (`data/mexico_city.cleaned.3857.geoparquet`) to avoid per-request transforms.
- Invalid geometries were repaired with `ST_MakeValid`/`shapely.make_valid` during the one-off cleanup; current file validates cleanly.
- CORS is enabled for local testing (`allow_origins=["*"]`) so tiles load from the frontend server or file://.
- Rendering is slow and coverage appears partial (only NW quadrant reported); need to re-check after performance work.
- Requirements were simplified to install cleanly in the virtualenv.

**Next Step:** Focus on tile performance (caching, query tuning) and confirm coverage after 3857 switch.

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

### f. ST_Transform / PROJ database failure (prior blocker)

-   **Problem:** `ST_Transform(..., 'EPSG:4326', 'EPSG:3857')` returns `POINT (Infinity Infinity)` even with `PROJ_DATA` / `PROJ_LIB` set.
-   **Impact:** Tile intersection against `ST_TileEnvelope` (3857) fails, producing empty tiles.
-   **Workaround Implemented:** Preproject data to EPSG:3857 and use `ST_TileEnvelope` directly, avoiding `ST_Transform` in requests.

### g. Tile rendering limitations (current)

-   **Symptoms:** MapLibre renders tiles, but coverage appears partial (NW quadrant).
-   **Likely Causes:** Per-request MVT generation without caching; needs query/perf profiling.
-   **Next Fixes to Explore:**
    1.  Add caching and/or pre-tiled data to improve performance.
    2.  Review tile query plan and reduce per-request overhead.
