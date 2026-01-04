# Project Status: Mexico City Cadastral Map

This document tracks the execution plan, progress, and key technical solutions for this project. Its purpose is to provide context for resuming work in new sessions.

---

## 1. Execution Plan

### Phase 1: Local Development & Core Functionality
-   [x] **Step 1: Project Scaffolding & Version Control**
-   [x] **Step 2: Data Acquisition and Preparation**
-   [x] **Step 3: Backend: The DuckDB Tile Server**
-   [ ] **Step 4: Frontend: The MapLibre GL JS Viewer**
-   [ ] **Step 5: Containerization**

### Phase 2: Deployment to Google Cloud with CI/CD
-   [ ] **Step 6: Google Cloud Project Setup**
-   [ ] **Step 7: GitHub Actions CI/CD Workflow**
-   [ ] **Step 8: Finalization and DNS (Optional)**

---

## 2. Current Status

We have successfully completed the first three steps of Phase 1. The backend server is running locally and serving tiles from the prepared GeoParquet file.

**Next Step:** Begin **Phase 1, Step 4: Frontend: The MapLibre GL JS Viewer**.

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

### d. Uvicorn Background Server Failure

-   **Problem:** The FastAPI server ran correctly in the foreground but crashed silently when started as a background process with `&`. Redirecting output to log files also resulted in empty files, suggesting the process was terminated before it could write any logs.
-   **Solution:**
    1.  Used the `nohup` (no hang up) command for more robust background execution.
    2.  The successful command is: `nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &` run from the `backend/` directory. The output is logged to `nohup.out`.
