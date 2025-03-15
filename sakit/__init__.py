"""Search Internet plugin for Solana Agent."""
from .search_internet import SearchInternetTool, SolanaPlugin

# This function MUST return a SolanaPlugin instance
def get_plugin():
    """Return the plugin instance for registration."""
    return SolanaPlugin()

__all__ = ["SearchInternetTool", "SolanaPlugin", "get_plugin"]
