"""
Pydantic Models
Data validation models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class AgencyData(BaseModel):
    """Model for individual agency data"""
    name: str = Field(..., description="Full name of the federal agency")
    code: str = Field(..., description="Short code for the agency (e.g., EPA, DOD)")
    regulation_size_mb: float = Field(..., description="Total size of regulations in megabytes", ge=0)
    last_updated: str = Field(..., description="ISO 8601 timestamp of last update")
    titles: Optional[List[dict]] = Field(None, description="List of CFR titles for this agency")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Environmental Protection Agency",
                "code": "EPA",
                "regulation_size_mb": 45.2,
                "last_updated": "2025-10-28T10:30:00Z",
                "titles": [
                    {
                        "title_number": 40,
                        "title_name": "Protection of Environment",
                        "size_mb": 45.2
                    }
                ]
            }
        }

class AgencyResponse(BaseModel):
    """Model for the main agencies API response"""
    agencies: List[AgencyData] = Field(..., description="List of all federal agencies")
    total_agencies: int = Field(..., description="Total count of agencies", ge=0)
    total_size_mb: float = Field(..., description="Total size of all regulations in MB", ge=0)
    last_sync: Optional[str] = Field(None, description="ISO 8601 timestamp of last data synchronization")

    class Config:
        json_schema_extra = {
            "example": {
                "agencies": [
                    {
                        "name": "Environmental Protection Agency",
                        "code": "EPA",
                        "regulation_size_mb": 45.2,
                        "last_updated": "2025-10-28T10:30:00Z"
                    },
                    {
                        "name": "Department of Defense",
                        "code": "DOD",
                        "regulation_size_mb": 123.5,
                        "last_updated": "2025-10-28T10:30:00Z"
                    }
                ],
                "total_agencies": 150,
                "total_size_mb": 2847.3,
                "last_sync": "2025-10-28T10:30:00Z"
            }
        }

class HealthResponse(BaseModel):
    """Model for health check response"""
    status: str = Field(..., description="Health status: healthy, degraded, or unhealthy")
    version: str = Field(..., description="API version")
    last_data_update: Optional[str] = Field(None, description="ISO 8601 timestamp of last data update")
    timestamp: str = Field(..., description="Current timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "last_data_update": "2025-10-28T10:30:00Z",
                "timestamp": "2025-10-28T14:23:15Z"
            }
        }

class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
    path: Optional[str] = Field(None, description="Request path that caused the error")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not Found",
                "message": "The requested resource was not found",
                "timestamp": "2025-10-28T14:23:15Z",
                "path": "/api/agencies/INVALID"
            }
        }
