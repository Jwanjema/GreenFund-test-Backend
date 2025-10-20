# GreenFund-test-Backend/app/models.py
from sqlmodel import Field, Relationship, SQLModel, JSON
from sqlalchemy import Column # Keep this import
from typing import Optional, List, TYPE_CHECKING # Add TYPE_CHECKING
from datetime import datetime, timezone # Import timezone


# --- Forward References ---
# Use TYPE_CHECKING to avoid circular import issues with relationships
if TYPE_CHECKING:
    from .models import User, Farm, FarmActivity, SoilReport, ForumThread, ForumPost

# --- User Model (Updated) ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Changed full_name back to optional to match previous schema fixes
    full_name: Optional[str] = None
    email: str = Field(unique=True, index=True)
    hashed_password: str
    location: Optional[str] = None
    # Use timezone-aware datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Existing Relationships
    farms: List["Farm"] = Relationship(back_populates="owner")
    activities: List["FarmActivity"] = Relationship(back_populates="user")

    # --- NEW: Forum Relationships ---
    threads: List["ForumThread"] = Relationship(back_populates="owner") # Threads created by user
    posts: List["ForumPost"] = Relationship(back_populates="owner") # Posts created by user
    # --- End New ---

# --- Farm Model (No changes needed) ---
class Farm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    location_text: str
    latitude: float
    longitude: float
    size_acres: float
    # Use timezone-aware datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    owner_id: int = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="farms")

    activities: List["FarmActivity"] = Relationship(back_populates="farm")
    soil_reports: List["SoilReport"] = Relationship(back_populates="farm")


# --- FarmActivity Model (No changes needed) ---
class FarmActivity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_type: str
    description: Optional[str] = None
    # Use timezone-aware datetime
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    carbon_footprint_kg: Optional[float] = None

    farm_id: int = Field(foreign_key="farm.id")
    farm: "Farm" = Relationship(back_populates="activities")

    user_id: int = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="activities")

# --- SoilReport Model (Minor type hint/default fixes) ---
class SoilReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Use timezone-aware datetime
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Make fields optional to match previous fixes for image analysis
    ph: Optional[float] = Field(default=None)
    nitrogen: Optional[float] = Field(default=None)
    phosphorus: Optional[float] = Field(default=None)
    potassium: Optional[float] = Field(default=None)
    moisture: Optional[float] = Field(default=None)
    ai_analysis_text: Optional[str] = None
    # Ensure correct type hint and default for JSON field
    suggested_crops: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    farm_id: int = Field(foreign_key="farm.id")
    farm: "Farm" = Relationship(back_populates="soil_reports")


# --- NEW: Forum Thread Model ---
class ForumThread(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str # Initial content of the thread
    # Use timezone-aware datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: int = Field(foreign_key="user.id")

    # Relationship to the User who created the thread
    owner: "User" = Relationship(back_populates="threads")
    # Relationship to the Posts within this thread
    posts: List["ForumPost"] = Relationship(back_populates="thread")
# --- End New ---


# --- NEW: Forum Post Model ---
class ForumPost(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    # Use timezone-aware datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: int = Field(foreign_key="user.id")
    thread_id: int = Field(foreign_key="forumthread.id") # Matches ForumThread table name

    # Relationship to the User who created the post
    owner: "User" = Relationship(back_populates="posts")
    # Relationship back to the Thread this post belongs to
    thread: "ForumThread" = Relationship(back_populates="posts")
# --- End New ---