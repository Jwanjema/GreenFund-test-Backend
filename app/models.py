# GreenFund-test-Backend/app/models.py
from sqlmodel import Field, Relationship, SQLModel, JSON
from sqlalchemy import Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

# --- Forward References ---
if TYPE_CHECKING:
    from .models import User, Farm, FarmActivity, SoilReport, ForumThread, ForumPost

# --- User Model ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = None
    email: str = Field(unique=True, index=True)
    hashed_password: str
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    farms: List["Farm"] = Relationship(back_populates="owner")
    activities: List["FarmActivity"] = Relationship(back_populates="user")
    threads: List["ForumThread"] = Relationship(back_populates="owner")
    posts: List["ForumPost"] = Relationship(back_populates="owner")

# --- Farm Model (Updated) ---
class Farm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    location_text: str
    latitude: float
    longitude: float
    size_acres: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # --- THIS FIELD WAS ADDED ---
    current_crop: Optional[str] = Field(default=None, index=True) 
    # --- END OF ADDITION ---

    owner_id: int = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="farms")

    activities: List["FarmActivity"] = Relationship(back_populates="farm")
    soil_reports: List["SoilReport"] = Relationship(back_populates="farm")


# --- FarmActivity Model ---
class FarmActivity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_type: str
    description: Optional[str] = None
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    carbon_footprint_kg: Optional[float] = None
    farm_id: int = Field(foreign_key="farm.id")
    farm: "Farm" = Relationship(back_populates="activities")
    user_id: int = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="activities")

# --- SoilReport Model ---
class SoilReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ph: Optional[float] = Field(default=None)
    nitrogen: Optional[float] = Field(default=None)
    phosphorus: Optional[float] = Field(default=None)
    potassium: Optional[float] = Field(default=None)
    moisture: Optional[float] = Field(default=None)
    ai_analysis_text: Optional[str] = None
    suggested_crops: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    farm_id: int = Field(foreign_key="farm.id")
    farm: "Farm" = Relationship(back_populates="soil_reports")


# --- ForumThread Model ---
class ForumThread(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: int = Field(foreign_key="user.id")

    owner: "User" = Relationship(back_populates="threads")
    posts: List["ForumPost"] = Relationship(back_populates="thread")

# --- ForumPost Model ---
class ForumPost(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: int = Field(foreign_key="user.id")
    thread_id: int = Field(foreign_key="forumthread.id")

    owner: "User" = Relationship(back_populates="posts")
    thread: "ForumThread" = Relationship(back_populates="posts")