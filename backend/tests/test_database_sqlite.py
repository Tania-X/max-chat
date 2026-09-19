"""SQLite 并发设置的回归测试。"""

from sqlalchemy import text


async def test_wal_and_busy_timeout_enabled(db_session):
    """流式聊天与记忆抽取后台任务会并发写入，默认 journal 模式下极易锁库。"""
    journal_mode = (await db_session.execute(text("PRAGMA journal_mode"))).scalar()
    busy_timeout = (await db_session.execute(text("PRAGMA busy_timeout"))).scalar()

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) >= 1000
