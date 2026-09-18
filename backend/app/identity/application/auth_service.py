import uuid

from app.identity.domain.models import User
from app.identity.domain.repository import UserRepository
from app.shared.exceptions import AuthError, ConflictError
from app.shared.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    async def register(self, username: str, password: str) -> tuple[User, str]:
        username = username.strip()
        if len(username) < 2:
            raise AuthError("用户名至少 2 个字符")
        if len(password) < 6:
            raise AuthError("密码至少 6 位")
        if await self.users.get_by_username(username):
            raise ConflictError("用户名已被注册")
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=hash_password(password),
            display_name=username,
        )
        await self.users.save(user)
        return user, create_access_token(user.id)

    async def login(self, username: str, password: str) -> tuple[User, str]:
        user = await self.users.get_by_username(username.strip())
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("用户名或密码错误")
        return user, create_access_token(user.id)
