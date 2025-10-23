# GreenFund-test-Backend-backup/app/routers/climate_actions.py
import httpx
import json
import asyncio # <-- Make sure asyncio is imported
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, desc
from openai import APIError

from app.database import get_db
from app.models import Farm, User, FarmActivity, SoilReport
from app.security import get_current_user
from app.schemas import PestDiseaseAlertResponse, CarbonGuidanceResponse, WaterAdviceResponse
from app.soil_model import get_openai_client
from app.climate_rules import assess_pest_disease_risks, assess_water_stress, assess_carbon_trend

router = APIRouter(prefix="/climate-actions", tags=["Climate Actions"])

# --- vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv ---
# --- UPDATED WEATHER FETCH FUNCTION ---
# --- vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv ---
async def _fetch_weather_data(latitude: float, longitude: float, daily_params: str):
    """Fetches weather data from Open-Meteo with basic retries."""
    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": latitude, "longitude": longitude, "daily": daily_params, "timezone": "auto"}
    max_retries = 2 # Try original request + 2 retries
    base_delay = 1 # Start with 1 second delay between retries

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                # Increased timeout to 15 seconds
                response = await client.get(WEATHER_API_URL, params=params, timeout=15.0)
                response.raise_for_status() # Raise exception for bad status codes (4xx, 5xx)
                # Return the 'daily' data, or an empty dict if missing
                return response.json().get("daily", {})
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"WARN: Attempt {attempt + 1}/{max_retries + 1} failed to fetch weather: {e}")
            if attempt == max_retries:
                # If this was the last attempt, raise the final HTTP Exception
                if isinstance(e, httpx.HTTPStatusError):
                    print(f"ERROR: Open-Meteo API returned status {e.response.status_code} after retries: {e.response.text}")
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Weather service error after retries.")
                else: # Handles httpx.RequestError (connection, timeout, etc.)
                     print(f"ERROR: Could not connect to Open-Meteo API after {max_retries + 1} attempts: {e}")
                     raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not connect to the weather service after retries.")
            # Wait before the next retry (e.g., 1s, 2s, 4s)
            await asyncio.sleep(base_delay * (2 ** attempt))
        except Exception as e:
            # Catch any other unexpected errors during fetch/parsing
            print(f"ERROR: An unexpected error occurred during weather fetch: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred fetching weather data.")
    # This line should technically be unreachable if retries/exceptions work correctly
    raise HTTPException(status_code=500, detail="Weather fetch failed unexpectedly after retries.")
# --- ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ---
# --- END UPDATED FUNCTION        ---
# --- ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ---


