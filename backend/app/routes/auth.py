"""Authentication endpoints for user registration and JWT login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserResponse, AuthResponse
from app.utils.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Register a new user account with hashed password and return an access token."""
    # 1. Check email uniqueness
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

    # 2. Enforce password presence
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration",
        )

    # 3. Create and persist user
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
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    await db.refresh(new_user)

    # 4. Generate JWT bearer token
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
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Authenticate a user using email and password, returning an access token."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    user.update_last_active()
    token = create_access_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
