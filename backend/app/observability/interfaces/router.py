from fastapi import APIRouter, Depends, Query

from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.observability.application import tracer
from app.shared.exceptions import NotFoundError

router = APIRouter(prefix="/api", tags=["observability"])


@router.get("/traces")
async def list_traces(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
):
    return await tracer.list_traces(user.id, session_id, limit)


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, user: User = Depends(get_current_user)):
    trace = await tracer.get_trace(user.id, trace_id)
    if not trace:
        raise NotFoundError("Trace 不存在")
    return trace


@router.get("/usage/summary")
async def usage_summary(
    days: int = Query(default=30, le=365), user: User = Depends(get_current_user)
):
    return await tracer.usage_summary(user.id, days)
