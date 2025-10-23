from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Farm, User
from app.schemas import FarmCreate, FarmRead
from app.security import get_current_user
from app.utils import get_coords_from_location  # <-- CORRECTED IMPORT

router = APIRouter(prefix="/farms", tags=["Farms"])


@router.post("/", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
async def create_farm(farm: FarmCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    coords = await get_coords_from_location(farm.location_text)
    if not coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find coordinates for location: '{farm.location_text}'."
        )

    # Use .model_dump() for Pydantic v2+ compatibility
    farm_data = farm.model_dump()
    farm_data.update(coords)
    farm_data["owner_id"] = current_user.id

    # Use .model_validate() for Pydantic v2+
    db_farm = Farm.model_validate(farm_data)

    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm


@router.get("/", response_model=List[FarmRead])
def read_farms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farms = db.exec(select(Farm).where(Farm.owner_id == current_user.id)).all()
    return farms


@router.get("/{farm_id}", response_model=FarmRead)
def read_farm(farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return farm


@router.patch("/{farm_id}", response_model=FarmRead)
async def update_farm(farm_id: int, farm_update: FarmCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_farm = db.get(Farm, farm_id)
    if not db_farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if db_farm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    farm_data = farm_update.model_dump(exclude_unset=True)

    if 'location_text' in farm_data and farm_data['location_text'] != db_farm.location_text:
        coords = await get_coords_from_location(farm_data['location_text'])
        if not coords:
            raise HTTPException(
                status_code=404, detail=f"Could not find new coordinates")
        farm_data.update(coords)

    for key, value in farm_data.items():
        setattr(db_farm, key, value)

    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(farm)
    db.commit()
    return
