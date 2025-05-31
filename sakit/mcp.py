import logging
import json
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
import urllib

try:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    FASTMCP_AVAILABLE = True
except ImportError as e:
    FASTMCP_AVAILABLE = False
    logging.warning(f"fastmcp library not found: {e}")

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    logging.warning(f"openai library not found: {e}")

logger = logging.getLogger(__name__)


class MCPTool(AutoTool):
    """
    Tool for interacting with MCP servers using fastmcp.
    Uses an OpenAI-compatible LLM to select and call tools based on a natural language query.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="mcp",
            description="Executes tasks using connected MCP servers (e.g., Zapier actions) via fastmcp. Provide a natural language query describing the task.",
            registry=registry,
        )
        self._server_url: Optional[str] = None
        self._openai_api_key: Optional[str] = None
        self._openai_base_url: Optional[str] = None
        logger.info("MCPTool (fastmcp) initialized.")

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The natural language task or query to execute using connected MCP tools.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        # Expect config['tools']['mcp']['url'] and config['openai']['api_key']
        if "tools" in config and "mcp" in config["tools"]:
            self._server_url = config["tools"]["mcp"].get("url")
            if self._server_url:
                parsed = urllib.parse.urlparse(self._server_url)
                root_domain = f"{parsed.scheme}://{parsed.hostname}"
                logger.info(
                    f"MCPTool: Configured with server root domain: {root_domain}"
                )
            else:
                logger.info("MCPTool: No MCP server URL provided.")

        if "openai" in config and isinstance(config["openai"], dict):
            self._openai_api_key = config["openai"].get("api_key")
        else:
            self._openai_api_key = None

    async def execute(self, query: str) -> Dict[str, Any]:
        if not FASTMCP_AVAILABLE:
            return {"status": "error", "message": "fastmcp library is not installed."}
        if not OPENAI_AVAILABLE:
            return {"status": "error", "message": "openai library is not installed."}
        if not self._openai_api_key:
            return {"status": "error", "message": "No OpenAI API key configured."}

        # 1. Connect to MCP server
        transport = StreamableHttpTransport(self._server_url)
        client = Client(transport=transport)

        async with client:
            tools = await client.list_tools()
            if not tools:
                return {
                    "status": "error",
                    "message": "No tools available on MCP server.",
                }

            # 2. Use LLM to select tool and generate parameters
            tool_descriptions = [
                {
                    "name": t.name,
                    "description": t.description,
                    "params": t.inputSchema,
                }
                for t in tools
            ]
            system_prompt = (
                "You are an expert AI agent. "
                "Given a user request and a list of available tools (with their parameters), "
                "choose the best tool and generate a valid parameter dictionary for it. "
                'Respond ONLY with a JSON object: {"tool": <tool_name>, "parameters": {<param_dict>}}. '
                'If you cannot find a suitable tool, respond with {"tool": null, "parameters": {}}.'
            )
            user_prompt = (
                f"User request: {query}\n\n"
                f"Available tools:\n{json.dumps(tool_descriptions, indent=2)}"
            )

            openai_client = AsyncOpenAI(
                api_key=self._openai_api_key,
            )
            completion = await openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=512,
            )
            response = completion.choices[0].message.content.strip()
            try:
                llm_result = json.loads(response)
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {response}")
                return {
                    "status": "error",
                    "message": f"LLM output parse error: {e}",
                    "raw_llm_output": response,
                }

            tool_name = llm_result.get("tool")
            parameters = llm_result.get("parameters", {})

            if not tool_name:
                return {
                    "status": "error",
                    "message": "No suitable tool found for the query.",
                    "llm_output": response,
                }

            # 3. Call the selected tool
            try:
                result = await client.call_tool(tool_name, parameters)
                # fastmcp returns a list of content objects; we assume first is main
                text_result = (
                    result[0].text
                    if result and hasattr(result[0], "text")
                    else str(result)
                )
                # Try to parse as JSON, fallback to string
                try:
                    parsed = json.loads(text_result)
                except Exception:
                    parsed = text_result
                return {
                    "status": "success",
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": parsed,
                }
            except Exception as e:
                logger.exception(f"Error calling tool '{tool_name}': {e}")
                return {
                    "status": "error",
                    "message": f"Tool call failed: {e}",
                    "tool": tool_name,
                    "parameters": parameters,
                }


class MCPPlugin:
    """Plugin for integrating MCP capabilities via fastmcp."""

    def __init__(self):
        self.name = "mcp"
        self.config = None
        self.tool_registry = None
        self._tool: Optional[MCPTool] = None
        logger.info(f"Created MCPPlugin object with name: {self.name}")

    @property
    def description(self):
        return "Plugin providing access to MCP servers (like Zapier) using fastmcp."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        if not FASTMCP_AVAILABLE:
            logger.warning("MCPPlugin: fastmcp library is not available.")
            return

        self.tool_registry = tool_registry
        logger.info("Initializing MCP plugin (fastmcp).")
        self._tool = MCPTool(registry=tool_registry)

        registered_tool = tool_registry.get_tool("mcp")
        if registered_tool and isinstance(registered_tool, MCPTool):
            logger.info("MCP tool registration verification: Success")
        else:
            logger.error("MCP tool registration verification: Failed or wrong type")

    def configure(self, config: Dict[str, Any]) -> None:
        if not FASTMCP_AVAILABLE:
            logger.warning("MCPPlugin: fastmcp library is not available.")
            return

        self.config = config
        logger.info(f"Configuring {self.name} plugin")
        if self._tool:
            self._tool.configure(self.config)
            logger.info("MCP tool configured.")
        else:
            logger.warning("Warning: MCP tool instance not found during configuration.")

    def get_tools(self) -> List[AutoTool]:
        if not FASTMCP_AVAILABLE:
            return []
        if self._tool:
            return [self._tool]
        return []


def get_plugin():
    if not FASTMCP_AVAILABLE:
        logger.warning(
            "MCPPlugin: Cannot create plugin instance, fastmcp library not available."
        )

        class DummyPlugin:
            name = "mcp (disabled)"
            description = "MCP plugin disabled (fastmcp library not found)"

            def initialize(self, *args, **kwargs):
                pass

            def configure(self, *args, **kwargs):
                pass

            def get_tools(self):
                return []

        return DummyPlugin()
    return MCPPlugin()
