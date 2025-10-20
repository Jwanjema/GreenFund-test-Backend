from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from pydantic import BaseModel
from typing import List, Dict

from app.database import get_db
from app.models import FarmActivity, User, Farm
from app.schemas import FarmActivityCreate, FarmActivityRead
from app.security import get_current_user
from app.carbon_model import estimate_carbon_footprint

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
)

# --- Schema (no change) ---
@router.post("/", response_model=FarmActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: FarmActivityCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, activity.farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    estimated_carbon = estimate_carbon_footprint(activity.activity_type, activity.description)
    
    db_activity = FarmActivity.model_validate(
        activity, 
        update={
            "user_id": current_user.id,
            "carbon_footprint_kg": estimated_carbon
        }
    )
    
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

# --- Schema (no change) ---
@router.get("/farm/{farm_id}", response_model=List[FarmActivityRead])
def get_activities_for_farm(
    farm_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    activities = db.exec(
        select(FarmActivity)
        .where(FarmActivity.farm_id == farm_id)
        .order_by(FarmActivity.date.desc())
    ).all()
    
    return activities

# --- Schema (no change) ---
@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = db.get(FarmActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    if activity.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    db.delete(activity)
    db.commit()
    return

# --- NEW SCHEMA ---
# This is the data structure we'll send to the frontend for the dashboard
class CarbonSummary(BaseModel):
    total_carbon_kg: float
    breakdown_by_activity: Dict[str, float]

# --- NEW ENDPOINT ---
@router.get("/farm/{farm_id}/carbon_summary", response_model=CarbonSummary)
def get_carbon_summary_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify user owns the farm
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Use a SQL query to get the total sum
    total_carbon = db.exec(
        select(func.sum(FarmActivity.carbon_footprint_kg))
        .where(FarmActivity.farm_id == farm_id)
    ).first()

    # Use a SQL query to get the sum for each activity_type
    breakdown_query = db.exec(
        select(
            FarmActivity.activity_type,
            func.sum(FarmActivity.carbon_footprint_kg)
        )
        .where(FarmActivity.farm_id == farm_id)
        .group_by(FarmActivity.activity_type)
    ).all()
    
    breakdown_dict = {activity: carbon for activity, carbon in breakdown_query}
    
    return CarbonSummary(
        total_carbon_kg=total_carbon or 0.0,
        breakdown_by_activity=breakdown_dict
    )