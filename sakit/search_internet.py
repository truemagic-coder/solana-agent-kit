from solana_agent import AutoTool, ToolRegistry
import requests
from typing import Dict, Any, List


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
        self._model = "sonar"
        self._citations = True  # Default to True

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
            },
            "required": ["query"]
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with all possible API key locations."""
        super().configure(config)
        
        # First check for tool-specific configuration (preferred location)
        if "tools" in config and isinstance(config["tools"], dict):
            if "search_internet" in config["tools"] and isinstance(config["tools"]["search_internet"], dict):
                # Check for API key in tool config
                if "api_key" in config["tools"]["search_internet"]:
                    self._api_key = config["tools"]["search_internet"]["api_key"]
                    print(f"Using API key from tools.search_internet.api_key: {self._api_key[:4]}...")
                
                # Check for citations setting in tool config
                if "citations" in config["tools"]["search_internet"]:
                    self._citations = bool(config["tools"]["search_internet"]["citations"])
                    print(f"Citations setting: {self._citations}")

                # Check for model setting in tool config
                if "model" in config["tools"]["search_internet"]:
                    self._model = config["tools"]["search_internet"]["model"]
                    print(f"Using model from tools.search_internet.model: {self._model}")

    async def execute(self, query: str) -> Dict[str, Any]:
        """Execute the search."""
        
        if not self._api_key:
            return {"status": "error", "message": "Perplexity API key not configured"}
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            
            # Choose appropriate prompt based on citations setting
            system_content = (
                "You search the internet for current information. Include detailed information with citations like [1], [2], etc." 
                if self._citations else
                "You search the internet for current information. Provide a comprehensive answer without citations or source references."
            )
            
            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_content,
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
                
                # Only process citations if setting is enabled
                if self._citations:
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
                else:
                    # No citation processing needed
                    formatted_content = content
                    
                return {
                    "status": "success",
                    "result": formatted_content,
                    "model_used": self._model,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to search: {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}


class SearchInternetPlugin:
    """Plugin for Solana Agent."""

    def __init__(self):
        """Initialize the plugin."""
        self.name = "search_internet"
        self.config = None
        self.tool_registry = None
        self._tool = None
        print(f"Created SolanaPlugin object with name: {self.name}")
        
    @property
    def description(self):
        """Return the plugin description."""
        return "Plugin for searching the internet with Perplexity AI"

    def initialize(self, tool_registry: ToolRegistry) -> None:
        """Initialize with tool registry from Solana Agent."""
        self.tool_registry = tool_registry
        print("Initializing search_internet plugin")
        
        # Create and immediately register the tool
        self._tool = SearchInternetTool(registry=tool_registry)
        success = tool_registry.register_tool(self._tool)
        print(f"Tool registration success: {success}")
        
        # Check available tools in registry
        all_tools = tool_registry.list_all_tools()
        print(f"All registered tools: {all_tools}")
        
        # Force a check to make sure it's registered
        registered_tool = tool_registry.get_tool("search_internet")
        print(f"Tool registration verification: {'Success' if registered_tool else 'Failed'}")

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with the provided config."""
        self.config = config
        
        # Configure the tool now that we have the config
        if self._tool:
            self._tool.configure(self.config)
            
            print(
                f"SearchInternetTool initialized with API key: {'Found' if self._tool._api_key else 'Not found'}"
            )
            print(f"SearchInternetTool default model: {self._tool._model}")

    def get_tools(self) -> List[AutoTool]:
        """Return the list of tools provided by this plugin."""
        if self._tool:
            print(f"Returning tool with name: {self._tool.name}")
            return [self._tool]
        return []


# Entry point function
def get_plugin():
    """Return plugin instance for registration."""
    return SearchInternetPlugin()
