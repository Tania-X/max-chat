from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.memory.domain.models import UserProfile
from app.memory.infrastructure.memory_repository import SqlAlchemyMemoryRepository
from app.shared.database import get_db
from app.shared.exceptions import NotFoundError

router = APIRouter(prefix="/api", tags=["memory"])


def _repo(db: AsyncSession) -> SqlAlchemyMemoryRepository:
    return SqlAlchemyMemoryRepository(db)


@router.get("/memory")
async def list_memories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    memories = await _repo(db).list_by_user(user.id)
    return [
        {
            "id": m.id,
            "content": m.content,
            "category": m.category,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    repo = _repo(db)
    memory = await repo.get(memory_id)
    # 不存在与无权访问统一返回 404，避免泄露他人记忆的存在性
    if not memory or memory.user_id != user.id:
        raise NotFoundError("记忆不存在")
    await repo.delete(user.id, memory_id)
    return {"ok": True}


@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await _repo(db).get_profile(user.id)
    return {"user_id": user.id, "data": profile.data, "updated_at": profile.updated_at.isoformat()}


class ProfileRequest(BaseModel):
    data: dict


@router.put("/profile")
async def update_profile(
    body: ProfileRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    profile = UserProfile(user_id=user.id, data=body.data)
    await _repo(db).save_profile(profile)
    return {"ok": True}
