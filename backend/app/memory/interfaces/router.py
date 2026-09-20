from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.memory.domain.models import UserProfile
from app.memory.infrastructure.extraction_run_repository import (
    SqlAlchemyExtractionRunRepository,
)
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


@router.get("/memory/extraction/stats")
async def extraction_stats(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记忆抽取健康度：成功率、失败原因分布、延迟与开销。

    抽取在后台异步执行，此前失败既没有日志也没有计数——这里把它变成可观测的。
    """
    repo = SqlAlchemyExtractionRunRepository(db)
    stats = await repo.stats(user.id, days)
    failures = await repo.recent_failures(user.id, limit=5)
    return {
        "days": days,
        "total": stats.total,
        "ok": stats.ok,
        "failed": stats.failed,
        "failure_rate": stats.failure_rate,
        "by_outcome": stats.by_outcome,
        "avg_latency_ms": stats.avg_latency_ms,
        "total_cost_usd": stats.total_cost_usd,
        "memories_written": stats.memories_written,
        "duplicates_skipped": stats.duplicates_skipped,
        "recent_failures": [
            {
                "outcome": f.outcome,
                "error": f.error,
                "raw_snippet": f.raw_snippet,
                "created_at": f.created_at.isoformat(),
            }
            for f in failures
        ],
    }


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
