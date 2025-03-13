"""
Search Internet Plugin for Solana Agent
Uses Perplexity AI API to search the web and provide results
"""

import requests
from typing import Dict, Any, Optional, Literal, List
from solana_agent import Tool


class SearchInternetTool(Tool):
    """Tool for searching the internet using Perplexity AI."""

    def __init__(self, config=None):
        """Initialize with optional config."""
        self._config = config or {}
        self._api_key = self._config.get("perplexity_api_key")
        self._default_model = (
            self._config.get("tools", {})
            .get("search_internet", {})
            .get("default_model", "sonar")
        )

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "search_internet"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Search the internet for current information on any topic using Perplexity AI"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up online",
                },
                "model": {
                    "type": "string",
                    "enum": [
                        "sonar",
                        "sonar-pro",
                        "sonar-reasoning-pro",
                        "sonar-reasoning",
                    ],
                    "description": f"The Perplexity model to use for search (default: {self._default_model})",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Execute the search and return results.

        Args:
            query: The search query string
            model: Optional Perplexity model to use, overrides default if specified

        Returns:
            Dictionary containing search results or error message
        """
        # Use specified model or fall back to default
        search_model = model if model else self._default_model

        result = self._search_internet(query, search_model)

        if result.startswith("Failed") or result.startswith("Error"):
            return {"status": "error", "message": result}

        return {"status": "success", "result": result, "model_used": search_model}

    def _search_internet(
        self,
        query: str,
        model: Literal[
            "sonar", "sonar-pro", "sonar-reasoning-pro", "sonar-reasoning"
        ] = "sonar",
    ) -> str:
        """Perform the internet search using Perplexity AI API.

        Args:
            query: Search query string
            model: Perplexity model to use
                - sonar: Fast, general-purpose search
                - sonar-pro: Enhanced search capabilities
                - sonar-reasoning-pro: Advanced reasoning with search
                - sonar-reasoning: Basic reasoning with search

        Returns:
            Search results or error message if search fails
        """
        try:
            if not self._api_key:
                return "Error: Perplexity API key not configured. Please add 'perplexity_api_key' to your configuration."

            url = "https://api.perplexity.ai/chat/completions"

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You answer the user's query by searching the internet for current information. Provide sources when available.",
                    },
                    {
                        "role": "user",
                        "content": query,
                    },
                ],
            }
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
            else:
                return (
                    f"Failed to search Perplexity. Status code: {response.status_code}"
                )
        except Exception as e:
            return f"Failed to search Perplexity. Error: {e}"


class SolanaPlugin:
    """Plugin provider for Solana Agent."""

    def __init__(self):
        """Initialize the plugin."""
        self.config = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with config from Solana Agent."""
        self.config = config

    def get_tools(self) -> List[Tool]:
        """Return the list of tools provided by this plugin."""
        return [SearchInternetTool(self.config)]
