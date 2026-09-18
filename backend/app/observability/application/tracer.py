import json
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.observability.infrastructure.models import TraceORM
from app.observability.infrastructure.pricing import estimate_cost
from app.shared.database import async_session_factory

logger = logging.getLogger(__name__)


async def record_trace(
    *,
    user_id: str,
    session_id: str,
    message_id: str | None,
    model_config,
    tool_events: list[dict],
    usage: dict,
    ttft_ms: int | None,
    duration_ms: int,
    error: str = "",
) -> str:
    trace_id = str(uuid.uuid4())
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    tps = round(completion_tokens / (duration_ms / 1000), 1) if duration_ms else 0.0
    cost = estimate_cost(model_config.model_name, prompt_tokens, completion_tokens)
    try:
        async with async_session_factory() as db:
            db.add(
                TraceORM(
                    id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    message_id=message_id,
                    provider=model_config.provider,
                    model_name=model_config.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    ttft_ms=ttft_ms,
                    duration_ms=duration_ms,
                    tokens_per_second=tps,
                    cost_usd=cost,
                    tool_spans=json.dumps(tool_events, ensure_ascii=False, default=str),
                    error=error,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("record trace failed: %s", exc)
    return trace_id


def _trace_to_dict(orm: TraceORM) -> dict:
    return {
        "id": orm.id,
        "session_id": orm.session_id,
        "message_id": orm.message_id,
        "provider": orm.provider,
        "model_name": orm.model_name,
        "prompt_tokens": orm.prompt_tokens,
        "completion_tokens": orm.completion_tokens,
        "ttft_ms": orm.ttft_ms,
        "duration_ms": orm.duration_ms,
        "tokens_per_second": orm.tokens_per_second,
        "cost_usd": orm.cost_usd,
        "tool_spans": json.loads(orm.tool_spans or "[]"),
        "error": orm.error,
        "created_at": orm.created_at.isoformat(),
    }


async def list_traces(user_id: str, session_id: str | None, limit: int = 50) -> list[dict]:
    async with async_session_factory() as db:
        stmt = select(TraceORM).where(TraceORM.user_id == user_id)
        if session_id:
            stmt = stmt.where(TraceORM.session_id == session_id)
        stmt = stmt.order_by(TraceORM.created_at.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [_trace_to_dict(r) for r in rows]


async def get_trace(user_id: str, trace_id: str) -> dict | None:
    async with async_session_factory() as db:
        orm = await db.get(TraceORM, trace_id)
        if not orm or orm.user_id != user_id:
            return None
        return _trace_to_dict(orm)


async def usage_summary(user_id: str, days: int = 30) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as db:
        base = select(TraceORM).where(TraceORM.user_id == user_id, TraceORM.created_at >= since)

        total_row = (
            await db.execute(
                select(
                    func.count(TraceORM.id),
                    func.coalesce(func.sum(TraceORM.prompt_tokens), 0),
                    func.coalesce(func.sum(TraceORM.completion_tokens), 0),
                    func.coalesce(func.sum(TraceORM.cost_usd), 0.0),
                    func.coalesce(func.avg(TraceORM.ttft_ms), 0.0),
                    func.coalesce(func.avg(TraceORM.tokens_per_second), 0.0),
                ).where(TraceORM.user_id == user_id, TraceORM.created_at >= since)
            )
        ).one()

        by_model = (
            await db.execute(
                select(
                    TraceORM.model_name,
                    TraceORM.provider,
                    func.count(TraceORM.id),
                    func.coalesce(func.sum(TraceORM.prompt_tokens), 0),
                    func.coalesce(func.sum(TraceORM.completion_tokens), 0),
                    func.coalesce(func.sum(TraceORM.cost_usd), 0.0),
                )
                .where(TraceORM.user_id == user_id, TraceORM.created_at >= since)
                .group_by(TraceORM.model_name, TraceORM.provider)
            )
        ).all()

        traces = (await db.execute(base.order_by(TraceORM.created_at))).scalars().all()
        by_day: dict[str, dict] = {}
        for t in traces:
            day = t.created_at.strftime("%Y-%m-%d")
            bucket = by_day.setdefault(day, {"date": day, "calls": 0, "tokens": 0, "cost_usd": 0.0})
            bucket["calls"] += 1
            bucket["tokens"] += t.prompt_tokens + t.completion_tokens
            bucket["cost_usd"] = round(bucket["cost_usd"] + t.cost_usd, 6)

        return {
            "days": days,
            "total_calls": total_row[0],
            "total_prompt_tokens": total_row[1],
            "total_completion_tokens": total_row[2],
            "total_cost_usd": round(total_row[3], 6),
            "avg_ttft_ms": round(total_row[4], 1),
            "avg_tokens_per_second": round(total_row[5], 1),
            "by_model": [
                {
                    "model_name": r[0],
                    "provider": r[1],
                    "calls": r[2],
                    "prompt_tokens": r[3],
                    "completion_tokens": r[4],
                    "cost_usd": round(r[5], 6),
                }
                for r in by_model
            ],
            "by_day": list(by_day.values()),
        }
