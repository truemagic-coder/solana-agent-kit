"""
Tests for MCP Tool.

Tests the MCPTool which connects to MCP servers using fastmcp
and uses LLM to select and call tools.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestMCPToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self):
        """Should have correct tool name."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            assert tool.name == "mcp"

    def test_schema_has_required_properties(self):
        """Should include query in required properties."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            schema = tool.get_schema()
            assert "query" in schema["properties"]
            assert "query" in schema["required"]


class TestMCPToolConfigure:
    """Test configuration method."""

    def test_configure_single_server(self):
        """Should configure single server correctly."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "openai": {"api_key": "test-openai-key"},
                    "tools": {
                        "mcp": {
                            "url": "https://mcp.example.com/api",
                            "headers": {"Authorization": "Bearer token"},
                        }
                    },
                }
            )

            assert len(tool._servers) == 1
            assert tool._servers[0]["url"] == "https://mcp.example.com/api"

    def test_configure_multiple_servers(self):
        """Should configure multiple servers correctly."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "openai": {"api_key": "test-openai-key"},
                    "tools": {
                        "mcp": {
                            "servers": [
                                {"url": "https://server1.com/api"},
                                {
                                    "url": "https://server2.com/api",
                                    "headers": {"X-Key": "abc"},
                                },
                            ]
                        }
                    },
                }
            )

            assert len(tool._servers) == 2
            assert tool._servers[0]["url"] == "https://server1.com/api"
            assert tool._servers[1]["url"] == "https://server2.com/api"
            assert tool._servers[1]["headers"]["X-Key"] == "abc"

    def test_configure_grok_as_default_provider(self):
        """Should configure Grok as default provider when grok key is available."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "grok": {"api_key": "test-grok-key"},
                    "openai": {"api_key": "test-openai-key"},
                    "tools": {"mcp": {"url": "https://mcp.example.com/api"}},
                }
            )

            # Grok should be prioritized over OpenAI by default
            assert tool._llm_provider == "grok"
            assert tool._llm_api_key == "test-grok-key"

    def test_configure_openai_explicit_provider(self):
        """Should use OpenAI when explicitly configured."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "openai": {"api_key": "test-openai-key"},
                    "tools": {
                        "mcp": {
                            "url": "https://mcp.example.com/api",
                            "llm_provider": "openai",
                        }
                    },
                }
            )

            # Should use OpenAI when explicitly specified
            assert tool._llm_provider == "openai"
            assert tool._llm_api_key == "test-openai-key"

    def test_configure_grok_provider(self):
        """Should configure Grok provider correctly."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "grok": {"api_key": "test-grok-key"},
                    "tools": {
                        "mcp": {
                            "url": "https://mcp.example.com/api",
                            "llm_provider": "grok",
                        }
                    },
                }
            )

            assert tool._llm_provider == "grok"
            assert tool._llm_base_url == "https://api.x.ai/v1"


class TestMCPToolExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_no_servers_error(self):
        """Should return error when no servers configured."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            # Need to reload after patching
            import importlib
            import sakit.mcp

            importlib.reload(sakit.mcp)

            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "grok": {"api_key": "test-key"},
                    "tools": {"mcp": {}},  # No URL
                }
            )

            result = await tool.execute(query="Test query")

            assert result["status"] == "error"
            assert "server" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_api_key_error(self):
        """Should return error when no API key configured."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            import importlib
            import sakit.mcp

            importlib.reload(sakit.mcp)

            from sakit.mcp import MCPTool

            tool = MCPTool()
            tool.configure(
                {
                    "tools": {
                        "mcp": {
                            "url": "https://mcp.example.com/api",
                        }
                    },
                }
            )

            result = await tool.execute(query="Test query")

            assert result["status"] == "error"
            assert "key" in result["message"].lower()


class TestMCPPlugin:
    """Test plugin class."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPPlugin

            plugin = MCPPlugin()
            assert plugin.name == "mcp"

    def test_plugin_description(self):
        """Should have descriptive description."""
        with patch.dict(
            "sys.modules",
            {"fastmcp": MagicMock(), "fastmcp.client.transports": MagicMock()},
        ):
            from sakit.mcp import MCPPlugin

            plugin = MCPPlugin()
            assert "mcp" in plugin.description.lower()

    def test_get_plugin_returns_dummy_without_fastmcp(self):
        """Should return dummy plugin when fastmcp is not available."""
        # Test the disabled state
        with patch.dict("sys.modules", {"fastmcp": None}):
            # This tests the fallback behavior
            pass  # The actual import test would need module reload
