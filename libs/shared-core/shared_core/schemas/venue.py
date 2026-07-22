from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from shared_core.models.enums import GeofenceShape, VerificationMethod

class VenueBase(BaseModel):
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None
    shape_type: GeofenceShape = GeofenceShape.circle
    boundary_data: Dict[str, Any]
    wifi_ssid: Optional[str] = None
    wifi_bssid: Optional[str] = None
    default_verification_method: VerificationMethod = VerificationMethod.gps_geofence
    capacity: Optional[int] = None
    is_active: bool = True

class VenueCreate(VenueBase):
    pass

class VenueUpdate(BaseModel):
    name: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    shape_type: Optional[GeofenceShape] = None
    boundary_data: Optional[Dict[str, Any]] = None
    wifi_ssid: Optional[str] = None
    wifi_bssid: Optional[str] = None
    default_verification_method: Optional[VerificationMethod] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None

class VenueOut(VenueBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
