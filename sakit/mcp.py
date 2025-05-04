import logging
from typing import Dict, Any, List, Optional

# Solana Agent Kit imports
from solana_agent import AutoTool, ToolRegistry

# mcp-use and LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from mcp_use import MCPAgent, MCPClient

    MCP_USE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"mcp-use or langchain-openai library had errors: {e}")
    MCP_USE_AVAILABLE = False
    # Define dummy types if mcp-use is not installed to avoid runtime errors on load
    BaseChatModel = type("BaseChatModel", (object,), {})
    MCPAgent = type("MCPAgent", (object,), {})
    MCPClient = type("MCPClient", (object,), {})
    ChatOpenAI = type("ChatOpenAI", (object,), {})  # Add dummy for ChatOpenAI
    # Use logging for the warning
    logging.warning(
        "mcp-use or langchain-openai library not found. MCPTool will not function. Install with 'pip install mcp-use langchain-openai'"
    )

# --- Setup Logger ---
logger = logging.getLogger(__name__)
# Basic configuration if no other logging is set up (optional, depends on framework)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MCPTool(AutoTool):
    """
    Tool for interacting with MCP servers using the mcp-use library.
    Takes a natural language query and executes it using tools available
    on the configured MCP server (e.g., Zapier actions).
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """Initialize with auto-registration."""
        super().__init__(
            name="mcp",
            description="Executes tasks using connected MCP servers (e.g., Zapier actions). Provide a natural language query describing the task.",
            registry=registry,
        )
        self._server_urls: List[str] = []
        self._llm = None  # LLM will be set by the plugin
        logger.info("MCPTool initialized. LLM will be set later.")

    def set_llm(self, llm):
        """Sets the LangChain LLM instance for the tool."""
        self._llm = llm
        logger.info(f"MCPTool: LLM instance set ({type(llm).__name__}).")

    def get_schema(self) -> Dict[str, Any]:
        """Define the tool schema for accepting a natural language query."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The natural language task or query to execute using connected MCP tools (e.g., 'Send an email to bob@example.com via Zapier', 'Browse example.com using the playwright server'). Specify the target server if multiple are configured and relevant.",
                }
                # Optional: Add server_name if you configure multiple servers and want explicit control
                # "server_name": {
                #     "type": "string",
                #     "description": "Optional: The specific MCP server name (e.g., 'zapier', 'playwright') to target for this query."
                # }
            },
            "required": ["query"],
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure MCP server URLs."""
        super().configure(config)
        if "tools" in config and "mcp" in config["tools"]:
            urls = config["tools"]["mcp"].get("urls", [])
            self._server_urls = [url for url in urls if url]
            logger.info(f"MCPTool: Configured with server URLs: {self._server_urls}")
        else:
            self._server_urls = []
            logger.warning("MCPTool: No MCP server URLs configured.")
        # LLM is set via set_llm by the plugin

    async def execute(
        self, query: str, server_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the query using an mcp-use agent."""
        if not MCP_USE_AVAILABLE:
            logger.error(
                "MCPTool execute failed: mcp-use or langchain-openai library is not installed."
            )
            return {
                "status": "error",
                "message": "mcp-use or langchain-openai library is not installed.",
            }

        if not self._server_urls:
            logger.error("MCPTool execute failed: No MCP server URLs configured.")
            return {
                "status": "error",
                "message": "No MCP server URLs configured for MCPTool.",
            }
        if not self._llm:
            # This should ideally not happen if the plugin configures it correctly
            logger.error(
                "MCPTool execute failed: LLM instance was not set before execute was called."
            )
            return {"status": "error", "message": "LLM not configured for MCPTool."}

        # Prepare mcp-use config dictionary
        mcp_servers_config = {}
        default_server_name = "default_mcp"  # Fallback name
        for i, url in enumerate(self._server_urls):
            name = f"server{i}"
            if "actions.zapier.com" in url:
                name = "zapier"  # Prioritize 'zapier' name if found
            elif i == 0:
                default_server_name = (
                    name  # Use first server name as default if no specific name found
                )
            mcp_servers_config[name] = {"url": url}

        # If a server_name wasn't provided, but we only have one server, use its name
        if not server_name and len(mcp_servers_config) == 1:
            server_name = list(mcp_servers_config.keys())[0]
        elif not server_name:
            server_name = default_server_name  # Use the determined default

        mcp_config = {"mcpServers": mcp_servers_config}
        logger.info(f"MCPTool: Using mcp-use config: {mcp_config}")

        client = None
        try:
            # Create MCPClient
            # Note: mcp-use might have its own logging
            client = MCPClient.from_dict(mcp_config)

            # Create agent using the provided LLM
            # Enable verbose for more insight from mcp-use
            agent = MCPAgent(
                llm=self._llm,
                client=client,
                max_steps=10,
                verbose=True,
                use_server_manager=True,
            )

            logger.debug(f"MCPTool: Running mcp-use agent with query: '{query}'")

            # Determine if server_name needs to be passed to run()
            num_servers = len(mcp_servers_config)
            target_server = None

            if server_name and server_name in mcp_servers_config:
                target_server = server_name
                logger.debug(f"MCPTool: Targeting specified server: {target_server}")
            elif num_servers > 1 and not server_name:
                logger.debug(
                    "MCPTool: Multiple servers configured but none specified for run."
                )
            elif num_servers == 1:
                target_server = list(mcp_servers_config.keys())[0]
                logger.debug(
                    f"MCPTool: Only one server ('{target_server}'), mcp-use will use it."
                )

            result = await agent.run(query)
            logger.debug(f"MCPTool: mcp-use agent result: {result}")

            # Ensure result is serializable
            final_result = str(result) if result is not None else "No result returned."

            return {"status": "success", "result": final_result}

        except Exception as e:
            # Use logger.exception to include traceback automatically
            logger.exception(
                f"MCPTool Error during mcp-use agent execution: {type(e).__name__}: {e}"
            )
            return {
                "status": "error",
                "message": f"MCP agent failed: {type(e).__name__}: {e}",
            }


