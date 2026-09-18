from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.application.auth_service import AuthService
from app.identity.domain.models import User
from app.identity.infrastructure.user_repository import SqlAlchemyUserRepository
from app.identity.interfaces.deps import get_current_user
from app.shared.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    token: str
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name)


@router.post("/register", response_model=TokenResponse)
async def register(body: Credentials, db: AsyncSession = Depends(get_db)):
    user, token = await AuthService(SqlAlchemyUserRepository(db)).register(
        body.username, body.password
    )
    return TokenResponse(token=token, user=_user_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: Credentials, db: AsyncSession = Depends(get_db)):
    user, token = await AuthService(SqlAlchemyUserRepository(db)).login(
        body.username, body.password
    )
    return TokenResponse(token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return _user_response(user)
