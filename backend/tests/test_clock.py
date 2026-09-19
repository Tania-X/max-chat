"""统一时间源的回归测试。"""

from datetime import datetime, timezone


def test_utcnow_is_naive_utc():
    """存储层使用 naive DateTime；时间源必须保持同一语义。

   混入 aware 值会让读取结果时而 naive 时而 aware，比较时直接抛 TypeError。
    """
    from app.shared.clock import utcnow

    now = utcnow()

    assert now.tzinfo is None
    reference = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((reference - now).total_seconds()) < 5
