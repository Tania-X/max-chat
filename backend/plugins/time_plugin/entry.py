from datetime import datetime


def get_current_time(timezone_name: str = "local") -> dict:
    """获取当前日期和时间。

    Args:
        timezone_name: 时区名称，默认使用服务器本地时区。

    Returns:
        包含当前时间字符串、ISO 格式与时间戳的字典。
    """
    now = datetime.now().astimezone()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "iso": now.isoformat(),
        "timestamp": int(now.timestamp()),
        "timezone": timezone_name,
    }


tools = [get_current_time]
