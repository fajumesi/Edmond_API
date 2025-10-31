"""
Test suite for eCFR API
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
import os

client = TestClient(app)

@pytest.fixture
def sample_agency_data():
    """Create sample agency data for testing"""
    return {
        "agencies": [
            {
                "name": "Environmental Protection Agency",
                "code": "EPA",
                "regulation_size_mb": 45.2,
                "last_updated": "2025-10-28T10:30:00Z",
                "titles": []
            },
            {
                "name": "Department of Defense",
                "code": "DOD",
                "regulation_size_mb": 123.5,
                "last_updated": "2025-10-28T10:30:00Z",
                "titles": []
            }
        ],
        "total_agencies": 2,
        "total_size_mb": 168.7,
        "last_sync": "2025-10-28T10:30:00Z"
    }

@pytest.fixture
def setup_test_data(sample_agency_data):
    """Setup test data file"""
    os.makedirs("data", exist_ok=True)
    with open("data/agency_data.json", "w") as f:
        json.dump(sample_agency_data, f)
    yield
    # Cleanup
    if os.path.exists("data/agency_data.json"):
        os.remove("data/agency_data.json")

def test_root_endpoint():
    """Test root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "endpoints" in data

def test_get_agencies(setup_test_data):
    """Test agencies endpoint returns data correctly"""
    response = client.get("/api/agencies")
    assert response.status_code == 200
    data = response.json()
    assert "agencies" in data
    assert "total_agencies" in data
    assert "total_size_mb" in data
    assert "last_sync" in data
    assert len(data["agencies"]) == 2

def test_get_agencies_no_data():
    """Test agencies endpoint when no data available"""
    # Remove data file if exists
    if os.path.exists("data/agency_data.json"):
        os.remove("data/agency_data.json")
    
    response = client.get("/api/agencies")
    assert response.status_code == 503

def test_get_agency_by_code(setup_test_data):
    """Test getting specific agency by code"""
    response = client.get("/api/agencies/EPA")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "EPA"
    assert data["name"] == "Environmental Protection Agency"
    assert data["regulation_size_mb"] == 45.2

def test_get_agency_by_code_case_insensitive(setup_test_data):
    """Test agency code lookup is case-insensitive"""
    response = client.get("/api/agencies/epa")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "EPA"

def test_get_agency_not_found(setup_test_data):
    """Test 404 for non-existent agency"""
    response = client.get("/api/agencies/INVALID")
    assert response.status_code == 404

def test_health_endpoint(setup_test_data):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "1.0.0"

def test_health_endpoint_no_data():
    """Test health check when data is missing"""
    if os.path.exists("data/agency_data.json"):
        os.remove("data/agency_data.json")
    
    response = client.get("/health")
    # Should still return 200 but with degraded status
    assert response.status_code in [200, 503]

def test_stats_endpoint(setup_test_data):
    """Test statistics endpoint"""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_agencies" in data
    assert "total_size_mb" in data
    assert "average_size_mb" in data
    assert "largest_agency" in data
    assert "smallest_agency" in data

def test_refresh_endpoint():
    """Test manual refresh trigger"""
    response = client.post("/api/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"

def test_cors_headers():
    """Test CORS headers are present"""
    response = client.options("/api/agencies")
    assert "access-control-allow-origin" in response.headers

def test_404_custom_handler():
    """Test custom 404 handler"""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"] == "Not Found"

@pytest.mark.asyncio
async def test_api_response_format(setup_test_data):
    """Test API response follows expected format"""
    response = client.get("/api/agencies")
    data = response.json()
    
    # Check structure
    assert isinstance(data["agencies"], list)
    assert isinstance(data["total_agencies"], int)
    assert isinstance(data["total_size_mb"], float)
    
    # Check agency structure
    if data["agencies"]:
        agency = data["agencies"][0]
        assert "name" in agency
        assert "code" in agency
        assert "regulation_size_mb" in agency
        assert "last_updated" in agency

def test_api_documentation():
    """Test that API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
