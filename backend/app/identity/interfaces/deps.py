from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models import User
from app.identity.infrastructure.user_repository import SqlAlchemyUserRepository
from app.shared.database import get_db
from app.shared.exceptions import AuthError
from app.shared.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthError("未登录")
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise AuthError("登录状态无效或已过期")
    user = await SqlAlchemyUserRepository(db).get_by_id(user_id)
    if not user:
        raise AuthError("用户不存在")
    return user
