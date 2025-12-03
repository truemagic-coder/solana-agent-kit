"""Tests for Privy DFlow swap tool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from sakit.privy_dflow import (
    PrivyDFlowTool,
    PrivyDFlowPlugin,
    get_plugin,
)


class TestPrivyDFlowToolInit:
    """Tests for PrivyDFlowTool initialization."""

    def test_tool_name(self):
        """Should have correct tool name."""
        tool = PrivyDFlowTool()
        assert tool.name == "privy_dflow"

    def test_tool_description(self):
        """Should have meaningful description."""
        tool = PrivyDFlowTool()
        assert "DFlow" in tool.description
        assert "swap" in tool.description.lower()


class TestPrivyDFlowToolSchema:
    """Tests for PrivyDFlowTool schema."""

    def test_schema_has_required_fields(self):
        """Should have all required fields in schema."""
        tool = PrivyDFlowTool()
        schema = tool.get_schema()

        assert "properties" in schema
        props = schema["properties"]

        assert "user_id" in props
        assert "input_mint" in props
        assert "output_mint" in props
        assert "amount" in props

    def test_schema_required_fields(self):
        """Should mark correct fields as required."""
        tool = PrivyDFlowTool()
        schema = tool.get_schema()

        required = schema.get("required", [])
        assert "user_id" in required
        assert "input_mint" in required
        assert "output_mint" in required
        assert "amount" in required


class TestPrivyDFlowToolConfigure:
    """Tests for PrivyDFlowTool configuration."""

    def test_configure_sets_credentials(self):
        """Should set credentials from config."""
        tool = PrivyDFlowTool()
        config = {
            "tools": {
                "privy_dflow": {
                    "app_id": "test_app_id",
                    "app_secret": "test_app_secret",
                    "signing_key": "test_signing_key",
                    "platform_fee_bps": 50,
                    "fee_account": "FeeAccount123",
                }
            }
        }

        tool.configure(config)

        assert tool._app_id == "test_app_id"
        assert tool._app_secret == "test_app_secret"
        assert tool._signing_key == "test_signing_key"
        assert tool._platform_fee_bps == 50
        assert tool._fee_account == "FeeAccount123"


class TestPrivyDFlowToolExecute:
    """Tests for PrivyDFlowTool execute method."""

    @pytest.fixture
    def configured_tool(self):
        """Create a configured tool for testing."""
        tool = PrivyDFlowTool()
        tool.configure(
            {
                "tools": {
                    "privy_dflow": {
                        "app_id": "test_app_id",
                        "app_secret": "test_app_secret",
                        "signing_key": "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg"
                        + "A" * 43
                        + "=",
                        "platform_fee_bps": 50,
                        "fee_account": "FeeAccount123",
                        "rpc_url": "https://api.mainnet-beta.solana.com",
                    }
                }
            }
        )
        return tool

    @pytest.mark.asyncio
    async def test_execute_missing_config(self):
        """Should return error when config is missing."""
        tool = PrivyDFlowTool()

        result = await tool.execute(
            user_id="did:privy:test123",
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount="1000000000",
        )

        assert result["status"] == "error"
        assert "config" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_wallet(self, configured_tool):
        """Should return error when user has no wallet."""
        mock_user = MagicMock()
        mock_user.linked_accounts = []

        with patch("sakit.privy_dflow.AsyncPrivyAPI") as MockPrivy:
            mock_privy_instance = AsyncMock()
            mock_privy_instance.users.get = AsyncMock(return_value=mock_user)
            mock_privy_instance.close = AsyncMock()
            MockPrivy.return_value = mock_privy_instance

            result = await configured_tool.execute(
                user_id="did:privy:test123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount="1000000000",
            )

            assert result["status"] == "error"
            assert "wallet" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_dflow_api_error(self, configured_tool):
        """Should return error when DFlow API fails."""
        mock_user = MagicMock()
        mock_wallet = MagicMock()
        mock_wallet.connector_type = "embedded"
        mock_wallet.delegated = True
        mock_wallet.id = "wallet123"
        mock_wallet.address = "WalletAddress123"
        mock_wallet.public_key = "WalletAddress123"
        mock_user.linked_accounts = [mock_wallet]

        with patch("sakit.privy_dflow.AsyncPrivyAPI") as MockPrivy:
            mock_privy_instance = AsyncMock()
            mock_privy_instance.users.get = AsyncMock(return_value=mock_user)
            mock_privy_instance.close = AsyncMock()
            MockPrivy.return_value = mock_privy_instance

            with patch("sakit.privy_dflow.DFlowSwap") as MockDFlow:
                mock_dflow_instance = MagicMock()
                mock_dflow_instance.get_order = AsyncMock(
                    return_value=MagicMock(
                        success=False,
                        error="Insufficient liquidity",
                    )
                )
                MockDFlow.return_value = mock_dflow_instance

                result = await configured_tool.execute(
                    user_id="did:privy:test123",
                    input_mint="So11111111111111111111111111111111111111112",
                    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount="1000000000",
                )

                assert result["status"] == "error"
                assert "liquidity" in result["message"].lower()


class TestPrivyDFlowPlugin:
    """Tests for PrivyDFlowPlugin."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        plugin = PrivyDFlowPlugin()
        assert plugin.name == "privy_dflow"

    def test_plugin_description(self):
        """Should have meaningful description."""
        plugin = PrivyDFlowPlugin()
        assert "DFlow" in plugin.description

    def test_plugin_get_tools_empty_before_init(self):
        """Should return empty list before initialization."""
        plugin = PrivyDFlowPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize(self):
        """Should create tool on initialize."""
        plugin = PrivyDFlowPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        tools = plugin.get_tools()
        assert len(tools) == 1
        assert isinstance(tools[0], PrivyDFlowTool)

    def test_plugin_configure(self):
        """Should configure the tool."""
        plugin = PrivyDFlowPlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)

        config = {
            "tools": {
                "privy_dflow": {
                    "app_id": "test_app_id",
                    "app_secret": "test_app_secret",
                    "signing_key": "test_signing_key",
                }
            }
        }
        plugin.configure(config)

        tool = plugin.get_tools()[0]
        assert tool._app_id == "test_app_id"


class TestGetPlugin:
    """Tests for get_plugin function."""

    def test_get_plugin_returns_instance(self):
        """Should return PrivyDFlowPlugin instance."""
        plugin = get_plugin()
        assert isinstance(plugin, PrivyDFlowPlugin)
