"""Authentication routes for user registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.utils.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------- Response Schemas ----------

from pydantic import BaseModel
from uuid import UUID


class AuthResponse(BaseModel):
    """Response returned after successful login or registration."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------- Endpoints ----------

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    - Validates email uniqueness
    - Hashes the password
    - Creates the user in the database
    - Returns a JWT access token
    """
    # Check if email already exists
    if user_data.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

    # Require password for registration
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration",
        )

    # Create user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        preferences=user_data.preferences or {},
        role=user_data.role or "user",
        is_active=True,
    )

    db.add(new_user)
    try:
        await db.flush()          # Populate the id
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    await db.refresh(new_user)

    # Generate JWT
    token = create_access_token(data={"sub": str(new_user.id)})

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(new_user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email and password",
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user with email and password.

    - Looks up user by email
    - Verifies bcrypt password
    - Returns a JWT access token
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last_active
    user.update_last_active()

    # Generate JWT
    token = create_access_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
