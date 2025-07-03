"""MCP сервер для интеграции с ИИ-ассистентом 1С.ai."""

__version__ = "0.1.0"
__author__ = "artesk"

from .mcp_server import OneCMcpServer
from .api_client import OneCApiClient
from .config import Config

__all__ = ["OneCMcpServer", "OneCApiClient", "Config"] 