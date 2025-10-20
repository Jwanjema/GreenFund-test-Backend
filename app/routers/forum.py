# GreenFund-test-Backend/app/routers/forum.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, desc
from typing import List

from app.database import get_db
from app.models import ForumThread, ForumPost, User
from app.schemas import ( # Import specific schemas from main schemas file
    ForumThreadCreate, ForumThreadReadBasic, ForumThreadReadWithPosts,
    ForumPostCreate, ForumPostRead
)
from app.security import get_current_user

router = APIRouter(
    prefix="/forum", # Simple prefix (will be combined with /api in main.py)
    tags=["forum"],
)

# --- Thread Endpoints ---

@router.post("/threads", response_model=ForumThreadReadBasic, status_code=status.HTTP_201_CREATED)
def create_thread(
    thread_data: ForumThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new forum thread.
    """
    # Create the ForumThread instance using the input data and owner_id
    db_thread = ForumThread(**thread_data.model_dump(), owner_id=current_user.id)
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    # Eagerly load owner data for the response
    # SQLModel should handle this if relationships are set correctly
    # If not, you might need: db_thread = db.get(ForumThread, db_thread.id) # Re-fetch with relationships
    return db_thread

@router.get("/threads", response_model=List[ForumThreadReadBasic])
def get_all_threads(
    skip: int = 0,
    limit: int = 20, # Add pagination
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user) # Allow anonymous viewing
):
    """
    Gets a list of all forum threads, ordered by most recent.
    Includes basic owner information.
    """
    # Select threads and eagerly load the 'owner' relationship
    statement = (
        select(ForumThread)
        .order_by(desc(ForumThread.created_at))
        .offset(skip)
        .limit(limit)
        # Options for eager loading (if needed, depends on SQLModel/SQLAlchemy config)
        # .options(selectinload(ForumThread.owner))
    )
    threads = db.exec(statement).all()
    # SQLModel/Pydantic should handle the conversion including nested 'owner'
    return threads

@router.get("/threads/{thread_id}", response_model=ForumThreadReadWithPosts)
def get_thread_by_id(
    thread_id: int,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user) # Allow viewing
):
    """
    Gets a single forum thread by its ID, including all its posts and author info.
    Posts are ordered oldest first.
    """
    # Fetch the thread and eagerly load owner, posts, and post owners
    # This might require more complex query setup or rely on lazy loading triggering
    db_thread = db.get(ForumThread, thread_id)

    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    # Accessing relationships ensures they are loaded for the Pydantic model conversion
    # SQLModel handles this automatically if lazy loading is enabled (default)
    # For optimization, explicit loading (joinedload, selectinload) is better
    # Example: Access owner
    _ = db_thread.owner
    # Example: Access posts and their owners
    for post in db_thread.posts:
        _ = post.owner

    # Sort posts manually if needed (SQLModel doesn't directly support order_by on relationship access)
    db_thread.posts.sort(key=lambda p: p.created_at)

    return db_thread

# --- Post Endpoints ---

@router.post("/posts", response_model=ForumPostRead, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: ForumPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new post within a specific thread.
    """
    # Check if thread exists
    db_thread = db.get(ForumThread, post_data.thread_id)
    if not db_thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found, cannot post reply.")

    # Create the ForumPost instance
    db_post = ForumPost(**post_data.model_dump(), owner_id=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    # Eagerly load owner for the response
    # SQLModel should handle this
    return db_post