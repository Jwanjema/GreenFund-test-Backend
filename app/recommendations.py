import json
from typing import List, Dict, Any
from openai import APIError
from app.models import FarmActivity
from app.soil_model import get_openai_client # Back to OpenAI
# Import rules - we can reuse some
from app.climate_rules import assess_pest_disease_risks, assess_water_stress

async def generate_recommendations(
    daily_forecast: Dict[str, Any],
    activities: List[FarmActivity],
    farm_crop: str
) -> List[str]:
    """Analyzes forecast and activities using Rules + AI to generate recommendations."""

    # 1. Run Rules (reuse from climate_rules)
    # Fetch required params if not already present in daily_forecast
    # Note: This might require fetching more weather data in the climate.py endpoint
    pest_assessment = assess_pest_disease_risks(daily_forecast, farm_crop)
    water_assessment = assess_water_stress(daily_forecast)

    # 2. Ask AI for Recommendations based on Assessment
    try:
        client = get_openai_client()
        activity_summary = ", ".join(list(set([a.activity_type for a in activities[:5]]))) or "no recent activities"
        current_crop_info = f"The primary crop is {farm_crop}." if farm_crop else "The farm grows various crops."

        prompt = f"""
        You are an AI agronomist for a Kenyan farmer. {current_crop_info}
        Based on the 7-day weather forecast and recent activities ({activity_summary}), a basic assessment suggests:
        - Key Pest/Disease Risks: {json.dumps(pest_assessment) if pest_assessment else "Low / None identified"}
        - Water Stress Level: {water_assessment}

        Provide ONLY a valid JSON object (no extra text or markdown) with a single key "recommendations" which is a list of 3 short, actionable, and prioritized recommendations for the farmer this week, considering the weather forecast and the assessment above. Focus on climate adaptation and efficiency.
        """

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        response_content = completion.choices[0].message.content
        ai_data = json.loads(response_content)
        return ai_data.get("recommendations", ["AI analysis failed to generate recommendations."])

    except APIError as e:
         print(f"OpenAI API Error during recommendation generation: {e}")
         return [f"Could not generate AI recommendations due to API error."] # Return error in list format
    except Exception as e:
        print(f"Error in AI recommendation generation: {e}")
        # Optionally, return recommendations based *only* on the rules if AI fails
        # fallback_recs = []
        # if water_assessment == "High": fallback_recs.append("High water stress expected. Consider irrigation scheduling.")
        # if "Powdery Mildew" in pest_assessment: fallback_recs.append(f"Monitor crops for Powdery Mildew due to {pest_assessment['Powdery Mildew']} risk.")
        # if fallback_recs: return fallback_recs[:3]
        return ["Could not generate AI recommendations at this time."]