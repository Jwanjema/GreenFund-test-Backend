# GreenFund-test-Backend/app/schemas.py
from pydantic import BaseModel, EmailStr, Field # Add Field
from typing import Optional, List
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    location: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    # Ensure all fields from UserBase are included if needed, or inherit properly
    # If UserRead should show email, full_name, location, Pydantic handles this
    # If not, remove them from UserBase and only put them where needed

# --- Farm Schemas ---
class FarmBase(BaseModel):
    name: str
    location_text: str
    size_acres: float

class FarmCreate(FarmBase):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class FarmRead(FarmBase):
    id: int
    latitude: float # Assuming latitude/longitude become non-optional after creation
    longitude: float
    owner_id: int

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- FarmActivity Schemas ---
class FarmActivityCreate(BaseModel):
    farm_id: int
    activity_type: str
    description: Optional[str] = None
    date: Optional[datetime] = None # Allow optional date, defaults on server

class FarmActivityRead(BaseModel):
    id: int
    activity_type: str
    description: Optional[str] = None
    date: datetime
    farm_id: int
    carbon_footprint_kg: Optional[float] = None # Carbon footprint might be calculated later
    user_id: int # Added user_id

# --- SoilReport Schemas ---
class SoilReportCreate(BaseModel):
    farm_id: int
    ph: float
    nitrogen: float
    phosphorus: float
    potassium: float
    moisture: float

class SoilReportRead(BaseModel):
    id: int
    date: datetime
    # Match optional fields from model
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None
    ai_analysis_text: Optional[str] = None
    # Use Optional List, default handled by model or endpoint
    suggested_crops: Optional[List[str]] = None
    farm_id: int

    # Allow ORM mode for easy conversion from SQLModel objects
    class Config:
        orm_mode = True # Use this for Pydantic v1. If using v2+, use `from_attributes = True`


# --- NEW: Forum Schemas Start ---

# --- User Info for Embedding ---
# A lightweight schema to include basic author info in forum responses
class ForumUserBase(BaseModel):
    id: int
    full_name: Optional[str] = None

    class Config:
        orm_mode = True # Use this for Pydantic v1. If using v2+, use `from_attributes = True`


# --- Schemas for Forum Posts ---
class ForumPostBase(BaseModel):
    content: str = Field(min_length=1)

class ForumPostCreate(ForumPostBase):
    thread_id: int # Which thread this post belongs to

class ForumPostRead(ForumPostBase):
    id: int
    created_at: datetime
    owner: ForumUserBase # Embed basic owner info

    # Allow ORM mode for easy conversion from SQLModel objects
    class Config:
        orm_mode = True # Use this for Pydantic v1. If using v2+, use `from_attributes = True`

# --- Schemas for Forum Threads ---
class ForumThreadBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=10) # Initial content when creating thread

class ForumThreadCreate(ForumThreadBase):
    pass # No extra fields needed for creation

class ForumThreadReadBasic(ForumThreadBase):
    id: int
    created_at: datetime
    owner: ForumUserBase # Embed basic owner info
    # You could add post_count here later if needed

    # Allow ORM mode
    class Config:
        orm_mode = True # Use this for Pydantic v1. If using v2+, use `from_attributes = True`


class ForumThreadReadWithPosts(ForumThreadReadBasic):
    # Include posts when reading a single thread, defaults to empty list
    posts: List[ForumPostRead] = []

    # Allow ORM mode (already inherited, but explicit doesn't hurt)
    class Config:
        orm_mode = True # Use this for Pydantic v1. If using v2+, use `from_attributes = True`

# --- NEW: Forum Schemas End ---

# --- NEW: Climate Action Schemas (Optional, for more structured responses) ---
# Example - Can be expanded later
class Alert(BaseModel):
    type: str # e.g., 'Pest', 'Disease'
    name: str
    risk_level: str # e.g., 'Low', 'Medium', 'High'
    advice: str

class PestDiseaseAlertResponse(BaseModel):
    farm_id: int
    alerts: List[Alert]

class CarbonGuidanceResponse(BaseModel):
    farm_id: int
    guidance: dict # Keep as dict for now, can be refined

class WaterAdviceResponse(BaseModel):
    farm_id: int
    advice: dict # Keep as dict for now, can be refined
# --- End Climate Action Schemas ---