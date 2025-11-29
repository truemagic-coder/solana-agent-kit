"""
Tests for Privy Ultra Tool.

Tests the PrivyUltraTool which swaps tokens using Jupiter Ultra API
via Privy delegated wallets.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sakit.privy_ultra import PrivyUltraTool, PrivyUltraPlugin


@pytest.fixture
def ultra_tool():
    """Create a configured PrivyUltraTool."""
    tool = PrivyUltraTool()
    tool.configure(
        {
            "tools": {
                "privy_ultra": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": "wallet-auth:test-signing-key",
                    "jupiter_api_key": "test-jupiter-key",
                    "referral_account": "RefAcct123",
                    "referral_fee": 50,
                }
            }
        }
    )
    return tool


@pytest.fixture
def ultra_tool_incomplete():
    """Create an incomplete PrivyUltraTool."""
    tool = PrivyUltraTool()
    tool.configure(
        {
            "tools": {
                "privy_ultra": {
                    "app_id": "test-app-id",
                    # Missing app_secret and signing_key
                }
            }
        }
    )
    return tool


class TestPrivyUltraToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self, ultra_tool):
        """Should have correct tool name."""
        assert ultra_tool.name == "privy_ultra"

    def test_schema_has_required_properties(self, ultra_tool):
        """Should include all required properties."""
        schema = ultra_tool.get_schema()
        assert "user_id" in schema["properties"]
        assert "input_mint" in schema["properties"]
        assert "output_mint" in schema["properties"]
        assert "amount" in schema["properties"]
        assert set(schema["required"]) == {
            "user_id",
            "input_mint",
            "output_mint",
            "amount",
        }

    def test_schema_property_types(self, ultra_tool):
        """Should have correct property types."""
        schema = ultra_tool.get_schema()
        assert schema["properties"]["user_id"]["type"] == "string"
        assert schema["properties"]["input_mint"]["type"] == "string"
        assert schema["properties"]["output_mint"]["type"] == "string"
        assert schema["properties"]["amount"]["type"] == "integer"


class TestPrivyUltraToolConfigure:
    """Test configuration method."""

    def test_configure_stores_privy_config(self, ultra_tool):
        """Should store Privy configuration."""
        assert ultra_tool.app_id == "test-app-id"
        assert ultra_tool.app_secret == "test-app-secret"
        assert ultra_tool.signing_key == "wallet-auth:test-signing-key"

    def test_configure_stores_jupiter_config(self, ultra_tool):
        """Should store Jupiter configuration."""
        assert ultra_tool.jupiter_api_key == "test-jupiter-key"
        assert ultra_tool.referral_account == "RefAcct123"
        assert ultra_tool.referral_fee == 50


class TestPrivyUltraToolExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_missing_config_error(self, ultra_tool_incomplete):
        """Should return error when config is incomplete."""
        result = await ultra_tool_incomplete.execute(
            user_id="did:privy:user123",
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1000000000,
        )

        assert result["status"] == "error"
        assert "config" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_wallet_found_error(self, ultra_tool):
        """Should return error when no delegated wallet found."""
        with patch(
            "sakit.privy_ultra.get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "wallet" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_transaction_error(self, ultra_tool):
        """Should return error when no transaction returned."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "WalletPubkey123...abc",
        }

        mock_order = MagicMock()
        mock_order.transaction = None

        with (
            patch(
                "sakit.privy_ultra.get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet_info,
            ),
            patch("sakit.privy_ultra.JupiterUltra") as MockUltra,
        ):
            mock_instance = AsyncMock()
            mock_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_instance

            result = await ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "transaction" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_wallet_found(self, ultra_tool):
        """Should return error when no wallet found."""
        with patch(
            "sakit.privy_ultra.get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "wallet" in result["message"].lower()


class TestPrivyUltraPlugin:
    """Test plugin class."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        plugin = PrivyUltraPlugin()
        assert plugin.name == "privy_ultra"

    def test_plugin_description(self):
        """Should have descriptive description."""
        plugin = PrivyUltraPlugin()
        assert (
            "swap" in plugin.description.lower()
            or "ultra" in plugin.description.lower()
        )

    def test_plugin_get_tools_empty_before_init(self):
        """Should return empty list before initialization."""
        plugin = PrivyUltraPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize(self):
        """Should initialize tool on registry."""
        plugin = PrivyUltraPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        assert plugin._tool is not None
        assert len(plugin.get_tools()) == 1
