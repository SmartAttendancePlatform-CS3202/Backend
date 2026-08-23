from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, model_validator
from shared_core.models.enums import VerificationMethod

ShapeType = Literal["circle", "square", "polygon"]

class VenueBase(BaseModel):
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None
    shape_type: ShapeType = "circle"
    boundary_data: Dict[str, Any]
    wifi_ssid: Optional[str] = None
    wifi_bssid: Optional[str] = None
    default_verification_method: VerificationMethod = VerificationMethod.gps_geofence
    capacity: Optional[int] = None
    is_active: bool = True

class VenueCreate(VenueBase):
    @model_validator(mode="after")
    def validate_boundary(self):
        shape = self.shape_type
        if shape == "circle":
            if not (self.boundary_data.get("center") or (self.boundary_data.get("latitude") is not None and self.boundary_data.get("longitude") is not None)):
                raise ValueError("Circle geofence requires center coordinates")
            if self.boundary_data.get("radius_m", self.boundary_data.get("radius_meters")) is None:
                raise ValueError("Circle geofence requires radius_meters")
        else:
            vertices = self.boundary_data.get("vertices", self.boundary_data.get("points", self.boundary_data.get("coordinates")))
            if not isinstance(vertices, list) or len(vertices) < 4:
                raise ValueError("Square/polygon geofence requires at least four vertices")
        return self

class VenueUpdate(BaseModel):
    name: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    shape_type: Optional[ShapeType] = None
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
