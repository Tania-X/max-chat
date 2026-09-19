"""stdio MCP 开关回归测试（对应加固项 S1）。

stdio 传输会以本机权限拉起任意子进程，等同代码执行。默认必须关闭，
只有显式配置 ALLOW_STDIO_MCP=true 才允许。
"""

import sys

import pytest

from app.capability.infrastructure import mcp_manager


class _StubSettings:
    def __init__(self, allow_stdio_mcp: bool):
        self.allow_stdio_mcp = allow_stdio_mcp


def _probe_config(canary):
    return {
        "transport": "stdio",
        "command": "/bin/sh",
        "args": ["-c", f"touch {canary}"],
    }


async def test_stdio_mcp_blocked_by_default(monkeypatch, tmp_path):
    """默认配置下不得拉起子进程。"""
    monkeypatch.setattr(mcp_manager, "get_settings", lambda: _StubSettings(False))
    canary = tmp_path / "spawned"

    tools = await mcp_manager.load_mcp_tools("probe", _probe_config(canary))

    assert tools == []
    assert not canary.exists(), "默认配置下仍然执行了用户提供的命令"


@pytest.mark.skipif(sys.platform == "win32", reason="依赖 POSIX shell")
async def test_stdio_mcp_runs_command_when_explicitly_enabled(monkeypatch, tmp_path):
    """显式开启后命令确实会被执行——这正是它必须默认关闭的原因。"""
    pytest.importorskip("mcp")
    monkeypatch.setattr(mcp_manager, "get_settings", lambda: _StubSettings(True))
    canary = tmp_path / "spawned"

    await mcp_manager.load_mcp_tools("probe", _probe_config(canary))

    assert canary.exists()
