from fastapi import APIRouter, Depends
from app import schemas, security  # Absolute import
from app.models import User     # Absolute import

router = APIRouter()


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: User = Depends(security.get_current_user)):
    return current_user
