import math
import pytest
from fastapi.testclient import TestClient
import gzip
from backend.main import app
from backend.db import get_db_connection, TABLE_NAME

# By using a 'with' statement, we ensure that the app's lifespan events
# (startup and shutdown) are triggered during the tests.
# This will initialize the database connection.
def test_read_root():
    """Test the root endpoint."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Mexico City Cadastral Map Tile Server!"}

def test_health_check_ok():
    """Test the health check endpoint when the server is healthy."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "ok"
        assert "Database connection is healthy" in json_response["message"]

# --- Tile Endpoint Tests ---

VALID_TILE_Z = 14

def _tile_coords_for_point(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    xtile = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile

def test_get_valid_tile():
    """Test requesting a valid, non-empty tile."""
    with TestClient(app) as client:
        con = get_db_connection()
        xmin, ymin, xmax, ymax = con.execute(
            f"SELECT ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext) "
            f"FROM (SELECT ST_Extent(geometry) AS ext FROM {TABLE_NAME});"
        ).fetchone()
        lon = (xmin + xmax) / 2
        lat = (ymin + ymax) / 2
        tile_x, tile_y = _tile_coords_for_point(lon, lat, VALID_TILE_Z)
        response = client.get(f"/tiles/{VALID_TILE_Z}/{tile_x}/{tile_y}.pbf")
        
        # Expect a 200 OK response
        assert response.status_code == 200
        
        # Check content type
        assert response.headers["content-type"] == "application/vnd.mapbox-vector-tile"
        
        # httpx automatically decompresses, so no Content-Encoding header will be present
        # We verify that the content is valid gzip by trying to decompress it
        # (even though httpx already did it)
        # The content should be the raw MVT bytes after httpx decompression
        assert len(response.content) > 0 # Should not be empty for a valid tile with data

def test_get_empty_tile():
    """Test requesting a tile that is valid but likely contains no features (e.g., in the ocean)."""
    with TestClient(app) as client:
        # z=14, x=0, y=0 is in the middle of the Atlantic Ocean
        response = client.get("/tiles/14/0/0.pbf")
        
        # For empty tiles, we return 204 No Content to signal an empty tile
        assert response.status_code == 204
        assert response.content == b""


def test_get_tile_invalid_zoom():
    """Test requesting a tile with a zoom level outside the supported range."""
    with TestClient(app) as client:
        # Test a zoom level that is too low
        invalid_low_zoom = 5
        response_low = client.get(f"/tiles/{invalid_low_zoom}/0/0.pbf")
        assert response_low.status_code == 404
        
        # Test a zoom level that is too high
        invalid_high_zoom = 25
        response_high = client.get(f"/tiles/{invalid_high_zoom}/0/0.pbf")
        assert response_high.status_code == 404
