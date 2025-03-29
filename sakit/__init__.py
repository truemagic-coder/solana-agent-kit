"""Search Internet plugin for Solana Agent."""
from .search_internet import SearchInternetTool, SearchInternetPlugin
from .mcp import MCPTool, MCPPlugin

__all__ = ["SearchInternetTool", "SearchInternetPlugin", "MCPTool", "MCPPlugin"]
