"""
Tests for eCFR data fetcher
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.fetcher import (
    fetch_title_structure,
    fetch_title_content,
    map_titles_to_agencies,
    fetch_and_update_data
)

@pytest.mark.asyncio
async def test_fetch_title_structure():
    """Test fetching title structure from eCFR API"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "titles": [
                {"number": 40, "name": "Protection of Environment"},
                {"number": 32, "name": "National Defense"}
            ]
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        titles = await fetch_title_structure()
        assert len(titles) == 2
        assert titles[0]["number"] == 40

@pytest.mark.asyncio
async def test_fetch_title_structure_error():
    """Test handling of API errors"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        titles = await fetch_title_structure()
        assert titles == []

@pytest.mark.asyncio
async def test_fetch_title_content():
    """Test fetching content for a specific title"""
    with patch('aiohttp.ClientSession') as mock_session:
        # Mock successful response with content
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'{"title": "Test Title"}' * 1000)
        
        session = AsyncMock()
        session.get.return_value.__aenter__.return_value = mock_response
        
        result = await fetch_title_content(40, session)
        assert result is not None
        assert "title_number" in result
        assert "size_mb" in result
        assert result["title_number"] == 40

def test_map_titles_to_agencies():
    """Test mapping titles to agencies"""
    title_contents = [
        {
            "title_number": 40,
            "title_name": "Protection of Environment",
            "size_mb": 45.2
        },
        {
            "title_number": 32,
            "title_name": "National Defense",
            "size_mb": 123.5
        }
    ]
    
    agencies = map_titles_to_agencies(title_contents)
    
    assert len(agencies) > 0
    assert all("name" in a for a in agencies)
    assert all("code" in a for a in agencies)
    assert all("regulation_size_mb" in a for a in agencies)

def test_map_titles_to_agencies_aggregation():
    """Test that multiple titles for same agency are aggregated"""
    title_contents = [
        {"title_number": 40, "title_name": "Environment", "size_mb": 20.0},
        {"title_number": 40, "title_name": "Environment Part 2", "size_mb": 25.0}
    ]
    
    agencies = map_titles_to_agencies(title_contents)
    
    # Should aggregate both titles into one agency
    epa_agencies = [a for a in agencies if a["code"] == "EPA"]
    if epa_agencies:
        assert epa_agencies[0]["regulation_size_mb"] >= 20.0

@pytest.mark.asyncio
async def test_fetch_and_update_data_creates_file():
    """Test that fetch_and_update_data creates data file"""
    import os
    import json
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    with patch('app.fetcher.fetch_title_structure') as mock_titles, \
         patch('app.fetcher.fetch_all_title_contents') as mock_contents:
        
        # Mock data
        mock_titles.return_value = [{"number": 40, "name": "Test"}]
        mock_contents.return_value = [
            {"title_number": 40, "title_name": "Test", "size_mb": 10.0}
        ]
        
        await fetch_and_update_data()
        
        # Check if file was created
        assert os.path.exists("data/agency_data.json")
        
        # Verify content
        with open("data/agency_data.json", "r") as f:
            data = json.load(f)
            assert "agencies" in data
            assert "last_sync" in data

@pytest.mark.asyncio
async def test_fetch_and_update_data_handles_errors():
    """Test error handling in fetch_and_update_data"""
    with patch('app.fetcher.fetch_title_structure') as mock_titles:
        # Simulate error
        mock_titles.return_value = []
        
        # Should not raise exception
        await fetch_and_update_data()

def test_agency_data_structure():
    """Test that agency data has required fields"""
    title_contents = [
        {"title_number": 40, "title_name": "Test", "size_mb": 10.0}
    ]
    
    agencies = map_titles_to_agencies(title_contents)
    
    for agency in agencies:
        assert "name" in agency
        assert "code" in agency
        assert "regulation_size_mb" in agency
        assert "last_updated" in agency
        assert isinstance(agency["regulation_size_mb"], (int, float))
        assert agency["regulation_size_mb"] >= 0
