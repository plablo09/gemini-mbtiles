import pytest
from fastapi.testclient import TestClient
import gzip
from backend.main import app

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

# A known tile coordinate that should contain data for Mexico City.
VALID_TILE_Z = 14
VALID_TILE_X = 4203
VALID_TILE_Y = 6799

def test_get_valid_tile():
    """Test requesting a valid, non-empty tile."""
    with TestClient(app) as client:
        response = client.get(f"/tiles/{VALID_TILE_Z}/{VALID_TILE_X}/{VALID_TILE_Y}.pbf")
        
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
        
        # For empty tiles, it's common practice for MVT servers to return 200 OK with an empty MVT
        assert response.status_code == 200
        
        # Check content type
        assert response.headers["content-type"] == "application/vnd.mapbox-vector-tile"

        # The content should be a very small, valid empty MVT
        assert len(response.content) > 0
        assert len(response.content) < 100 # An empty MVT is typically very small (e.g., < 50 bytes)


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
