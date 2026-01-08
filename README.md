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
