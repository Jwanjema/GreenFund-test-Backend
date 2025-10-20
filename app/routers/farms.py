import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Farm, User
from app.schemas import FarmCreate, FarmRead
from app.security import get_current_user

router = APIRouter(
    prefix="/farms",
    tags=["farms"],
)

async def get_coords_from_location(location_text: str):
    """Calls the Nominatim API to get lat/lon for a location name."""
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    
    # --- THIS IS THE FIX ---
    # We add `countrycodes="ke"` to restrict the search to Kenya.
    params = {
        "q": location_text,
        "format": "json",
        "limit": 1,
        "countrycodes": "ke" 
    }
    
    # We must send a User-Agent header or Nominatim will reject the request
    headers = {"User-Agent": "GreenFundApp/1.0 (dev.test.app@gmail.com)"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(NOMINATIM_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not data:
                return None
            return {
                "latitude": float(data[0]["lat"]),
                "longitude": float(data[0]["lon"]),
            }
        except (httpx.RequestError, httpx.HTTPStatusError, IndexError, KeyError) as e:
            print(f"Geocoding error: {e}") # Added for server-side debugging
            return None

@router.post("/", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
async def create_farm(farm: FarmCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    coords = await get_coords_from_location(farm.location_text)
    if not coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find coordinates for location: '{farm.location_text}'. Please try being more specific (e.g., 'Kiambu Town')."
        )
    
    farm_data = farm.model_dump()
    farm_data.update(coords)
    farm_data["owner_id"] = current_user.id
    
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
        raise HTTPException(status_code=403, detail="Not authorized to access this farm")
    return farm

@router.patch("/{farm_id}", response_model=FarmRead)
async def update_farm(farm_id: int, farm_update: FarmCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_farm = db.get(Farm, farm_id)
    if not db_farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if db_farm.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this farm")
    
    farm_data = farm_update.model_dump(exclude_unset=True)
    
    # --- Geocode again if the location text changed ---
    if 'location_text' in farm_data and farm_data['location_text'] != db_farm.location_text:
        coords = await get_coords_from_location(farm_data['location_text'])
        if not coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find coordinates for new location: '{farm_data['location_text']}'"
            )
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
        raise HTTPException(status_code=403, detail="Not authorized to delete this farm")
        
    db.delete(farm)
    db.commit()
    return