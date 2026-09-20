from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.domain.models import (
    OUTCOME_OK,
    ExtractionRun,
    ExtractionStats,
)
from app.memory.domain.repository import ExtractionRunRepository
from app.memory.infrastructure.models import ExtractionRunORM
from app.shared.clock import utcnow


def _to_entity(orm: ExtractionRunORM) -> ExtractionRun:
    return ExtractionRun(
        id=orm.id,
        user_id=orm.user_id,
        session_id=orm.session_id,
        outcome=orm.outcome,
        latency_ms=orm.latency_ms,
        error=orm.error,
        raw_snippet=orm.raw_snippet,
        prompt_tokens=orm.prompt_tokens,
        completion_tokens=orm.completion_tokens,
        cost_usd=orm.cost_usd,
        memories_written=orm.memories_written,
        duplicates_skipped=orm.duplicates_skipped,
        created_at=orm.created_at,
    )


class SqlAlchemyExtractionRunRepository(ExtractionRunRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, run: ExtractionRun) -> ExtractionRun:
        self.session.add(
            ExtractionRunORM(
                id=run.id,
                user_id=run.user_id,
                session_id=run.session_id,
                outcome=run.outcome,
                latency_ms=run.latency_ms,
                error=run.error,
                raw_snippet=run.raw_snippet,
                prompt_tokens=run.prompt_tokens,
                completion_tokens=run.completion_tokens,
                cost_usd=run.cost_usd,
                memories_written=run.memories_written,
                duplicates_skipped=run.duplicates_skipped,
                created_at=run.created_at,
            )
        )
        await self.session.commit()
        return run

    async def stats(self, user_id: str, days: int = 30) -> ExtractionStats:
        since = utcnow() - timedelta(days=days)
        rows = (
            await self.session.execute(
                select(
                    ExtractionRunORM.outcome,
                    func.count(ExtractionRunORM.id),
                    func.coalesce(func.avg(ExtractionRunORM.latency_ms), 0.0),
                    func.coalesce(func.sum(ExtractionRunORM.cost_usd), 0.0),
                    func.coalesce(func.sum(ExtractionRunORM.memories_written), 0),
                    func.coalesce(func.sum(ExtractionRunORM.duplicates_skipped), 0),
                )
                .where(ExtractionRunORM.user_id == user_id, ExtractionRunORM.created_at >= since)
                .group_by(ExtractionRunORM.outcome)
            )
        ).all()

        stats = ExtractionStats()
        weighted_latency = 0.0
        for outcome, count, avg_latency, cost, written, duplicates in rows:
            count = int(count)
            stats.by_outcome[outcome] = count
            stats.total += count
            if outcome == OUTCOME_OK:
                stats.ok += count
            else:
                stats.failed += count
            weighted_latency += float(avg_latency) * count
            stats.total_cost_usd += float(cost)
            stats.memories_written += int(written)
            stats.duplicates_skipped += int(duplicates)

        if stats.total:
            stats.avg_latency_ms = round(weighted_latency / stats.total, 1)
        stats.total_cost_usd = round(stats.total_cost_usd, 8)
        return stats

    async def recent_failures(self, user_id: str, limit: int = 5) -> list[ExtractionRun]:
        rows = (
            (
                await self.session.execute(
                    select(ExtractionRunORM)
                    .where(ExtractionRunORM.user_id == user_id, ExtractionRunORM.outcome != OUTCOME_OK)
                    .order_by(ExtractionRunORM.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [_to_entity(r) for r in rows]
