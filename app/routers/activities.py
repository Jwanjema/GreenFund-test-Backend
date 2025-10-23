# GreenFund-test-Backend-backup/app/routers/activities.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timezone # Import timezone

from app.database import get_db
from app.models import FarmActivity, User, Farm
from app.schemas import FarmActivityCreate, FarmActivityRead
from app.security import get_current_user
from app.carbon_model import estimate_carbon_with_ai # Using OpenAI version

router = APIRouter(prefix="/activities", tags=["Activities"])

@router.post("/", response_model=FarmActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity: FarmActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, activity.farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    # Estimate carbon using AI
    estimated_carbon = await estimate_carbon_with_ai(
        activity.activity_type,
        activity.value,
        activity.unit,
        activity.description
    )

    # --- THIS IS THE CORRECTED DATE HANDLING ---
    # Create a dictionary from the input data
    activity_data = activity.model_dump()

    # Ensure the date is set *before* validation if it's missing or None
    if activity_data.get("date") is None:
        activity_data["date"] = datetime.now(timezone.utc) # Use timezone-aware UTC now

    # Add user_id and carbon estimate before validation
    activity_data["user_id"] = current_user.id
    activity_data["carbon_footprint_kg"] = estimated_carbon

    # Now validate the complete data including the guaranteed date
    try:
        db_activity = FarmActivity.model_validate(activity_data)
    except Exception as e: # Catch potential validation errors explicitly
         print(f"ERROR: Validation failed for FarmActivity: {e}")
         print(f"Data causing validation error: {activity_data}")
         raise HTTPException(status_code=422, detail=f"Invalid activity data: {e}")
    # --- END CORRECTION ---

    # Add to DB session, commit, and refresh
    try:
        db.add(db_activity)
        db.commit()
        db.refresh(db_activity)
        return db_activity
    except Exception as e:
        db.rollback() # Rollback DB changes if commit fails
        print(f"ERROR: Failed to save activity to DB: {e}")
        raise HTTPException(status_code=500, detail="Could not save activity to database.")


# --- (The rest of the file remains the same) ---

@router.get("/farm/{farm_id}", response_model=List[FarmActivityRead])
def get_activities_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Farm not found")

    activities = db.exec(
        select(FarmActivity)
        .where(FarmActivity.farm_id == farm_id)
        .order_by(FarmActivity.date.desc())
    ).all()
    return activities

@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = db.get(FarmActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if activity.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(activity)
    db.commit()
    return

class CarbonSummary(BaseModel):
    total_carbon_kg: float
    breakdown_by_activity: Dict[str, float]

@router.get("/farm/{farm_id}/carbon_summary", response_model=CarbonSummary)
def get_carbon_summary_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Farm not found")

    total_carbon = db.exec(
        select(func.sum(FarmActivity.carbon_footprint_kg))
        .where(FarmActivity.farm_id == farm_id)
    ).first()

    breakdown_query = db.exec(
        select(
            FarmActivity.activity_type,
            func.sum(FarmActivity.carbon_footprint_kg)
        )
        .where(FarmActivity.farm_id == farm_id)
        .group_by(FarmActivity.activity_type)
    ).all()

    breakdown_dict = {activity: carbon for activity, carbon in breakdown_query if carbon is not None}

    return CarbonSummary(
        total_carbon_kg=total_carbon or 0.0,
        breakdown_by_activity=breakdown_dict
    )