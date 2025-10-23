from fastapi import APIRouter, Depends
from app.models import User
from app.schemas import UserRead
from app.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the details of the currently authenticated user.
    """
    return current_user
