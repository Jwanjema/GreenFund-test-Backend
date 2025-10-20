from typing import List, Dict, Any
from app.models import FarmActivity
from datetime import datetime, timedelta

def generate_recommendations(
    daily_forecast: Dict[str, Any], 
    activities: List[FarmActivity]
) -> List[str]:
    """
    Analyzes a 7-day forecast AND recent farm activities
    to generate smart recommendations.
    """
    recommendations = set()

    # --- 1. Analyze Weather (Existing Logic) ---
    max_temps = daily_forecast.get("temperature_2m_max", [])
    min_temps = daily_forecast.get("temperature_2m_min", [])
    precipitation = daily_forecast.get("precipitation_sum", [])
    
    if any(temp > 30 for temp in max_temps):
        recommendations.add("🌡️ High temperatures detected. Ensure crops have adequate water and check for signs of heat stress.")
    
    if any(temp < 5 for temp in min_temps):
        recommendations.add("❄️ Low temperatures detected. Protect sensitive crops from potential frost damage, especially overnight.")
    
    total_precipitation = sum(precipitation)
    
    if any(precip > 10 for precip in precipitation):
        recommendations.add("💧 Heavy rainfall is expected. Ensure proper drainage to prevent waterlogging and check for soil erosion.")
    
    if total_precipitation < 2:
        recommendations.add("☀️ A dry week is expected. Plan your irrigation schedule to conserve water but avoid crop dehydration.")

    # --- 2. Analyze Activities (New Logic) ---
    now = datetime.utcnow()
    recent_activities = [
        act for act in activities 
        if act.date > (now - timedelta(days=7))
    ]

    # Rule: Check for high-carbon activities
    high_carbon_activities = [
        act.activity_type for act in recent_activities 
        if act.activity_type == "Fertilizing"
    ]
    if high_carbon_activities:
        recommendations.add("💨 You recently used fertilizer, which has a high carbon footprint. Consider switching to organic compost to improve soil health and reduce emissions.")

    # Rule: Check planting activity against rain forecast
    planted_recently = any(act.activity_type == "Planting" for act in recent_activities)
    
    if planted_recently and total_precipitation < 2:
        recommendations.add("🌱 You've planted recently during a forecasted dry week. Ensure your new seeds get critical irrigation to help them germinate.")
    
    if planted_recently and any(precip > 10 for precip in precipitation):
        recommendations.add("🌱 You've planted recently, and heavy rain is coming. Be sure to check for seed washout or soil erosion in your new plots.")
        
    # Rule: Check for inactivity
    if not recent_activities:
        recommendations.add("🤔 No activities logged this week. Remember to log your activities to get more accurate insights and track your carbon footprint.")

    # Rule: Default message if conditions are mild and no major activities
    if not recommendations:
        recommendations.add("✅ Weather looks stable and no critical actions detected. It's a good week for routine farm activities.")

    return list(recommendations)