from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.venue import VenueOut, VenueCreate, VenueUpdate
from shared_core.models.identity import User
from app.services import venue_service

router = APIRouter(prefix="/venues", tags=["venues"])

@router.get("", response_model=List[VenueOut])
def list_venues(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return venue_service.get_all_venues(db, skip=skip, limit=limit)

@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(
    data: VenueCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return venue_service.create_venue(db, data.model_dump())

@router.get("/{id}", response_model=VenueOut)
def get_venue(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    venue = venue_service.get_venue(db, id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

@router.patch("/{id}", response_model=VenueOut)
def update_venue(
    id: UUID,
    data: VenueUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    venue = venue_service.update_venue(db, id, data.model_dump(exclude_unset=True))
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue
