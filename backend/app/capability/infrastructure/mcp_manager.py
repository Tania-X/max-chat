import asyncio
import logging

from app.shared.config import get_settings

logger = logging.getLogger(__name__)

MCP_TIMEOUT_SECONDS = 10


async def load_mcp_tools(name: str, config: dict) -> list:
    """连接一个 MCP server 并返回其工具集。不可达时降级为空。"""
    transport = config.get("transport", "stdio")
    if transport == "stdio" and not get_settings().allow_stdio_mcp:
        # stdio 传输会以本机权限拉起任意子进程（等同代码执行），默认关闭
        logger.warning(
            "已跳过 stdio MCP server %r：需显式设置 ALLOW_STDIO_MCP=true 才启用", name
        )
        return []

    try:
        # ADK 2.x 起更名为 McpToolset，旧名 MCPToolset 仍可用但会告警
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset as MCPToolset
    except ImportError:
        try:
            from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
        except ImportError:
            try:
                from google.adk.tools.mcp_tool import MCPToolset
            except ImportError:
                logger.warning("ADK MCPToolset unavailable")
                return []

    try:
        if transport == "stdio":
            from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
            from mcp import StdioServerParameters

            toolset = MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=config["command"],
                        args=config.get("args", []),
                        env=config.get("env"),
                    ),
                    timeout=MCP_TIMEOUT_SECONDS,
                )
            )
        else:
            from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

            toolset = MCPToolset(
                connection_params=SseConnectionParams(
                    url=config["url"], headers=config.get("headers"), timeout=MCP_TIMEOUT_SECONDS
                )
            )
        return await asyncio.wait_for(toolset.get_tools(), timeout=MCP_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("mcp server %s unavailable: %s", name, exc)
        return []
