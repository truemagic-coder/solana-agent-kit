"""Tests for Solana DFlow swap tool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from sakit.solana_dflow_swap import (
    SolanaDFlowSwapTool,
    SolanaDFlowSwapPlugin,
    get_plugin,
)


class TestSolanaDFlowSwapToolInit:
    """Tests for SolanaDFlowSwapTool initialization."""

    def test_tool_name(self):
        """Should have correct tool name."""
        tool = SolanaDFlowSwapTool()
        assert tool.name == "solana_dflow_swap"

    def test_tool_description(self):
        """Should have meaningful description."""
        tool = SolanaDFlowSwapTool()
        assert "DFlow" in tool.description
        assert "swap" in tool.description.lower()


class TestSolanaDFlowSwapToolSchema:
    """Tests for SolanaDFlowSwapTool schema."""

    def test_schema_has_required_fields(self):
        """Should have all required fields in schema."""
        tool = SolanaDFlowSwapTool()
        schema = tool.get_schema()

        assert "properties" in schema
        props = schema["properties"]

        assert "input_mint" in props
        assert "output_mint" in props
        assert "amount" in props

    def test_schema_required_fields(self):
        """Should mark correct fields as required."""
        tool = SolanaDFlowSwapTool()
        schema = tool.get_schema()

        required = schema.get("required", [])
        assert "input_mint" in required
        assert "output_mint" in required
        assert "amount" in required

    def test_schema_has_slippage_bps(self):
        """Should have optional slippage_bps field."""
        tool = SolanaDFlowSwapTool()
        schema = tool.get_schema()

        assert "slippage_bps" in schema["properties"]
        assert "slippage_bps" not in schema.get("required", [])


class TestSolanaDFlowSwapToolConfigure:
    """Tests for SolanaDFlowSwapTool configuration."""

    def test_configure_sets_credentials(self):
        """Should set credentials from config."""
        tool = SolanaDFlowSwapTool()
        config = {
            "tools": {
                "solana_dflow_swap": {
                    "private_key": "test_private_key",
                    "platform_fee_bps": 50,
                    "fee_account": "FeeAccount123",
                    "referral_account": "RefAccount123",
                    "payer_private_key": "payer_key",
                    "rpc_url": "https://custom-rpc.com",
                }
            }
        }

        tool.configure(config)

        assert tool._private_key == "test_private_key"
        assert tool._platform_fee_bps == 50
        assert tool._fee_account == "FeeAccount123"
        assert tool._referral_account == "RefAccount123"
        assert tool._payer_private_key == "payer_key"
        assert tool._rpc_url == "https://custom-rpc.com"

    def test_configure_uses_default_rpc_url(self):
        """Should use default RPC URL when not provided."""
        tool = SolanaDFlowSwapTool()
        config = {
            "tools": {
                "solana_dflow_swap": {
                    "private_key": "test_private_key",
                }
            }
        }

        tool.configure(config)

        assert tool._rpc_url == "https://api.mainnet-beta.solana.com"


class TestSolanaDFlowSwapToolExecute:
    """Tests for SolanaDFlowSwapTool execute method."""

    @pytest.mark.asyncio
    async def test_execute_missing_config(self):
        """Should return error when private key is missing."""
        tool = SolanaDFlowSwapTool()

        result = await tool.execute(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1000000000,
        )

        assert result["status"] == "error"
        assert "private key" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_dflow_api_error(self):
        """Should return error when DFlow API fails."""
        tool = SolanaDFlowSwapTool()
        # Use a valid base58 keypair for testing
        tool._private_key = "5MaiiCavjCmn9Hs1o3eznqDEhRwxo7pXiAYez7keQUviUkauRiTMD8DrESdrNjN8zd9mTmVhRvBJeg5vhyvgrAhG"
        tool._rpc_url = "https://api.mainnet-beta.solana.com"

        with patch("sakit.solana_dflow_swap.DFlowSwap") as MockDFlow:
            mock_dflow_instance = MagicMock()
            mock_dflow_instance.get_order = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    error="Insufficient liquidity",
                )
            )
            MockDFlow.return_value = mock_dflow_instance

            result = await tool.execute(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "liquidity" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_transaction_returned(self):
        """Should return error when no transaction is returned."""
        tool = SolanaDFlowSwapTool()
        tool._private_key = "5MaiiCavjCmn9Hs1o3eznqDEhRwxo7pXiAYez7keQUviUkauRiTMD8DrESdrNjN8zd9mTmVhRvBJeg5vhyvgrAhG"
        tool._rpc_url = "https://api.mainnet-beta.solana.com"

        with patch("sakit.solana_dflow_swap.DFlowSwap") as MockDFlow:
            mock_dflow_instance = MagicMock()
            mock_dflow_instance.get_order = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction=None,
                    error=None,
                )
            )
            MockDFlow.return_value = mock_dflow_instance

            result = await tool.execute(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "no transaction" in result["message"].lower()


class TestSolanaDFlowSwapPlugin:
    """Tests for SolanaDFlowSwapPlugin."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        plugin = SolanaDFlowSwapPlugin()
        assert plugin.name == "solana_dflow_swap"

    def test_plugin_description(self):
        """Should have meaningful description."""
        plugin = SolanaDFlowSwapPlugin()
        assert "DFlow" in plugin.description

    def test_plugin_get_tools_empty_before_init(self):
        """Should return empty list before initialization."""
        plugin = SolanaDFlowSwapPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize(self):
        """Should create tool on initialize."""
        plugin = SolanaDFlowSwapPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        tools = plugin.get_tools()
        assert len(tools) == 1
        assert isinstance(tools[0], SolanaDFlowSwapTool)

    def test_plugin_configure(self):
        """Should configure the tool."""
        plugin = SolanaDFlowSwapPlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)

        config = {
            "tools": {
                "solana_dflow_swap": {
                    "private_key": "test_private_key",
                    "platform_fee_bps": 100,
                }
            }
        }
        plugin.configure(config)

        tool = plugin.get_tools()[0]
        assert tool._private_key == "test_private_key"
        assert tool._platform_fee_bps == 100


class TestGetPlugin:
    """Tests for get_plugin function."""

    def test_get_plugin_returns_instance(self):
        """Should return SolanaDFlowSwapPlugin instance."""
        plugin = get_plugin()
        assert isinstance(plugin, SolanaDFlowSwapPlugin)
