"""Authentication API routes."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token, decode_access_token, hash_password,
    verify_password, oauth2_scheme,
)
from app.core.logging import log_audit
from app.database.connection import get_db
from app.models.database_models import Role, User
from app.models.schemas import LoginResponse, MessageResponse, UserRead, UserRegisterRequest

router = APIRouter()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: decode JWT and return the current authenticated User."""
    payload = decode_access_token(token)
    user_id = int(payload.get("sub"))
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user_id, User.is_active == True)
    )  # noqa
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: ensure the current user has ADMIN role."""
    if not current_user.role or current_user.role.name != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return current_user


@router.post("/login", response_model=LoginResponse, summary="Login and receive JWT token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username/password and receive a Bearer JWT token."""
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.username == form_data.username, User.is_active == True)  # noqa
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        log_audit("login_failed", detail={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username})
    role_name = user.role.name if user.role else None

    log_audit("login_success", user_id=user.id, detail={"username": user.username})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=role_name,
    )


@router.get("/me", response_model=UserRead, summary="Get current logged-in user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user



@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Create a new system user. Requires ADMIN role."""
    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists.")

    role_result = await db.execute(select(Role).where(Role.name == request.role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail=f"Role '{request.role_name}' not found.")

    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role_id=role.id,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    log_audit("user_registered", detail={"username": request.username, "role": request.role_name})
    return new_user
