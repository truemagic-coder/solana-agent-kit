from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client

from solana_agent import AutoTool, ToolRegistry


class MCPTool(AutoTool):
    """Tool for interacting with MCP servers."""

    def __init__(self, registry=None):
        """Initialize with auto-registration."""
        super().__init__(
            name="mcp",
            description="Interact with MCP servers to access external tools and resources. Use this to search, retrieve, and execute tools from connected MCP servers.",
            registry=registry,
        )
        self._server_urls = []  # Changed to list
        self._sessions = {}     # Map of URL -> Session

    def get_schema(self) -> Dict[str, Any]:
        """Define the tool schema with detailed instructions for the LLM."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": """
                    The action to perform. Available actions:
                    - list_tools: Get a list of all available tools on the MCP server
                    - list_resources: Get a list of all available resources
                    - call_tool: Execute a specific tool
                    - read_resource: Retrieve the content of a specific resource
                    """,
                    "enum": ["list_tools", "list_resources", "call_tool", "read_resource"]
                },
                "name": {
                    "type": "string",
                    "description": """
                    Name of the tool or resource to interact with.
                    - Required when action is 'call_tool' or 'read_resource'
                    - Not needed for 'list_tools' or 'list_resources'
                    """
                },
                "args": {
                    "type": "object",
                    "description": """
                    Arguments to pass to the tool when using 'call_tool'.
                    The required arguments depend on the specific tool being called.
                    First use list_tools to see available tools and their requirements.
                    """
                }
            },
            "required": ["action"],
            "examples": [
                {
                    "summary": "List all available tools",
                    "value": {"action": "list_tools"}
                },
                {
                    "summary": "Call a specific tool",
                    "value": {
                        "action": "call_tool",
                        "name": "tool_name",
                        "args": {"param1": "value1"}
                    }
                },
                {
                    "summary": "Read a resource",
                    "value": {
                        "action": "read_resource",
                        "name": "resource_name"
                    }
                }
            ]
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with MCP server settings."""
        super().configure(config)
        
        if "tools" in config and "mcp" in config["tools"]:
            mcp_config = config["tools"]["mcp"]
            # Handle both single string and array of URLs
            urls = mcp_config.get("server_urls") or [mcp_config.get("server_url")]
            self._server_urls = [url for url in urls if url]  # Filter out None values
            print(f"Configured MCP Tool with {len(self._server_urls)} server(s)")

    async def execute(self, action: str, name: Optional[str] = None, 
                 args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute MCP operations across all configured servers."""
        if not self._server_urls:
            return {
                "status": "error", 
                "message": "No MCP server URLs configured. Please provide server_urls in the tools.mcp configuration."
            }

        errors = []
        for server_url in self._server_urls:
            try:
                # Get or create session for this server
                if server_url not in self._sessions:
                    read, write = await sse_client(server_url)
                    self._sessions[server_url] = ClientSession(read, write)
                    await self._sessions[server_url].initialize()

                session = self._sessions[server_url]
                args = args or {}
                
                # Execute requested action with detailed responses for LLM understanding
                if action == "list_tools":
                    tools = await session.list_tools()
                    return {
                        "status": "success",
                        "server": server_url,
                        "message": "Available tools found",
                        "result": [
                            {
                                "name": t.name,
                                "description": t.description,
                                "server": server_url,
                                "how_to_use": f"To use this tool, call with: action='call_tool', name='{t.name}', args=<required_parameters>"
                            } 
                            for t in tools
                        ]
                    }
                    
                elif action == "list_resources":
                    resources = await session.list_resources()
                    return {
                        "status": "success",
                        "server": server_url,
                        "message": "Available resources found",
                        "result": [
                            {
                                "name": r.name,
                                "description": r.description,
                                "server": server_url,
                                "how_to_access": f"To read this resource, call with: action='read_resource', name='{r.name}'"
                            }
                            for r in resources
                        ]
                    }
                    
                elif action == "call_tool":
                    if not name:
                        return {
                            "status": "error",
                            "message": "Tool name is required for call_tool action. Use list_tools to see available tools."
                        }
                    result = await session.call_tool(name, args)
                    return {
                        "status": "success",
                        "server": server_url,
                        "message": f"Tool '{name}' executed successfully",
                        "result": result
                    }
                    
                elif action == "read_resource":
                    if not name:
                        return {
                            "status": "error",
                            "message": "Resource name is required for read_resource action. Use list_resources to see available resources."
                        }
                    content, mime_type = await session.read_resource(name)
                    return {
                        "status": "success",
                        "server": server_url,
                        "message": f"Resource '{name}' retrieved successfully",
                        "result": {
                            "content": content.decode() if isinstance(content, bytes) else content,
                            "mime_type": mime_type
                        }
                    }
                
                else:
                    return {
                        "status": "error",
                        "message": f"Unknown action: {action}. Available actions are: list_tools, list_resources, call_tool, read_resource"
                    }

            except Exception as e:
                error_msg = f"Server {server_url}: {str(e)}"
                errors.append(error_msg)
                print(f"MCP Error: {error_msg}")
                continue  # Try next server

        # If we get here, all servers failed
        return {
            "status": "error",
            "message": "All MCP servers failed to process the request",
            "errors": errors,
            "suggestion": "Check server connections and try again. Available actions are: list_tools, list_resources, call_tool, read_resource"
        }
        
class MCPPlugin:
    """Plugin for Model Context Protocol (MCP) integration."""

    def __init__(self):
        """Initialize the plugin."""
        self.name = "mcp"
        self.config = None
        self.tool_registry = None
        self._tool = None
        print(f"Created MCPPlugin object with name: {self.name}")
        
    @property
    def description(self):
        """Return the plugin description."""
        return "Plugin for accessing external tools and resources through MCP servers"

    def initialize(self, tool_registry: ToolRegistry) -> None:
        """Initialize with tool registry from Solana Agent."""
        self.tool_registry = tool_registry
        print("Initializing MCP plugin")
        
        # Create and immediately register the tool
        self._tool = MCPTool(registry=tool_registry)
        success = tool_registry.register_tool(self._tool)
        print(f"Tool registration success: {success}")
        
        # Check available tools in registry
        all_tools = tool_registry.list_all_tools()
        print(f"All registered tools: {all_tools}")
        
        # Force a check to make sure it's registered
        registered_tool = tool_registry.get_tool("mcp")
        print(f"Tool registration verification: {'Success' if registered_tool else 'Failed'}")

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with the provided config."""
        self.config = config
        
        # Configure the tool now that we have the config
        if self._tool:
            self._tool.configure(self.config)
            
            print(
                f"MCP Tool initialized with server URL: {'Found' if self._tool._server_urls else 'Not found'}"
            )

    def get_tools(self) -> List[AutoTool]:
        """Return the list of tools provided by this plugin."""
        if self._tool:
            print(f"Returning tool with name: {self._tool.name}")
            return [self._tool]
        return []


# Entry point function
def get_plugin():
    """Return plugin instance for registration."""
    return MCPPlugin()