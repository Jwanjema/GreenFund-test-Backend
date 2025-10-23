from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select, desc
from typing import List

from app.database import get_db
from app.models import Farm, SoilReport, User
from app.schemas import SoilReportCreate, SoilReportRead
from app.security import get_current_user
from app.soil_model import analyze_soil_with_ai, analyze_soil_image_with_ai

# --- THIS IS THE FIX ---
# Ensure the router object is created correctly
router = APIRouter(prefix="/soil", tags=["Soil"])
# --- END FIX ---


@router.post("/manual", response_model=SoilReportRead, status_code=status.HTTP_201_CREATED)
async def create_soil_report_manual(
    report_data: SoilReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, report_data.farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or not owned by user")

    try:
        # Get AI analysis based on numerical data
        ai_analysis_data = await analyze_soil_with_ai(report_data.model_dump())
        
        # Combine input data with AI results
        full_report_data = report_data.model_dump()
        full_report_data.update(ai_analysis_data)
        
        db_report = SoilReport.model_validate(full_report_data)
        
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI analysis failed: {e}")
    except Exception as e:
        db.rollback() # Rollback in case of other errors during save
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save soil report: {e}")


@router.post("/upload_soil_image/{farm_id}", response_model=SoilReportRead, status_code=status.HTTP_201_CREATED)
async def upload_soil_image_analysis(
    farm_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or not owned by user")

    if not file.content_type.startswith("image/"):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Please upload an image.")

    try:
        image_data = await file.read()
        
        # Get AI analysis based on image data
        ai_analysis_data = await analyze_soil_image_with_ai(image_data)
        
        # Prepare data for saving
        full_report_data = {
            "farm_id": farm_id,
            "ph": ai_analysis_data.get("ph", 0.0), # Use placeholders from AI function
            "nitrogen": ai_analysis_data.get("nitrogen", 0),
            "phosphorus": ai_analysis_data.get("phosphorus", 0),
            "potassium": ai_analysis_data.get("potassium", 0),
            "moisture": ai_analysis_data.get("moisture", 0),
            "ai_analysis_text": ai_analysis_data.get("ai_analysis_text"),
            "suggested_crops": ai_analysis_data.get("suggested_crops"),
        }
        
        db_report = SoilReport.model_validate(full_report_data)
        
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI image analysis failed: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not process image or save report: {e}")


@router.get("/farm/{farm_id}", response_model=List[SoilReportRead])
def get_soil_reports_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm or farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found or not owned by user")
    
    reports = db.exec(
        select(SoilReport)
        .where(SoilReport.farm_id == farm_id)
        .order_by(desc(SoilReport.date)) # Order by date descending
    ).all()
    
    return reports