# Project Status: Mexico City Cadastral Map

This document tracks the execution plan, progress, and key technical solutions for this project. Its purpose is to provide context for resuming work in new sessions.

---

## 1. Execution Plan

### Phase 1: Local Development & Core Functionality
-   [x] **Step 1: Project Scaffolding & Version Control**
-   [x] **Step 2: Data Acquisition and Preparation**
-   [ ] **Step 3: Backend: The DuckDB Tile Server** (Problematic - see Troubleshooting)
-   [ ] **Step 4: Frontend: The MapLibre GL JS Viewer**
-   [ ] **Step 5: Containerization**

### Phase 2: Deployment to Google Cloud with CI/CD
-   [ ] **Step 6: Google Cloud Project Setup**
-   [ ] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

---

## 2. Current Status

We have successfully completed the data acquisition and preparation step. However, the backend tile server for DuckDB is currently problematic due to issues with the `gdal` extension. The user is researching alternatives.

**Next Step:** User is researching solutions for the backend tile server.

---

## 3. Key Technical Notes & Troubleshooting

This section documents important solutions to issues encountered during setup.

### a. GitHub Authentication with Passkeys

-   **Problem:** User's passkey-enabled GitHub account prevented standard password authentication for `git push`.
-   **Solution:**
    1.  Installed the official GitHub CLI: `brew install gh`.
    2.  Authenticated using `gh auth login` with the SSH protocol.
    3.  Resolved a "Permission denied" error by explicitly adding the local SSH key to GitHub: `gh ssh-key add`.
    4.  Configured the Git remote to use the SSH URL: `git remote add origin git@github.com:plablo09/gemini-mbtiles.git`.

### b. SSH Passphrase Prompts

-   **Problem:** Every `git push` required re-entering the SSH key passphrase.
-   **Solution:**
    1.  Created a `~/.ssh/config` file to instruct SSH to use the macOS Keychain to store the passphrase automatically.
    2.  The user ran `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` to add the key's passphrase to the Keychain.

### c. Data Preparation Script

-   **Problem:** The initial script to read a shapefile from within a `.zip` archive using a `zip://` URI failed with a pathing error, even with absolute paths.
-   **Solution:**
    1.  Unzipped the `CATASTRO.zip` file into the `data/` directory using the `unzip` command.
    2.  Modified `prepare_data.py` to read the `.shp` file directly from the filesystem, which worked successfully.

### d. Uvicorn Background Server Failure (Initial)

-   **Problem:** The FastAPI server ran correctly in the foreground but crashed silently when started as a background process with `&`. Redirecting output to log files also resulted in empty files.
-   **Solution:**
    1.  Used the `nohup` (no hang up) command for more robust background execution.
    2.  The successful command is: `nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &` run from the `backend/` directory. The output is logged to `nohup.out`.

### e. DuckDB `gdal` Extension & GeoParquet Reading Issues

-   **Problem:** Persistent `500 Internal Server Error` when the backend attempted to serve tiles.
    -   **Attempt 1 (DuckDB 1.4.3, direct file read):** Failed with `Binder Error: No extension found that is capable of reading the file...`. The `gdal` extension failed to download from DuckDB's extension server for `v1.4.3/osx_arm64`.
    -   **Attempt 2 (DuckDB 1.4.3, `geopandas` in-memory load):** Refactored `main.py` to load GeoParquet into `geopandas` DataFrame at startup and query this in-memory DataFrame with DuckDB. Failed with `Not implemented Error: Data type 'geometry' not recognized`, as DuckDB could not interpret the `geopandas` geometry objects directly.
    -   **Attempt 3 (DuckDB 0.10.3, direct file read):** Downgraded `duckdb` to `0.10.3` (hoping for `gdal` extension availability) and reverted `main.py` to the original direct file-reading logic with `INSTALL gdal; LOAD gdal;`. Still resulted in `HTTP Error: Failed to download extension "gdal"` for `v0.10.3/osx_arm64`.
-   **Current Status:** The core issue is that the DuckDB `gdal` extension for reading GeoParquet files is not reliably available for download on `osx_arm64` via the DuckDB extension server for the versions tested. This prevents direct spatial querying of GeoParquet files by DuckDB in the current setup. The user is now researching alternative solutions for this backend data access.