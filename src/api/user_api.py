import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database.postgres import get_db
from src.database.models import User
from src.schemas.user import UserCreate, UserResponse
from src.cache.redis_cache import cache

router = APIRouter(prefix="/user", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(request: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user profile with demographic and interest data."""
    user = User(
        name=request.name,
        age=request.age,
        location=request.location,
        interests=json.dumps(request.interests)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Invalidate profile cache
    cache.delete(f"user:profile:{user.id}")

    return user

@router.get("s", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    """Retrieves all user profiles."""
    return db.query(User).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Retrieves a single user profile by its ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found")
    return user