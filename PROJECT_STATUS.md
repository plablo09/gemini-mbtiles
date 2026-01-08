# Project Status: Mexico City Cadastral Map

This document tracks the execution plan, progress, and key technical solutions for this project. Its purpose is to provide context for resuming work in new sessions.

---

## 1. Execution Plan

### Phase 1: Local Development & Core Functionality
-   [x] **Step 1: Project Scaffolding & Version Control**
-   [x] **Step 2: Data Acquisition and Preparation**
-   [x] **Step 3: Backend: The DuckDB Tile Server** (Optimized with index, simplification, caching)
-   [x] **Step 4: Frontend: The MapLibre GL JS Viewer** (Basemap added, performance tuned)
-   [x] **Step 5: Containerization**

### Phase 2: Deployment to Google Cloud with CI/CD
-   [ ] **Step 6: Google Cloud Project Setup**
-   [ ] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

---

## 2. Current Status

-   **Backend:**
    -   Serves MVT tiles via FastAPI + DuckDB.
    -   **Optimizations:** Uses `RTREE` spatial index, `ST_Simplify` (dynamic tolerance), and in-memory LRU caching (`@lru_cache`).
    -   **Connection Handling:** Switched to a small DuckDB connection pool with per-connection spatial loading and sanity checks to handle concurrent tile requests.
    -   **Storage:** Uses a file-backed DuckDB at `data/mexico_city.duckdb` so pooled connections share the same data.
    -   **Configuration:** `MIN_ZOOM` set to 14 to prevent server overload. Area filtering is currently disabled to ensure full data visibility.
    -   **Robustness:** Fixed Python 3.9 type hinting issues (`Optional[bytes]`).
-   **Frontend:**
    -   Displays tiles using MapLibre GL JS.
    -   **UX:** Includes OSM Raster Basemap and a custom Zoom Level indicator.
    -   **Configuration:** Starts at Zoom 14 to match backend capabilities.
-   **Data:**
    -   `data/mexico_city.cleaned.3857.geoparquet` is the verified source of truth (EPSG:3857).

**Next Step:** Containerization (Docker) to package the application for deployment.

---

## 3. Key Technical Decisions & Troubleshooting Log

### Session: Jan 8, 2026 - Performance & Stability

#### 1. Performance Optimization
-   **Issue:** Tiles at Zoom 8-10 were extremely slow or failing to load.
-   **Analysis:** At low zoom levels, the query was attempting to fetch/render >100,000 features per tile. Aggressive `ST_Area` filtering caused "holes" (missing data), while insufficient filtering caused timeouts.
-   **Solution:**
    -   **Spatial Index:** Implemented `CREATE INDEX ... USING RTREE (geometry)` on the in-memory DuckDB table.
    -   **Zoom Limits:** Restricted `MIN_ZOOM` to **14**. Cadastral lots are too small to be useful at Z<14, and rendering them as individual vectors is prohibitively expensive without pre-generalized aggregations.
    -   **Simplification:** Tuned `ST_Simplify` to `0.5 * resolution`.
-   **Caching:** Added `@lru_cache(maxsize=2048)` to the tile generation function.

#### 2. Concurrency & Pooling
-   **Issue:** Random tile failures during MapLibre panning/zooming due to concurrent requests against a single DuckDB connection.
-   **Solution:** Added a small connection pool and moved DuckDB to a file-backed DB to safely share state across pooled connections.

#### 2. Frontend Integration Fixes
-   **MapLibre Error:** `ReferenceError: Can't find variable: maplibregl`.
    -   *Fix:* Added the missing `<script>` tag for `maplibre-gl.js` in `index.html`.
-   **Port Conflict / 404s:**
    -   *Issue:* Frontend served on `[::1]:8000` (IPv6) masked Backend on `127.0.0.1:8000` (IPv4).
    -   *Fix:* Updated `map.js` to strictly point to `http://127.0.0.1:8000/...` and recommended running frontend on port 8080.
-   **UX:** Added OpenStreetMap basemap for geographic context and a visual Zoom Level indicator.

#### 3. Backend Stability
-   **Zombie Processes:** Old `uvicorn` processes were lingering and holding ports.
    -   *Fix:* Terminated processes using `pkill -f uvicorn` and verified with `ps`.
-   **Python Compatibility:** Fixed 3.9 `bytes | None` syntax error by switching to `Optional[bytes]`.

### Session: Jan 8, 2026 (Evening) - Containerization

#### 1. Dockerfile Implementation
-   **Approach:** Created a slim Python-based image that serves both the FastAPI backend and the static frontend.
-   **Data:** The `data/mexico_city.duckdb` file is copied into the image for a self-contained deployment.
-   **Optimizations:**
    -   Updated `.dockerignore` to exclude large source data files (`.geoparquet`, `.zip`), reducing build context from ~3GB to ~1.3GB.
    -   Verified that `FastAPI` correctly serves `frontend/` as static files within the container.
-   **Verification:**
    -   Built image `gemini-mbtiles`.
    -   Ran container and verified `/health` and `/tiles/14/...` endpoints via `curl`.
    -   Confirmed frontend assets (`index.html`, `style.css`, `map.js`) are served.

### Prior Troubleshooting (Summary)
-   **Data Prep:** `zip://` URIs failed; switched to unzipping locally.
-   **Projections:** `ST_Transform` failed in DuckDB; switched to pre-projecting data to EPSG:3857 in `prepare_data.py`.
