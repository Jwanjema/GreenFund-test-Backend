from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List # This import might be needed if you add more user routes

from app.database import get_db
from app.models import User
# Import the new UserUpdate schema
from app.schemas import UserRead, UserUpdate
from app.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the details of the currently authenticated user.
    """
    return current_user

# --- NEW ENDPOINT ADDED ---
@router.put("/me", response_model=UserRead)
def update_users_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the details (full_name, email, location) of the currently authenticated user.
    """
    # Get the data from the Pydantic model
    # exclude_unset=True means we only update fields that were actually sent
    update_data = user_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    # Check for email conflict if email is being changed
    if "email" in update_data and update_data["email"] != current_user.email:
        existing_user = db.exec(select(User).where(User.email == update_data["email"])).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered by another user")

    # Update the user object in memory
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    try:
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        print(f"Error updating user: {e}") # For server logs
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update user details")