# Mexico City Cadastral Map Tile Server

A high-performance vector tile server for Mexico City's cadastral data, built with **FastAPI**, **DuckDB**, and **MapLibre GL JS**.

## Features

-   **Vector Tiles (MVT):** Serves Mapbox Vector Tiles dynamically from a DuckDB database.
-   **Spatial Indexing:** Uses DuckDB's `RTREE` index for fast spatial queries.
-   **Frontend Viewer:** A lightweight MapLibre GL JS client to visualize the data.
-   **Containerized:** Fully Dockerized for easy deployment.

## Quick Start (Docker)

The easiest way to run the application is using Docker.

### Prerequisites

-   Docker installed on your machine.
-   The DuckDB database file `data/mexico_city.duckdb` must exist locally (created via `prepare_data.py` or `db.py` initialization).

### Running the Application

1.  **Build the Docker image:**

    ```bash
    docker build -t gemini-mbtiles .
    ```

2.  **Run the container:**

    ```bash
    docker run -d -p 8000:8000 --name gemini-mbtiles-container gemini-mbtiles
    ```

3.  **Access the Map:**

    Open your browser to [http://localhost:8000](http://localhost:8000).

### Stopping the Container

```bash
docker stop gemini-mbtiles-container
docker rm gemini-mbtiles-container
```

## CI/CD & Data Management

This project uses **GitHub Actions** for automated testing and deployment to **Google Cloud Run**.

### Architecture
-   **CI (Continuous Integration):** Runs on every push. It creates a synthetic "dummy" dataset (single polygon) to test the API and tile generation logic without needing the large production dataset.
-   **CD (Continuous Deployment):** Runs on pushes to `main`. It downloads the full production database (`mexico_city.duckdb`) from a secure **Google Cloud Storage (GCS)** bucket and bakes it into the Docker image before deploying to Cloud Run.

### Updating Production Data
The production database is too large to be stored in Git. To update the data served by the application:

1.  **Update Local Data:**
    Run your data preparation scripts (e.g., `prepare_data.py`) to update `data/mexico_city.duckdb`.

2.  **Upload to GCS:**
    Use the helper script to upload your local database to the production bucket:
    ```bash
    ./scripts/deploy_data.sh
    ```
    *Note: You need Google Cloud SDK installed and authenticated.*

3.  **Trigger Deployment:**
    Push a commit to the `main` branch. The CD pipeline will pick up the new database file from GCS during the build process.

## Local Development (Without Docker)

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the server:**
    ```bash
    python -m uvicorn backend.main:app --reload
    ```

4.  **Access the Map:**
    Open [http://localhost:8000](http://localhost:8000).
