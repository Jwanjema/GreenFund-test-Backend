# GreenFund-test-Backend/app/schemas.py
from pydantic import BaseModel, EmailStr, Field
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

    class Config:
        from_attributes = True

# --- Farm Schemas ---


class FarmBase(BaseModel):
    name: str
    location_text: str
    size_acres: float


class FarmCreate(FarmBase):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_crop: Optional[str] = None


class FarmRead(FarmBase):
    id: int
    latitude: float
    longitude: float
    owner_id: int
    current_crop: Optional[str] = None

    class Config:
        from_attributes = True

# --- Token Schemas ---


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None

# --- FarmActivity Schemas (Updated) ---


class FarmActivityCreate(BaseModel):
    farm_id: int
    activity_type: str
    description: Optional[str] = None
    date: Optional[datetime] = None
    # --- NEW FIELDS ---
    value: float
    unit: str
    # --- END NEW ---


class FarmActivityRead(BaseModel):
    id: int
    activity_type: str
    description: Optional[str] = None
    date: datetime
    farm_id: int
    carbon_footprint_kg: Optional[float] = None
    user_id: int

    class Config:
        from_attributes = True

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
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None
    ai_analysis_text: Optional[str] = None
    suggested_crops: Optional[List[str]] = None
    farm_id: int

    class Config:
        from_attributes = True

# --- Forum Schemas ---


class ForumUserBase(BaseModel):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class ForumPostBase(BaseModel):
    content: str = Field(min_length=1)


class ForumPostCreate(ForumPostBase):
    thread_id: int


class ForumPostRead(ForumPostBase):
    id: int
    created_at: datetime
    owner: ForumUserBase

    class Config:
        from_attributes = True


class ForumThreadBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=10)


class ForumThreadCreate(ForumThreadBase):
    pass


class ForumThreadReadBasic(ForumThreadBase):
    id: int
    created_at: datetime
    owner: ForumUserBase
    posts: List[ForumPostRead] = []  # Include posts to get reply count

    class Config:
        from_attributes = True


class ForumThreadReadWithPosts(ForumThreadReadBasic):
    posts: List[ForumPostRead] = []

    class Config:
        from_attributes = True

# --- Climate Action Schemas ---


class Alert(BaseModel):
    type: str
    name: str
    risk_level: str
    advice: str


class PestDiseaseAlertResponse(BaseModel):
    farm_id: int
    alerts: List[Alert]


class CarbonGuidanceResponse(BaseModel):
    farm_id: int
    guidance: dict


class WaterAdviceResponse(BaseModel):
    farm_id: int
    advice: dict
