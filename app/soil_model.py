import os
import json
import httpx
from openai import AsyncOpenAI
from typing import Dict, Any, List
from fastapi import HTTPException, status

# --- OpenAI (Manual Entry) Setup ---
try:
    openai_client = AsyncOpenAI()
except Exception as e:
    print(
        f"Warning: OpenAI client could not be initialized. API key might be missing. {e}")
    openai_client = None

# --- Hugging Face (Image Upload) Setup ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/diego0020/_Soil_Classification"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# --- 1. OpenAI Logic (Manual Entry) ---


def get_system_prompt() -> str:
    return """
    You are an expert agronomist and soil scientist specializing in Kenyan agriculture.
    Your goal is to provide concise, actionable, and encouraging advice to smallholder farmers.
    The user will provide soil data in JSON format. You must:
    1.  Provide a brief "ai_analysis_text" (as a single string).
    2.  Provide a list of "suggested_crops" (as a JSON list of strings).
    Your response MUST be in a valid JSON format.
    """


def create_user_prompt(data: Dict[str, float]) -> str:
    return f"""
    Here is my soil test data from my farm in Kenya:
    - pH: {data['ph']}
    - Nitrogen (N): {data['nitrogen']} ppm
    - Phosphorus (P): {data['phosphorus']} ppm
    - Potassium (K): {data['potassium']} ppm
    - Moisture: {data['moisture']}%
    Please provide your analysis and crop suggestions in the required JSON format.
    """


async def analyze_soil_with_ai(data: Dict[str, float]) -> Dict[str, Any]:
    if not openai_client:
        raise ValueError("OpenAI client is not configured (API key missing?)")

    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": create_user_prompt(data)}
            ]
        )
        response_content = completion.choices[0].message.content
        ai_results = json.loads(response_content)
        return ai_results

    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        raise ValueError(f"Failed to get AI analysis: {e}")

# --- 2. Hugging Face Logic (Image Upload) ---


def get_ai_advice_for_soil_type(soil_type: str) -> Dict[str, Any]:
    """
    A simple rule-based engine to give advice based on the classified soil type.
    """
    soil_type = soil_type.lower().replace("_", " ")
    analysis = ""
    crops = []

    if "black soil" in soil_type:
        analysis = "This looks like rich Black Soil (often called 'Black Cotton Soil' in Kenya). This is excellent, nutrient-rich soil, great for holding moisture. It can be heavy when wet, but is very fertile."
        crops = ["Maize", "Beans", "Sorghum", "Cotton", "Sugarcane", "Wheat"]
    elif "clay soil" in soil_type:
        analysis = "This looks like Clay Soil. It holds water very well but can be heavy, poorly drained, and hard to work. Adding organic compost and sand can improve its texture."
        crops = ["Cabbage", "Kale (Sukuma Wiki)",
                 "Beans", "Potatoes", "Sugarcane"]
    elif "red soil" in soil_type:
        analysis = "This appears to be Red Soil (often lateritic). It's common in many parts of Kenya. It drains well but can be acidic and low in nutrients. Adding lime and plenty of compost/manure is crucial."
        crops = ["Tea", "Coffee", "Cassava",
                 "Millet", "Groundnuts", "Pineapples"]
    elif "rice soil" in soil_type:
        analysis = "This looks like soil from a rice paddy or a seasonally waterlogged area (like a vlei or mbuga). It is heavy and holds water. If not used for rice, it needs significant drainage improvements."
        crops = ["Rice", "Taro (Arrowroot)", "Sugarcane"]
    elif "sand soil" in soil_type:
        analysis = "This appears to be Sandy Soil. It drains very quickly, warms up fast, but doesn't hold nutrients or water well. Frequent watering and adding lots of compost are essential."
        crops = ["Carrots", "Sweet Potatoes", "Groundnuts",
                 "Sorghum", "Millet", "Watermelon"]
    else:
        analysis = f"The soil is classified as {soil_type}. It's always a good idea to test its pH and add organic matter like compost or manure to improve its structure and fertility."
        crops = ["Cabbage", "Potatoes", "Beans"]

    return {
        "ai_analysis_text": analysis,
        "suggested_crops": crops
    }


async def analyze_soil_image_with_ai(image_data: bytes) -> Dict[str, Any]:
    """
    Makes the API call to Hugging Face to classify the soil image.
    """
    if not HF_API_TOKEN:
        raise ValueError("Hugging Face API token is not configured.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                HF_MODEL_URL,
                headers=HF_HEADERS,
                content=image_data,
                timeout=30.0
            )
            response.raise_for_status()

            hf_results = response.json()

            if not hf_results:
                raise ValueError("AI model returned an empty response.")

            top_result = max(hf_results, key=lambda x: x['score'])
            soil_type = top_result['label']

            ai_advice = get_ai_advice_for_soil_type(soil_type)

            ai_advice.update({
                "ph": 0.0,
                "nitrogen": 0,
                "phosphorus": 0,
                "potassium": 0,
                "moisture": 0,
            })

            return ai_advice

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                raise HTTPException(
                    status_code=503, detail="AI model is loading, please try again in a moment.")
            elif e.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="Soil image classification model not found. Please try again later.")
            print(f"Error calling Hugging Face: {e}")
            raise ValueError(
                f"Failed to analyze image with AI: {e.response.text}")
        except Exception as e:
            print(f"Error processing Hugging Face response: {e}")
            raise ValueError(f"Failed to process AI response: {e}")
