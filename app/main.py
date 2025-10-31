"""
eCFR Regulations API - Main Application with Beautiful Dashboard
FastAPI application that provides regulation size data via REST API and web dashboard
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json
import os
from datetime import datetime
import logging
from pathlib import Path

from .scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from .fetcher import fetch_and_update_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data file path
DATA_FILE = "data/agency_data.json"

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Starting eCFR API application...")
    
    # Start the background scheduler
    start_scheduler()
    
    # Initial data check
    if not os.path.exists(DATA_FILE):
        logger.info("No data file found. Triggering initial data fetch...")
        try:
            await fetch_and_update_data()
        except Exception as e:
            logger.error(f"Initial data fetch failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down eCFR API application...")
    stop_scheduler()

# Create FastAPI application
app = FastAPI(
    title="eCFR Regulations API",
    description="API for accessing federal regulation sizes from eCFR.gov",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_data():
    """Load agency data from JSON file"""
    if not os.path.exists(DATA_FILE):
        logger.error(f"Data file not found: {DATA_FILE}")
        return None
    
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data file: {e}")
        return None

# Root endpoint - Beautiful Dashboard
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve beautiful dashboard at root"""
    dashboard_path = Path(__file__).parent / "templates" / "dashboard.html"
    
    if dashboard_path.exists():
        return dashboard_path.read_text()
    
    # Fallback simple HTML if dashboard file not found
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>eCFR API</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }
            h1 { color: #333; }
            .links { margin-top: 30px; }
            a { display: inline-block; margin: 10px; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
            a:hover { background: #5568d3; }
        </style>
    </head>
    <body>
        <h1>📊 eCFR Regulations API</h1>
        <p>Federal Regulation Size Tracking</p>
        <div class="links">
            <a href="/docs">📖 API Documentation</a>
            <a href="/api/agencies">📡 View Data</a>
            <a href="/health">💚 Health Check</a>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns API status and last data update time
    """
    data = load_data()
    
    return {
        "status": "healthy" if data else "degraded",
        "version": "1.0.0",
        "last_data_update": data.get("last_sync") if data else None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/agencies")
async def get_agencies():
    """
    Get all federal agencies with their regulation sizes
    
    Returns:
        JSON containing list of agencies with sizes and metadata
    """
    data = load_data()
    
    if not data:
        raise HTTPException(
            status_code=503,
            detail="Data not available. Initial data fetch may be in progress."
        )
    
    return data

@app.get("/api/agencies/{agency_code}")
async def get_agency(agency_code: str):
    """
    Get specific agency by code
    
    Args:
        agency_code: Agency code (e.g., 'EPA', 'FDA')
    
    Returns:
        JSON containing agency details
    """
    data = load_data()
    
    if not data:
        raise HTTPException(
            status_code=503,
            detail="Data not available"
        )
    
    # Find agency by code
    agency = next(
        (a for a in data.get("agencies", []) if a["code"].upper() == agency_code.upper()),
        None
    )
    
    if not agency:
        raise HTTPException(
            status_code=404,
            detail=f"Agency with code '{agency_code}' not found"
        )
    
    return agency

@app.get("/api/stats")
async def get_statistics():
    """
    Get aggregate statistics
    
    Returns:
        JSON containing aggregate statistics
    """
    data = load_data()
    
    if not data:
        raise HTTPException(
            status_code=503,
            detail="Data not available"
        )
    
    agencies = data.get("agencies", [])
    
    return {
        "total_agencies": len(agencies),
        "total_size_mb": data.get("total_size_mb", 0),
        "largest_agency": max(agencies, key=lambda x: x["regulation_size_mb"]) if agencies else None,
        "smallest_agency": min(agencies, key=lambda x: x["regulation_size_mb"]) if agencies else None,
        "average_size_mb": round(data.get("total_size_mb", 0) / len(agencies), 2) if agencies else 0,
        "last_sync": data.get("last_sync")
    }

@app.post("/api/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """
    Trigger manual data refresh
    This endpoint triggers a background fetch of fresh data
    
    Returns:
        JSON confirmation message
    """
    background_tasks.add_task(fetch_and_update_data)
    
    return {
        "message": "Data refresh triggered",
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/scheduler/status")
async def scheduler_status():
    """
    Get scheduler status
    
    Returns:
        JSON containing scheduler status and job information
    """
    return get_scheduler_status()

# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": str(exc.detail) if hasattr(exc, 'detail') else "The requested resource was not found",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
