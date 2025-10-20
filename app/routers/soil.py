# GreenFund-test-Backend/app/routers/soil.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import SoilReport, User, Farm
from app.schemas import SoilReportCreate, SoilReportRead
from app.security import get_current_user
from app.soil_model import analyze_soil_with_ai, analyze_soil_image_with_ai

router = APIRouter(
    prefix="/soil", # Keep prefix simple here
    tags=["soil"],
)

# Endpoint 1: Analyze MANUAL text data
@router.post("/manual", response_model=SoilReportRead, status_code=status.HTTP_201_CREATED)
async def create_soil_report_manual(
    report: SoilReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, report.farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        ai_input = report.model_dump()
        ai_results = await analyze_soil_with_ai(ai_input) # Call OpenAI
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    db_report = SoilReport.model_validate(
        report,
        update=ai_results
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

# Endpoint 2: Analyze UPLOADED image data (New Path)
@router.post("/upload_soil_image/{farm_id}", response_model=SoilReportRead, status_code=status.HTTP_201_CREATED)
async def create_soil_report_image(
    farm_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    image_data = await file.read()

    try:
        ai_results = await analyze_soil_image_with_ai(image_data) # Call Hugging Face
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except HTTPException as e: # Catch the 503 "model loading" error
        raise e

    db_report_data = ai_results
    db_report_data["farm_id"] = farm_id

    db_report = SoilReport.model_validate(db_report_data)

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


# Endpoint 3: Get all reports for a farm
@router.get("/farm/{farm_id}", response_model=List[SoilReportRead])
def get_reports_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    reports = db.exec(
        select(SoilReport)
        .where(SoilReport.farm_id == farm_id)
        .order_by(SoilReport.date.desc())
    ).all()

    return reports