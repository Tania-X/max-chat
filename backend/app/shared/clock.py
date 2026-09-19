"""统一的时间源。

``datetime.utcnow()`` 在 Python 3.12 已废弃，但直接改用 timezone-aware 的
``datetime.now(timezone.utc)`` 会与两处既有约定冲突：

- 存储层用的是不带时区的 ``DateTime`` 列，混入 aware 值会让读取结果时而
  naive 时而 aware，比较时直接抛 TypeError；
- 前端按「后端返回 naive UTC」的约定渲染（``created_at + 'Z'``）。

因此这里保持 naive UTC 语义，只把废弃调用替换掉。
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """当前 UTC 时间（naive，语义与旧 datetime.utcnow() 一致）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
