# GreenFund-test-Backend/app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
# --- ADD SQLModel import if not already present ---
from sqlmodel import SQLModel
# --- End Add ---

# --- User Schemas ---

class UserBase(SQLModel): # <-- Use SQLModel if you want ORM features later
    email: EmailStr
    full_name: Optional[str] = None
    location: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    # created_at: datetime # Often included in Read models

    class Config:
        from_attributes = True

# --- vvvvvvvvvvvvvvvvvvvvvvvvvvv ---
# --- ADD THIS USER UPDATE SCHEMA ---
# --- vvvvvvvvvvvvvvvvvvvvvvvvvvv ---
class UserUpdate(SQLModel): # Use SQLModel here too
    # Fields that the user is allowed to update
    # Optional[] means the field doesn't have to be sent in the request
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None # Allowing email change requires careful handling (e.g., verification)
    location: Optional[str] = None
# --- ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ---
# --- END ADDITION              ---
# --- ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ---


# --- Farm Schemas ---
# ... (rest of your Farm schemas) ...
class FarmBase(SQLModel): # <-- Consider using SQLModel for consistency
    name: str
    location_text: str
    size_acres: Optional[float] = None # Made optional based on models.py
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_crop: Optional[str] = None

class FarmCreate(FarmBase):
    pass # No extra fields needed beyond FarmBase for creation based on your models

class FarmRead(FarmBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Token Schemas ---
# ... (rest of your Token schemas) ...
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- FarmActivity Schemas ---
# ... (rest of your FarmActivity schemas) ...
class FarmActivityBase(SQLModel): # <-- Use SQLModel
    activity_type: str
    description: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=datetime.utcnow) # Set default date
    value: Optional[float] = None # Made optional
    unit: Optional[str] = None    # Made optional

class FarmActivityCreate(FarmActivityBase):
    farm_id: int

class FarmActivityRead(FarmActivityBase):
    id: int
    farm_id: int
    user_id: int
    carbon_footprint_kg: Optional[float] = None
    date: datetime # Make date required for reading

    class Config:
        from_attributes = True


# --- SoilReport Schemas ---
# ... (rest of your SoilReport schemas) ...
class SoilReportBase(SQLModel): # <-- Use SQLModel
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    moisture: Optional[float] = None

class SoilReportCreate(SoilReportBase):
    farm_id: int

class SoilReportRead(SoilReportBase):
    id: int
    farm_id: int
    date: datetime
    ai_analysis_text: Optional[str] = None
    suggested_crops: Optional[List[str]] = None

    class Config:
        from_attributes = True


# --- Forum Schemas ---
# ... (rest of your Forum schemas) ...
# (Consider using SQLModel here too if Forum models inherit from SQLModel)
class ForumUserBase(BaseModel):
    id: int
    full_name: Optional[str] = None
    class Config: from_attributes = True

class ForumPostBase(BaseModel):
    content: str = Field(min_length=1)

class ForumPostCreate(ForumPostBase):
    thread_id: int

class ForumPostRead(ForumPostBase):
    id: int
    created_at: datetime
    owner: ForumUserBase
    class Config: from_attributes = True

class ForumThreadBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=10)

class ForumThreadCreate(ForumThreadBase):
    pass

class ForumThreadReadBasic(ForumThreadBase):
    id: int
    created_at: datetime
    owner: ForumUserBase
    posts: List[ForumPostRead] = []
    class Config: from_attributes = True

class ForumThreadReadWithPosts(ForumThreadReadBasic):
    posts: List[ForumPostRead] = []
    class Config: from_attributes = True


# --- Climate Action Schemas ---
# ... (rest of your Climate Action schemas) ...
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
    guidance: dict # Consider defining a specific Guidance schema

class WaterAdviceResponse(BaseModel):
    farm_id: int
    advice: dict # Consider defining a specific Advice schema