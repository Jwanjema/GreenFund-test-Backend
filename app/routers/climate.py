import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.database import get_db
from app.models import Farm, User, FarmActivity
from app.security import get_current_user
from app.recommendations import generate_recommendations

router = APIRouter(
    prefix="/climate",  # Simple prefix
    tags=["climate"],
)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@router.get("/{farm_id}/forecast")  # Path relative to router prefix
async def get_weather_forecast(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    if farm.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    activities = db.exec(
        select(FarmActivity)
        .where(FarmActivity.farm_id == farm_id)
        .order_by(FarmActivity.date.desc())
    ).all()

    params = {
        "latitude": farm.latitude,
        "longitude": farm.longitude,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            forecast_data = response.json()

            recommendations = generate_recommendations(
                forecast_data.get("daily", {}),
                activities
            )

            return {
                "forecast": forecast_data,
                "recommendations": recommendations
            }

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with weather service: {exc}"
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Received an invalid response from weather service: {exc.response.text}"
            )
