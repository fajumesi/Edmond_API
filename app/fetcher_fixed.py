"""
eCFR Data Fetcher - CORRECTED VERSION
Fetches regulation data from eCFR API and calculates sizes
Uses: https://www.ecfr.gov/api/admin/v1/agencies.json
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
ECFR_AGENCIES_URL = "https://www.ecfr.gov/api/admin/v1/agencies.json"
ECFR_BASE_URL = "https://www.ecfr.gov/api/versioner/v1"
DATA_FILE = "data/agency_data.json"
TEMP_FILE = "data/agency_data.tmp.json"

async def fetch_agencies_list() -> List[Dict[str, Any]]:
    """
    Fetch the list of all federal agencies from eCFR API
    
    Returns:
        List of agency objects with metadata
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ECFR_AGENCIES_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch agencies: HTTP {response.status}")
                    return []
                
                data = await response.json()
                agencies = data.get("agencies", [])
                logger.info(f"Fetched {len(agencies)} agencies from eCFR")
                return agencies
    
    except asyncio.TimeoutError:
        logger.error("Timeout while fetching agencies list")
        return []
    except Exception as e:
        logger.error(f"Error fetching agencies list: {e}")
        return []

async def fetch_agency_titles(agency_slug: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """
    Fetch titles for a specific agency
    
    Args:
        agency_slug: Agency identifier slug
        session: aiohttp session for connection pooling
        
    Returns:
        List of title numbers for this agency
    """
    url = f"{ECFR_BASE_URL}/titles"
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch titles for {agency_slug}: HTTP {response.status}")
                return []
            
            data = await response.json()
            titles = data.get("titles", [])
            return titles
    
    except Exception as e:
        logger.error(f"Error fetching titles for {agency_slug}: {e}")
        return []

async def fetch_title_size(title_number: int, session: aiohttp.ClientSession) -> float:
    """
    Fetch the size of a specific CFR title
    
    Args:
        title_number: The CFR title number
        session: aiohttp session for connection pooling
        
    Returns:
        Size in megabytes
    """
    # Use the full JSON endpoint for the title
    url = f"{ECFR_BASE_URL}/full/{datetime.utcnow().strftime('%Y-%m-%d')}/title-{title_number}.json"
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch title {title_number}: HTTP {response.status}")
                return 0.0
            
            # Read the content to calculate size
            content = await response.read()
            size_bytes = len(content)
            size_mb = size_bytes / (1024 * 1024)
            
            logger.info(f"Title {title_number}: {size_mb:.2f} MB")
            return round(size_mb, 2)
    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching title {title_number}")
        return 0.0
    except Exception as e:
        logger.error(f"Error fetching title {title_number}: {e}")
        return 0.0

async def calculate_agency_sizes(agencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate regulation sizes for each agency
    
    Args:
        agencies: List of agency objects from eCFR
        
    Returns:
        List of agencies with calculated regulation sizes
    """
    results = []
    
    # Create a session for connection pooling
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # First, get all titles
        logger.info("Fetching CFR titles structure...")
        url = f"{ECFR_BASE_URL}/titles"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch titles: HTTP {response.status}")
                    return []
                
                data = await response.json()
                titles = data.get("titles", [])
                logger.info(f"Found {len(titles)} CFR titles")
        except Exception as e:
            logger.error(f"Error fetching titles: {e}")
            return []
        
        # Map titles to agencies based on title numbers
        # This is a simplified mapping - in reality, agencies can have multiple titles
        title_agency_map = {
            1: "General Provisions",
            2: "Grants and Agreements", 
            3: "The President",
            4: "Accounts",
            5: "Administrative Personnel",
            6: "Domestic Security",
            7: "Agriculture",
            8: "Aliens and Nationality",
            9: "Animals and Animal Products",
            10: "Energy",
            11: "Federal Elections",
            12: "Banks and Banking",
            13: "Business Credit",
            14: "Aeronautics and Space",
            15: "Commerce and Foreign Trade",
            16: "Commercial Practices",
            17: "Commodity and Securities Exchanges",
            18: "Conservation of Power",
            19: "Customs Duties",
            20: "Employees' Benefits",
            21: "Food and Drugs",
            22: "Foreign Relations",
            23: "Highways",
            24: "Housing and Urban Development",
            25: "Indians",
            26: "Internal Revenue",
            27: "Alcohol, Tobacco and Firearms",
            28: "Judicial Administration",
            29: "Labor",
            30: "Mineral Resources",
            31: "Money and Finance: Treasury",
            32: "National Defense",
            33: "Navigation and Navigable Waters",
            34: "Education",
            36: "Parks, Forests, and Public Property",
            37: "Patents, Trademarks, and Copyrights",
            38: "Pensions, Bonuses, and Veterans' Relief",
            39: "Postal Service",
            40: "Protection of Environment",
            41: "Public Contracts and Property Management",
            42: "Public Health",
            43: "Public Lands: Interior",
            44: "Emergency Management",
            45: "Public Welfare",
            46: "Shipping",
            47: "Telecommunication",
            48: "Federal Acquisition Regulations",
            49: "Transportation",
            50: "Wildlife and Fisheries",
        }
        
        # Fetch sizes for all titles
        logger.info(f"Fetching sizes for {len(titles)} titles...")
        title_sizes = {}
        
        tasks = []
        for title in titles:
            title_num = title.get("number")
            if title_num:
                tasks.append(fetch_title_size(title_num, session))
        
        sizes = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results
        for i, title in enumerate(titles):
            title_num = title.get("number")
            if title_num and i < len(sizes):
                if isinstance(sizes[i], (int, float)):
                    title_sizes[title_num] = sizes[i]
        
        logger.info(f"Successfully fetched sizes for {len(title_sizes)} titles")
        
        # Aggregate by agency using the mapping
        agency_data = {}
        for title_num, size_mb in title_sizes.items():
            agency_name = title_agency_map.get(title_num, f"Title {title_num}")
            
            # Create a simplified agency code
            agency_code = agency_name.upper().replace(" ", "_").replace(":", "")[:10]
            
            if agency_code not in agency_data:
                agency_data[agency_code] = {
                    "name": agency_name,
                    "code": agency_code,
                    "regulation_size_mb": 0.0,
                    "titles": []
                }
            
            agency_data[agency_code]["regulation_size_mb"] += size_mb
            agency_data[agency_code]["titles"].append({
                "title_number": title_num,
                "size_mb": size_mb
            })
        
        # Convert to list
        for code, data in agency_data.items():
            data["regulation_size_mb"] = round(data["regulation_size_mb"], 2)
            data["last_updated"] = datetime.utcnow().isoformat() + "Z"
            results.append(data)
        
        # Sort by size descending
        results.sort(key=lambda x: x["regulation_size_mb"], reverse=True)
    
    return results

async def fetch_and_update_data():
    """
    Main function to fetch all data and update the cache file
    """
    logger.info("Starting data fetch process...")
    start_time = datetime.utcnow()
    
    try:
        # Fetch agencies from eCFR
        logger.info(f"Fetching agencies from {ECFR_AGENCIES_URL}")
        agencies_list = await fetch_agencies_list()
        
        if not agencies_list:
            logger.warning("No agencies fetched from API, using title-based approach")
        
        # Calculate sizes for all agencies
        agencies = await calculate_agency_sizes(agencies_list)
        
        if not agencies:
            logger.error("No agency data generated. Aborting update.")
            return
        
        # Create final data structure
        total_size_mb = sum(a["regulation_size_mb"] for a in agencies)
        
        final_data = {
            "agencies": agencies,
            "total_agencies": len(agencies),
            "total_size_mb": round(total_size_mb, 2),
            "last_sync": datetime.utcnow().isoformat() + "Z",
            "fetch_duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        }
        
        # Write to temp file first (atomic update)
        os.makedirs("data", exist_ok=True)
        with open(TEMP_FILE, 'w') as f:
            json.dump(final_data, f, indent=2)
        
        # Rename temp file to actual file (atomic operation)
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
