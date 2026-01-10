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
-   [x] **Step 6: Google Cloud Project Setup** (Project: `mexico-city-cadastre-map`)
-   [x] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

### Phase 3: 3D Visualization & Advanced Features
-   [x] **Step 9: Data Analysis for Extrusion** (Identified `no_niveles`)
-   [x] **Step 10: Backend Support for 3D** (Added `no_niveles` to MVT)
-   [x] **Step 11: Frontend 3D Toggle & Fill-Extrusion Layer**
-   [x] **Step 12: Performance Optimization for 3D View** (Implemented Cache-Control & Versioning)

### Phase 4: Thematic Mapping & UX Improvements
-   [x] **Step 13: Data Analysis for Coloring** (Identified `uso_suelo` categories)
-   [x] **Step 14: Implement Categorical Coloring** (Habitacional=Orange, Comercio=Red, etc.)
-   [x] **Step 15: Interactive Legend & Help UI** (Unified dark-themed controls)

## 3. Data Management Workflow

Since the database (`mexico_city.duckdb`) is too large for git, we use a "Remote Artifact" pattern:

1.  **Local Updates:**
    -   Run `python prepare_data.py` to regenerate `geoparquet`.
    -   Restart local backend (rebuilds `duckdb`).
2.  **Push to Production:**
    -   Run `scripts/deploy_data.sh` to upload the local database to GCS.
    -   Commit and push code changes to `main` to trigger a deployment.
    -   The CD pipeline will download the updated database from GCS during the build.

---

## 4. Current Status

-   **Backend:**
    -   Fully functional FastAPI + DuckDB tile server.
    -   **Caching:** `Cache-Control: public, max-age=86400` implemented for static tiles.
    -   **Schema:** Serves `no_niveles` (height) attribute cast to integer.
-   **Frontend:**
    -   MapLibre GL JS viewer with **3D Toggle**.
    -   **Versioning:** Uses `TILE_VERSION` constant (`v1.1`) to manage browser cache during schema updates.
    -   **Visualization:** Renders `fill-extrusion` layer based on `no_niveles * 3.5m`.
-   **Infrastructure:**
    -   Containerized (Docker).
    -   Deployed on Google Cloud Run.
    -   **CI/CD:** Automated testing and deployment pipeline via GitHub Actions.
    -   **Data:** Production data hosted in GCS.
-   **Data:** `data/mexico_city.cleaned.3857.geoparquet` is the source of truth (EPSG:3857).

**Next Step:** Project finalized. Maintenance mode.

---

## 5. Key Technical Decisions & Troubleshooting Log

### Session: Jan 9, 2026 - 3D Feature Implementation & Troubleshooting

#### 1. 3D Extrusion Implementation
-   **Goal:** Extrude polygons based on `no_niveles` (number of levels).
-   **Implementation:**
    -   Added `no_niveles` to backend MVT query.
    -   Added `fill-extrusion` layer to MapLibre style with a 2D/3D toggle button.
    -   Mapped height to `no_niveles * 3.5m`.

#### 2. The "Missing Attribute" Mystery (SOLVED)
-   **Issue:** Browser persisted in showing old tile schema (missing `no_niveles`) despite backend code updates, even with incognito mode initially failing to show changes (likely due to deep caching or race conditions in testing).
-   **Resolution:**
    -   **Backend:** Added explicit `Cache-Control: public, max-age=86400` to tile responses.
    -   **Frontend:** Implemented a `TILE_VERSION` constant (e.g., `?v=v1.1`) in `map.js` to force-bust browser cache whenever the backend schema changes.
    -   **Code:** Verified correct SQL with `COALESCE(CAST(no_niveles AS INTEGER), 0)` to ensure robust MVT encoding.
-   **Result:** 3D extrusion now renders correctly with varied heights.

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

### Session: Jan 8, 2026 (Night) - Google Cloud Setup

#### 1. Project Initialization
-   **Project:** Created new GCP project `mexico-city-cadastre-map` and linked billing.
-   **Tooling:** Installed Google Cloud SDK via Homebrew and authenticated.
-   **Infrastructure:**
    -   Enabled `run.googleapis.com` (Cloud Run) and `artifactregistry.googleapis.com`.
    -   Created Artifact Registry repository `containers` in `us-central1`.

#### 2. Manual Deployment & Tuning
-   **Platform Build:** Rebuilt Docker image for `linux/amd64` to match Cloud Run architecture.
-   **Configuration:** Updated `Dockerfile` to respect the `PORT` env var (defaulting to 8000).
-   **Deployment:**
    -   Pushed image to Artifact Registry.
    -   Deployed to Cloud Run with `4Gi` memory (for DuckDB) and `2` vCPUs (for concurrency).
    -   Verified the live application at `https://gemini-mbtiles-938940805151.us-central1.run.app`.

### Prior Troubleshooting (Summary)
-   **Data Prep:** `zip://` URIs failed; switched to unzipping locally.
-   **Projections:** `ST_Transform` failed in DuckDB; switched to pre-projecting data to EPSG:3857 in `prepare_data.py`.
