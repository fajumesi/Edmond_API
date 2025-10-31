"""
eCFR Data Fetcher
Fetches regulation data from eCFR API and calculates sizes
"""

import aiohttp
import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# eCFR API configuration
ECFR_BASE_URL = "https://www.ecfr.gov/api/versioner/v1"
DATA_FILE = "data/agency_data.json"
TEMP_FILE = "data/agency_data.tmp.json"

async def fetch_title_structure() -> List[Dict[str, Any]]:
    """
    Fetch the list of all CFR titles from eCFR API
    
    Returns:
        List of title objects with metadata
    """
    url = f"{ECFR_BASE_URL}/titles"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch titles: HTTP {response.status}")
                    return []
                
                data = await response.json()
                titles = data.get("titles", [])
                logger.info(f"Fetched {len(titles)} CFR titles")
                return titles
    
    except asyncio.TimeoutError:
        logger.error("Timeout while fetching title structure")
        return []
    except Exception as e:
        logger.error(f"Error fetching title structure: {e}")
        return []

async def fetch_title_content(title_number: int, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Fetch the full content for a specific CFR title
    
    Args:
        title_number: The CFR title number
        session: aiohttp session for connection pooling
        
    Returns:
        Dictionary with title data and size information
    """
    url = f"{ECFR_BASE_URL}/full/{datetime.utcnow().strftime('%Y-%m-%d')}/title-{title_number}.json"
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch title {title_number}: HTTP {response.status}")
                return None
            
            # Read the content to calculate size
            content = await response.read()
            size_bytes = len(content)
            size_mb = size_bytes / (1024 * 1024)
            
            # Parse JSON to get metadata
            try:
                data = json.loads(content)
                
                return {
                    "title_number": title_number,
                    "title_name": data.get("title", f"Title {title_number}"),
                    "size_mb": round(size_mb, 2),
                    "size_bytes": size_bytes
                }
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for title {title_number}")
                return None
    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching title {title_number}")
        return None
    except Exception as e:
        logger.error(f"Error fetching title {title_number}: {e}")
        return None

async def fetch_all_title_contents(titles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch content for all titles concurrently
    
    Args:
        titles: List of title metadata objects
        
    Returns:
        List of title content with size information
    """
    title_contents = []
    
    # Create a session for connection pooling
    connector = aiohttp.TCPConnector(limit=10)  # Limit concurrent connections
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minute total timeout
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create tasks for all titles
        tasks = []
        for title in titles:
            title_number = title.get("number")
            if title_number:
                tasks.append(fetch_title_content(title_number, session))
        
        # Execute all tasks concurrently with progress logging
        logger.info(f"Fetching content for {len(tasks)} titles...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} raised exception: {result}")
            elif result is not None:
                title_contents.append(result)
        
        logger.info(f"Successfully fetched {len(title_contents)} of {len(tasks)} titles")
    
    return title_contents

def map_titles_to_agencies(title_contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map CFR titles to federal agencies
    
    This is a simplified mapping. In production, this should use the official
    agency mapping from eCFR or a maintained database.
    
    Args:
        title_contents: List of title content objects
        
    Returns:
        List of agency objects with aggregated regulation sizes
    """
    # Title to Agency mapping (simplified - actual mapping is more complex)
    title_agency_map = {
        1: {"name": "General Provisions", "code": "GEN"},
        2: {"name": "Grants and Agreements", "code": "GRANTS"},
        3: {"name": "The President", "code": "POTUS"},
        4: {"name": "Accounts", "code": "GAO"},
        5: {"name": "Administrative Personnel", "code": "OPM"},
        6: {"name": "Domestic Security", "code": "DHS"},
        7: {"name": "Agriculture", "code": "USDA"},
        8: {"name": "Aliens and Nationality", "code": "USCIS"},
        9: {"name": "Animals and Animal Products", "code": "APHIS"},
        10: {"name": "Energy", "code": "DOE"},
        11: {"name": "Federal Elections", "code": "FEC"},
        12: {"name": "Banks and Banking", "code": "FRB"},
        13: {"name": "Business Credit and Assistance", "code": "SBA"},
        14: {"name": "Aeronautics and Space", "code": "FAA"},
        15: {"name": "Commerce and Foreign Trade", "code": "DOC"},
        16: {"name": "Commercial Practices", "code": "FTC"},
        17: {"name": "Commodity and Securities Exchanges", "code": "SEC"},
        18: {"name": "Conservation of Power and Water Resources", "code": "FERC"},
        19: {"name": "Customs Duties", "code": "CBP"},
        20: {"name": "Employees' Benefits", "code": "DOL"},
        21: {"name": "Food and Drugs", "code": "FDA"},
        22: {"name": "Foreign Relations", "code": "STATE"},
        23: {"name": "Highways", "code": "FHWA"},
        24: {"name": "Housing and Urban Development", "code": "HUD"},
        25: {"name": "Indians", "code": "BIA"},
        26: {"name": "Internal Revenue", "code": "IRS"},
        27: {"name": "Alcohol, Tobacco and Firearms", "code": "ATF"},
        28: {"name": "Judicial Administration", "code": "DOJ"},
        29: {"name": "Labor", "code": "DOL"},
        30: {"name": "Mineral Resources", "code": "DOI"},
        31: {"name": "Money and Finance: Treasury", "code": "TREAS"},
        32: {"name": "National Defense", "code": "DOD"},
        33: {"name": "Navigation and Navigable Waters", "code": "USCG"},
        34: {"name": "Education", "code": "ED"},
        36: {"name": "Parks, Forests, and Public Property", "code": "NPS"},
        37: {"name": "Patents, Trademarks, and Copyrights", "code": "USPTO"},
        38: {"name": "Pensions, Bonuses, and Veterans' Relief", "code": "VA"},
        39: {"name": "Postal Service", "code": "USPS"},
        40: {"name": "Protection of Environment", "code": "EPA"},
        41: {"name": "Public Contracts and Property Management", "code": "GSA"},
        42: {"name": "Public Health", "code": "HHS"},
        43: {"name": "Public Lands: Interior", "code": "BLM"},
        44: {"name": "Emergency Management and Assistance", "code": "FEMA"},
        45: {"name": "Public Welfare", "code": "HHS"},
        46: {"name": "Shipping", "code": "MARAD"},
        47: {"name": "Telecommunication", "code": "FCC"},
        48: {"name": "Federal Acquisition Regulations System", "code": "FAR"},
        49: {"name": "Transportation", "code": "DOT"},
        50: {"name": "Wildlife and Fisheries", "code": "FWS"},
    }
    
    # Aggregate by agency
    agency_data = {}
    
    for title_content in title_contents:
        title_num = title_content.get("title_number")
        size_mb = title_content.get("size_mb", 0)
        
        # Get agency info for this title
        agency_info = title_agency_map.get(title_num, {
            "name": f"Title {title_num} Agency",
            "code": f"T{title_num}"
        })
        
        agency_code = agency_info["code"]
        
        if agency_code not in agency_data:
            agency_data[agency_code] = {
                "name": agency_info["name"],
                "code": agency_code,
                "regulation_size_mb": 0.0,
                "titles": []
            }
        
        agency_data[agency_code]["regulation_size_mb"] += size_mb
        agency_data[agency_code]["titles"].append({
            "title_number": title_num,
            "title_name": title_content.get("title_name"),
            "size_mb": size_mb
        })
    
    # Convert to list and round sizes
    agencies = []
    for code, data in agency_data.items():
        data["regulation_size_mb"] = round(data["regulation_size_mb"], 2)
        data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        agencies.append(data)
    
    # Sort by size descending
    agencies.sort(key=lambda x: x["regulation_size_mb"], reverse=True)
    
    return agencies

async def fetch_and_update_data():
    """
    Main function to fetch all data and update the cache file
    """
    logger.info("Starting data fetch process...")
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Fetch title structure
        titles = await fetch_title_structure()
        
        if not titles:
            logger.error("No titles fetched. Aborting update.")
            return
        
        # Step 2: Fetch content for all titles
        title_contents = await fetch_all_title_contents(titles)
        
        if not title_contents:
            logger.error("No title contents fetched. Aborting update.")
            return
        
        # Step 3: Map to agencies and aggregate
        agencies = map_titles_to_agencies(title_contents)
        
        # Step 4: Create final data structure
        total_size_mb = sum(a["regulation_size_mb"] for a in agencies)
        
        final_data = {
            "agencies": agencies,
            "total_agencies": len(agencies),
            "total_size_mb": round(total_size_mb, 2),
            "last_sync": datetime.utcnow().isoformat() + "Z",
            "fetch_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        }
        
        # Step 5: Write to temp file first (atomic update)
        os.makedirs("data", exist_ok=True)
        with open(TEMP_FILE, 'w') as f:
            json.dump(final_data, f, indent=2)
        
        # Step 6: Rename temp file to actual file (atomic operation)
        os.replace(TEMP_FILE, DATA_FILE)
        
        logger.info(f"Data update completed successfully in {final_data['fetch_duration_seconds']:.2f} seconds")
        logger.info(f"Total agencies: {len(agencies)}, Total size: {total_size_mb:.2f} MB")
        
    except Exception as e:
        logger.error(f"Error in data fetch process: {e}", exc_info=True)
        # Clean up temp file if it exists
        if os.path.exists(TEMP_FILE):
            try:
                os.remove(TEMP_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    # Run the fetcher directly for testing
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_and_update_data())
