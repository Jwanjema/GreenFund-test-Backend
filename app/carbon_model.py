from typing import Optional

# This is a very simple "model" using placeholder values.
# In a real-world app, this would be a complex system that
# might parse the description for (e.g., "50kg", "diesel tractor").
EMISSION_FACTORS = {
    "Planting": 1.5,
    "Irrigation": 2.2,
    "Fertilizing": 10.0, # Synthetic fertilizers have a high footprint
    "Pest Control": 3.0,
    "Harvesting": 1.8,
    "Other": 0.5,
}

def estimate_carbon_footprint(activity_type: str, description: Optional[str] = None) -> float:
    """
    Estimates the carbon footprint for a given farm activity.
    """
    # We just use the base factor for now.
    return EMISSION_FACTORS.get(activity_type, 0.5)