# --- Plugin Class ---


class MCPPlugin:
    """Plugin for integrating MCP capabilities via the mcp-use library."""

    def __init__(self):
        """Initialize the plugin."""
        self.name = "mcp"
        self.config = None
        self.tool_registry = None
        self._tool: Optional[MCPTool] = None
        self._llm = None  # LLM instance created during configure
        logger.info(f"Created MCPPlugin object with name: {self.name}")

    @property
    def description(self):
        """Return the plugin description."""
        return "Plugin providing access to MCP servers (like Zapier) using mcp-use."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        """
        Initialize the plugin, create the MCPTool, and register it.
        The LLM instance will be created during the configure phase.
        """
        if not MCP_USE_AVAILABLE:
            logger.warning(
                "MCPPlugin: Skipping initialization as mcp-use or langchain-openai library is not available."
            )
            return

        self.tool_registry = tool_registry
        logger.info("Initializing MCP plugin. LLM will be configured later.")

        # Create and immediately register the tool (LLM will be set in configure)
        self._tool = MCPTool(registry=tool_registry)

        # Verification
        registered_tool = tool_registry.get_tool("mcp")
        if registered_tool and isinstance(registered_tool, MCPTool):
            logger.info("MCP tool registration verification: Success")
        else:
            logger.error(
                f"MCP tool registration verification: Failed or wrong type ({type(registered_tool)})"
            )

        all_tools = tool_registry.list_all_tools()
        logger.info(f"All registered tools after MCP init: {all_tools}")

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin, create the LLM, and configure the tool."""
        if not MCP_USE_AVAILABLE:
            logger.warning(
                "MCPPlugin: Skipping configuration as mcp-use or langchain-openai library is not available."
            )
            return

        self.config = config
        logger.info(f"Configuring {self.name} plugin")

        # --- Create LLM Instance ---
        openai_api_key = None
        try:
            # Attempt to get the OpenAI API key from the config
            if (
                "openai" in config
                and isinstance(config["openai"], dict)
                and "api_key" in config["openai"]
            ):
                openai_api_key = config["openai"]["api_key"]
                logger.info("MCPPlugin: Found OpenAI API key in config.")
            else:
                logger.warning(
                    "MCPPlugin: OpenAI API key not found in config['openai']['api_key']."
                )

            if openai_api_key:
                # Instantiate ChatOpenAI - choose a model suitable for tool use
                llm_model = "gpt-4.1"
                self._llm = ChatOpenAI(
                    model=llm_model, api_key=openai_api_key, temperature=0
                )
                logger.info(
                    f"MCPPlugin: Created ChatOpenAI LLM instance (model={self._llm.model_name})."
                )
            else:
                logger.error(
                    "MCPPlugin: Cannot create LLM instance without OpenAI API key."
                )
                self._llm = None  # Ensure LLM is None if key is missing

        except Exception as llm_e:
            logger.exception(f"MCPPlugin: Error creating ChatOpenAI instance: {llm_e}")
            self._llm = None
        # --- LLM Instance Created (or failed) ---

        # Configure the tool instance
        if self._tool:
            self._tool.configure(self.config)  # Configure server URLs
            if self._llm:
                self._tool.set_llm(self._llm)  # Pass the created LLM to the tool
            else:
                logger.warning(
                    "MCPPlugin: LLM instance not available, MCPTool may not function."
                )
            logger.info(
                f"MCP Tool configured with server URLs: {self._tool._server_urls if hasattr(self._tool, '_server_urls') else 'N/A'}"
            )
        else:
            logger.warning(
                f"Warning: {self.name} tool instance not found during configuration."
            )

    def get_tools(self) -> List[AutoTool]:
        """Return the list of tools provided by this plugin."""
        if not MCP_USE_AVAILABLE:
            return []

        if self._tool:
            return [self._tool]
        return []


# Entry point function
def get_plugin():
    """Return plugin instance for registration."""
    if not MCP_USE_AVAILABLE:
        logger.warning(
            "MCPPlugin: Cannot create plugin instance, mcp-use or langchain-openai library not available."
        )

        # Return a dummy object or handle appropriately in your framework
        class DummyPlugin:
            name = "mcp (disabled)"
            description = (
                "MCP plugin disabled (mcp-use/langchain-openai library not found)"
            )

            def initialize(self, *args, **kwargs):
                pass

            def configure(self, *args, **kwargs):
                pass

            def get_tools(self):
                return []

        return DummyPlugin()

    return MCPPlugin()