@router.get("/alerts/{farm_id}", response_model=PestDiseaseAlertResponse)
async def get_pest_disease_alerts(farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farm = db.get(Farm, farm_id)
    if not farm: raise HTTPException(status_code=404, detail="Farm not found")

    # 1. Fetch weather (now uses retry logic)
    weather_params = "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean"
    try:
        forecast_data = await _fetch_weather_data(farm.latitude, farm.longitude, weather_params)
    except HTTPException as http_exc:
         # If weather fetch fails after retries, re-raise the specific error
         raise http_exc
    except Exception as e:
        # Catch any other unexpected error during the fetch call
        print(f"ERROR: Unexpected error calling _fetch_weather_data for alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve weather data for alerts.")


    # 2. Run Rules
    pest_risk_assessment = assess_pest_disease_risks(forecast_data, farm.current_crop)

    # 3. Ask AI for Refined Advice
    try:
        client = get_openai_client()
        current_crop_info = f"The farm is growing: {farm.current_crop}." if farm.current_crop else "The farm grows various crops."
        prompt = f"""
        You are an AI agronomist advising a Kenyan farmer. {current_crop_info}
        A basic analysis suggests the following pest/disease risks for the next 7 days based on weather:
        {json.dumps(pest_risk_assessment) if pest_risk_assessment else "No significant risks identified by basic rules."}

        Refine this assessment. Provide ONLY a valid JSON object (no extra text or markdown) with a key "alerts" which is a list.
        For each significant risk (prioritize 'High' or 'Medium'), provide: "type" (Pest/Disease), "name", "risk_level" (Low/Medium/High), and concise, actionable "advice" suitable for a smallholder farmer in Kenya. Limit to the top 2 most relevant alerts based on the assessment.
        If the assessment is empty, return an empty list for "alerts".
        """
        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        response_content = completion.choices[0].message.content
        ai_data = json.loads(response_content)
        alerts_data = ai_data.get("alerts", [])
    except APIError as e:
        print(f"ERROR: OpenAI API error during pest analysis: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=f"AI pest analysis failed: {getattr(e, 'message', str(e))}")
    except Exception as e:
        print(f"ERROR: Unexpected error during AI pest analysis refinement: {e}")
        raise HTTPException(status_code=500, detail=f"AI pest analysis refinement failed: {e}")

    return PestDiseaseAlertResponse(farm_id=farm_id, alerts=alerts_data)


@router.get("/carbon-guidance/{farm_id}", response_model=CarbonGuidanceResponse)
async def get_carbon_sequestration_guidance(farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farm = db.get(Farm, farm_id)
    if not farm: raise HTTPException(status_code=404, detail="Farm not found")

    # Fetch Farm Data
    activities = db.exec(select(FarmActivity).where(FarmActivity.farm_id == farm_id).order_by(desc(FarmActivity.date)).limit(10)).all()

    # Run Rules
    carbon_trend_assessment = assess_carbon_trend(activities)

    # Ask AI for Refined Advice
    try:
        client = get_openai_client()
        activity_summary = ", ".join(list(set([a.activity_type for a in activities]))) or "no activities logged"
        prompt = f"""
        You are an AI agronomist advising a Kenyan farmer on soil carbon.
        Farm Details: Crop={farm.current_crop or 'N/A'}, Recent Activities Summary={activity_summary}.
        A basic assessment based on recent activities suggests the carbon trend is: "{carbon_trend_assessment}".

        Provide guidance. Return ONLY a valid JSON object (no extra text or markdown) with two keys:
        1. "estimated_current_seq_rate": A refined qualitative estimate (e.g., "Low, potential to improve", "Moderate", "High based on practices").
        2. "recommendations": A list of 3 specific, actionable soil carbon improvement recommendations relevant to Kenyan smallholder farming, considering the basic trend assessment.
        """
        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        response_content = completion.choices[0].message.content
        guidance_data = json.loads(response_content)
    except APIError as e:
        print(f"ERROR: OpenAI API error during carbon analysis: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=f"AI carbon analysis failed: {getattr(e, 'message', str(e))}")
    except Exception as e:
        print(f"ERROR: Unexpected error during AI carbon analysis refinement: {e}")
        raise HTTPException(status_code=500, detail=f"AI carbon analysis refinement failed: {e}")

    return CarbonGuidanceResponse(farm_id=farm_id, guidance=guidance_data)


@router.get("/water-management/{farm_id}", response_model=WaterAdviceResponse)
async def get_water_management_advice(farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farm = db.get(Farm, farm_id)
    if not farm: raise HTTPException(status_code=404, detail="Farm not found")

    # 1. Fetch weather (now uses retry logic)
    weather_params = "precipitation_sum,et0_fao_evapotranspiration"
    try:
        forecast_data = await _fetch_weather_data(farm.latitude, farm.longitude, weather_params)
    except HTTPException as http_exc:
        # If weather fetch fails after retries, re-raise the specific error
        raise http_exc
    except Exception as e:
        # Catch any other unexpected error during the fetch call
        print(f"ERROR: Unexpected error calling _fetch_weather_data for water advice: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve weather data for water advice.")


    # 2. Run Rules
    water_stress_assessment = assess_water_stress(forecast_data)

    # 3. Ask AI for Refined Advice
    try:
        client = get_openai_client()
        current_crop_info = f"The farm grows: {farm.current_crop}." if farm.current_crop else ""
        prompt = f"""
        You are an AI agronomist advising a Kenyan farmer on water management. {current_crop_info}
        A basic analysis suggests the water stress level for the next 7 days is: "{water_stress_assessment}".
        Weather Forecast Snippet: {json.dumps(forecast_data)}

        Provide advice based on the assessment and forecast. Return ONLY a valid JSON object (no extra text or markdown) with three keys:
        1. "next_7_days_outlook": A brief (1 sentence) summary based on the assessment.
        2. "irrigation_advice": One specific, actionable irrigation tip for the week, considering the stress level and forecast (e.g., amount, timing).
        3. "tips": A list of 2 short, practical water-saving tips relevant to the assessment (e.g., mulching if stress is High, checking for leaks).
        """
        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        response_content = completion.choices[0].message.content
        advice_data = json.loads(response_content)
    except APIError as e:
        print(f"ERROR: OpenAI API error during water analysis: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=f"AI water analysis failed: {getattr(e, 'message', str(e))}")
    except Exception as e:
        print(f"ERROR: Unexpected error during AI water analysis refinement: {e}")
        raise HTTPException(status_code=500, detail=f"AI water analysis refinement failed: {e}")

    return WaterAdviceResponse(farm_id=farm_id, advice=advice_data)