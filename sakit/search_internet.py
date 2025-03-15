from solana_agent import AutoTool, ToolRegistry
import requests
from typing import Dict, Any, Optional, List


class SearchInternetTool(AutoTool):
    """Tool for searching the internet using Perplexity AI."""

    def __init__(self, registry=None):
        """Initialize with auto-registration."""
        super().__init__(
            name="search_internet",
            description="Search the internet for current information using Perplexity AI",
            registry=registry,
        )
        self._api_key = None
        self._default_model = "sonar"

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with all possible API key locations."""
        super().configure(config)

        # Try multiple locations for the API key with explicit debugging
        if "perplexity_api_key" in config:
            self._api_key = config["perplexity_api_key"]
            print("Found API key directly in config root")
        elif (
            "tools" in config
            and "search_internet" in config["tools"]
            and "api_key" in config["tools"]["search_internet"]
        ):
            self._api_key = config["tools"]["search_internet"]["api_key"]
            print("Found API key in tools.search_internet.api_key")

        # Debug output
        print(f"API key configured: {'YES' if self._api_key else 'NO'}")
        print(f"Config keys available: {list(config.keys())}")

        # Get default model
        if (
            "tools" in config
            and "search_internet" in config["tools"]
            and "default_model" in config["tools"]["search_internet"]
        ):
            self._default_model = config["tools"]["search_internet"]["default_model"]

    def get_schema(self) -> Dict[str, Any]:
        """Return parameter schema for the tool."""
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
                    "description": f"The Perplexity model to use (default: {self._default_model})",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Execute the search."""
        search_model = model or self._default_model
        
        if not self._api_key:
            return {"status": "error", "message": "Perplexity API key not configured"}
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            payload = {
                "model": search_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You search the internet for current information. Include detailed information with citations like [1], [2], etc.",
                    },
                    {"role": "user", "content": query},
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
                
                # Remove the existing Sources section if present
                if "Sources:" in content:
                    content = content.split("Sources:")[0].strip()
                
                # Get citations if available
                links = []
                if "citations" in data:
                    citations = data["citations"]
                    for i, citation in enumerate(citations, 1):
                        url = citation if isinstance(citation, str) else (citation["url"] if "url" in citation else "")
                        if url:
                            links.append(f"[{i}] {url}")
                
                # Format the final content with properly numbered sources
                if links:
                    formatted_content = content + "\n\n**Sources:**\n" + "\n".join(links)
                else:
                    formatted_content = content
                    
                return {
                    "status": "success",
                    "result": formatted_content,
                    "model_used": search_model,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to search: {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}


class SolanaPlugin:
    """Plugin for Solana Agent."""

    def __init__(self):
        """Initialize the plugin."""
        self.name = "search_internet"
        self.config = None
        self.tool_registry = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with config from Solana Agent."""
        self.config = config
        self.tool_registry = ToolRegistry()

        # Debug the config
        print(
            f"Initializing search_internet plugin with config keys: {list(config.keys())}"
        )

        # Check for API key and print if found
        if "perplexity_api_key" in config:
            print("Perplexity API key is properly included in config")

    def get_tools(self) -> List[AutoTool]:
        """Return tool with explicit registry passing."""
        # Create and register the tool
        tool = SearchInternetTool()
        tool.configure(self.config)  # Pass the stored config

        print(
            f"Created search_internet tool with API key: {'Present' if tool._api_key else 'Missing'}"
        )
        return [tool]


# Entry point function
def get_plugin():
    """Return plugin instance for registration."""
    return SolanaPlugin()
