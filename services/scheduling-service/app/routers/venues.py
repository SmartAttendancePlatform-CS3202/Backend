from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared_core.db.session import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role, verify_internal_key
from shared_core.schemas.venue import VenueOut, VenueCreate, VenueUpdate
from shared_core.models.identity import User
from app.services import venue_service
from shared_core.audit import audit

router = APIRouter(prefix="/venues", tags=["venues"])

@router.get("", response_model=List[VenueOut])
def list_venues(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return venue_service.get_all_venues(db)

@router.post("", response_model=VenueOut, status_code=201)
def create(data: VenueCreate, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return venue_service.create_venue(db, data.model_dump())

@router.get("/internal/{id}", dependencies=[Depends(verify_internal_key)], response_model=VenueOut)
def internal(id: UUID, db: Session = Depends(get_db)):
    obj = venue_service.get_venue(db, id)
    if not obj:
        raise HTTPException(404, "Venue not found")
    return obj

@router.get("/{id}", response_model=VenueOut)
def get(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = venue_service.get_venue(db, id)
    if not obj:
        raise HTTPException(404, "Venue not found")
    return obj

@router.patch("/{id}", response_model=VenueOut)
def update(id: UUID, data: VenueUpdate, current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    obj = venue_service.get_venue(db, id)
    if not obj: raise HTTPException(404, "Venue not found")
    old = {"shape_type": getattr(obj.shape_type, "value", obj.shape_type), "boundary_data": obj.boundary_data}
    obj = venue_service.update_venue(db, id, data.model_dump(exclude_unset=True))
    audit(db, current_user.id, "venue.update", "venue", obj.id, old_data=old, new_data={"shape_type": getattr(obj.shape_type, "value", obj.shape_type), "boundary_data": obj.boundary_data})
    db.commit()
    return obj
