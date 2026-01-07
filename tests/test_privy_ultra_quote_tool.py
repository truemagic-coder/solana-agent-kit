"""
Tests for Privy Ultra Quote Tool.

Tests the PrivyUltraQuoteTool which provides swap previews using Jupiter Ultra API
via Privy delegated wallets. Shows slippage and price impact without executing.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sakit.privy_ultra_quote import (
    PrivyUltraQuoteTool,
    PrivyUltraQuotePlugin,
    get_privy_embedded_wallet,
    get_plugin,
)


@pytest.fixture
def quote_tool():
    """Create a configured PrivyUltraQuoteTool."""
    tool = PrivyUltraQuoteTool()
    tool.configure(
        {
            "tools": {
                "privy_ultra_quote": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "jupiter_api_key": "test-jupiter-key",
                    "referral_account": "RefAcct123",
                    "referral_fee": 50,
                }
            }
        }
    )
    return tool


@pytest.fixture
def quote_tool_with_payer():
    """Create a PrivyUltraQuoteTool with payer."""
    tool = PrivyUltraQuoteTool()
    tool.configure(
        {
            "tools": {
                "privy_ultra_quote": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "jupiter_api_key": "test-jupiter-key",
                    "payer_private_key": "PayerPrivateKey...base58",
                }
            }
        }
    )
    return tool


@pytest.fixture
def quote_tool_incomplete():
    """Create an incomplete PrivyUltraQuoteTool."""
    tool = PrivyUltraQuoteTool()
    tool.configure(
        {
            "tools": {
                "privy_ultra_quote": {
                    "app_id": "test-app-id",
                    # Missing app_secret
                }
            }
        }
    )
    return tool


class TestPrivyUltraQuoteToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self, quote_tool):
        """Should have correct tool name."""
        assert quote_tool.name == "privy_ultra_quote"

    def test_schema_has_required_properties(self, quote_tool):
        """Should include all required properties."""
        schema = quote_tool.get_schema()
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

    def test_schema_property_types(self, quote_tool):
        """Should have correct property types."""
        schema = quote_tool.get_schema()
        assert schema["properties"]["user_id"]["type"] == "string"
        assert schema["properties"]["input_mint"]["type"] == "string"
        assert schema["properties"]["output_mint"]["type"] == "string"
        assert schema["properties"]["amount"]["type"] == "integer"


class TestPrivyUltraQuoteToolConfigure:
    """Test configuration method."""

    def test_configure_stores_privy_config(self, quote_tool):
        """Should store Privy configuration."""
        assert quote_tool.app_id == "test-app-id"
        assert quote_tool.app_secret == "test-app-secret"

    def test_configure_stores_jupiter_config(self, quote_tool):
        """Should store Jupiter configuration."""
        assert quote_tool.jupiter_api_key == "test-jupiter-key"
        assert quote_tool.referral_account == "RefAcct123"
        assert quote_tool.referral_fee == 50

    def test_configure_stores_payer_key(self, quote_tool_with_payer):
        """Should store payer private key."""
        assert quote_tool_with_payer.payer_private_key == "PayerPrivateKey...base58"


class TestPrivyUltraQuoteToolExecute:
    """Test execute method for quote preview."""

    @pytest.mark.asyncio
    async def test_execute_missing_privy_config_error(self, quote_tool_incomplete):
        """Should return error when Privy config is incomplete."""
        result = await quote_tool_incomplete.execute(
            user_id="did:privy:user123",
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1000000000,
        )

        assert result["status"] == "error"
        assert "privy" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_user_id_sanitization(self, quote_tool):
        """Should handle user_id with extra formatting."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "UserPubkey123",
        }

        mock_order = MagicMock()
        mock_order.input_mint = "So11111111111111111111111111111111111111112"
        mock_order.output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        mock_order.in_amount = "1000000000"
        mock_order.out_amount = "50000000"
        mock_order.slippage_bps = 100
        mock_order.price_impact_pct = "0.5"
        mock_order.swap_type = "ExactIn"
        mock_order.gasless = False

        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch("sakit.privy_ultra_quote.Keypair") as MockKeypair,
            patch("sakit.privy_ultra_quote.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = mock_wallet_info

            mock_payer_keypair = MagicMock()
            mock_payer_keypair.pubkey.return_value = "PayerPubkey123"
            MockKeypair.from_base58_string.return_value = mock_payer_keypair

            mock_ultra_instance = AsyncMock()
            mock_ultra_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_ultra_instance

            result = await quote_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_no_wallet_found(self, quote_tool):
        """Should return error when no wallet found for user."""
        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = None

            result = await quote_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "wallet" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_success_returns_quote(self, quote_tool):
        """Should return quote with slippage and price impact."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "UserPubkey123",
        }

        mock_order = MagicMock()
        mock_order.input_mint = "So11111111111111111111111111111111111111112"
        mock_order.output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        mock_order.in_amount = "1000000000"
        mock_order.out_amount = "50000000"
        mock_order.slippage_bps = 100
        mock_order.price_impact_pct = "0.5"
        mock_order.swap_type = "ExactIn"
        mock_order.gasless = False

        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch("sakit.privy_ultra_quote.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = mock_wallet_info

            mock_ultra_instance = AsyncMock()
            mock_ultra_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_ultra_instance

            result = await quote_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "success"
            assert result["input_mint"] == "So11111111111111111111111111111111111111112"
            assert (
                result["output_mint"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            )
            assert result["in_amount"] == "1000000000"
            assert result["out_amount"] == "50000000"
            assert result["slippage_bps"] == 100
            assert result["price_impact_pct"] == "0.5"
            assert result["swap_type"] == "ExactIn"
            assert result["gasless"] is False
            assert "preview only" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_with_payer(self, quote_tool_with_payer):
        """Should include payer in get_order call."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "UserPubkey123",
        }

        mock_order = MagicMock()
        mock_order.input_mint = "So11111111111111111111111111111111111111112"
        mock_order.output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        mock_order.in_amount = "1000000000"
        mock_order.out_amount = "50000000"
        mock_order.slippage_bps = 100
        mock_order.price_impact_pct = "0.5"
        mock_order.swap_type = "ExactIn"
        mock_order.gasless = True

        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch("sakit.privy_ultra_quote.Keypair") as MockKeypair,
            patch("sakit.privy_ultra_quote.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = mock_wallet_info

            mock_payer_keypair = MagicMock()
            mock_payer_keypair.pubkey.return_value = "PayerPubkey123"
            MockKeypair.from_base58_string.return_value = mock_payer_keypair

            mock_ultra_instance = AsyncMock()
            mock_ultra_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_ultra_instance

            result = await quote_tool_with_payer.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            # Verify get_order was called with payer
            call_args = mock_ultra_instance.get_order.call_args
            assert call_args.kwargs["payer"] == "PayerPubkey123"

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_jupiter_api_error(self, quote_tool):
        """Should handle Jupiter API errors gracefully."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "UserPubkey123",
        }

        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch("sakit.privy_ultra_quote.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = mock_wallet_info

            mock_ultra_instance = AsyncMock()
            mock_ultra_instance.get_order = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            MockUltra.return_value = mock_ultra_instance

            result = await quote_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "API rate limit" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_privy_closes_client(self, quote_tool):
        """Should close Privy client after execution."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "UserPubkey123",
        }

        mock_order = MagicMock()
        mock_order.input_mint = "So11111111111111111111111111111111111111112"
        mock_order.output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        mock_order.in_amount = "1000000000"
        mock_order.out_amount = "50000000"
        mock_order.slippage_bps = 100
        mock_order.price_impact_pct = "0.5"
        mock_order.swap_type = "ExactIn"
        mock_order.gasless = False

        with (
            patch("sakit.privy_ultra_quote.AsyncPrivyAPI") as MockPrivyAPI,
            patch("sakit.privy_ultra_quote.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra_quote.get_privy_embedded_wallet"
            ) as mock_get_wallet,
        ):
            mock_privy = AsyncMock()
            mock_privy.close = AsyncMock()
            MockPrivyAPI.return_value = mock_privy

            mock_get_wallet.return_value = mock_wallet_info

            mock_ultra_instance = AsyncMock()
            mock_ultra_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_ultra_instance

            result = await quote_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            # Verify Privy client was closed
            mock_privy.close.assert_called_once()
            assert result["status"] == "success"


class TestGetPrivyEmbeddedWallet:
    """Test get_privy_embedded_wallet helper function."""

    @pytest.mark.asyncio
    async def test_get_wallet_success_embedded_delegated(self):
        """Should return wallet info when found (SDK-created embedded delegated)."""
        mock_wallet = MagicMock()
        mock_wallet.connector_type = "embedded"
        mock_wallet.delegated = True
        mock_wallet.id = "wallet-123"
        mock_wallet.address = "UserPubkey123"
        mock_wallet.public_key = None
        mock_wallet.type = "solana_embedded_wallet"
        mock_wallet.chain_type = None

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_wallet]

        mock_privy = AsyncMock()
        mock_privy.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy, "did:privy:user123")

        assert result is not None
        assert result["wallet_id"] == "wallet-123"
        assert result["public_key"] == "UserPubkey123"

    @pytest.mark.asyncio
    async def test_get_wallet_success_bot_first(self):
        """Should return wallet info when found (API-created bot-first)."""
        mock_wallet = MagicMock()
        mock_wallet.type = "wallet"
        mock_wallet.chain_type = "solana"
        mock_wallet.id = "wallet-456"
        mock_wallet.address = "UserPubkey456"
        mock_wallet.public_key = None
        mock_wallet.connector_type = None
        mock_wallet.delegated = False

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_wallet]

        mock_privy = AsyncMock()
        mock_privy.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy, "did:privy:user123")

        assert result is not None
        assert result["wallet_id"] == "wallet-456"
        assert result["public_key"] == "UserPubkey456"

    @pytest.mark.asyncio
    async def test_get_wallet_not_found_no_solana(self):
        """Should return None when no Solana wallet found."""
        mock_wallet = MagicMock()
        mock_wallet.type = "ethereum_wallet"
        mock_wallet.chain_type = "ethereum"
        mock_wallet.connector_type = None
        mock_wallet.delegated = False

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_wallet]

        mock_privy = AsyncMock()
        mock_privy.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy, "did:privy:user123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_wallet_api_error(self):
        """Should handle API errors gracefully."""
        mock_privy = AsyncMock()
        mock_privy.users.get = AsyncMock(side_effect=Exception("Privy API error"))

        result = await get_privy_embedded_wallet(mock_privy, "did:privy:user123")

        assert result is None


class TestPrivyUltraQuotePlugin:
    """Test plugin functionality."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        plugin = PrivyUltraQuotePlugin()
        assert plugin.name == "privy_ultra_quote"

    def test_plugin_description(self):
        """Should have proper description."""
        plugin = PrivyUltraQuotePlugin()
        assert plugin.description is not None
        assert len(plugin.description) > 0

    def test_plugin_initialize(self):
        """Should initialize with tool registry."""
        plugin = PrivyUltraQuotePlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)
        assert plugin.tool_registry == mock_registry
        assert plugin._tool is not None

    def test_plugin_configure(self):
        """Should pass config to tool."""
        plugin = PrivyUltraQuotePlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)

        config = {
            "tools": {
                "privy_ultra_quote": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "jupiter_api_key": "test-api-key",
                }
            }
        }
        plugin.configure(config)
        assert plugin._tool.app_id == "test-app-id"
        assert plugin._tool.app_secret == "test-app-secret"
        assert plugin._tool.jupiter_api_key == "test-api-key"

    def test_plugin_get_tools(self):
        """Should return configured tools."""
        plugin = PrivyUltraQuotePlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)
        tools = plugin.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "privy_ultra_quote"


def test_get_plugin():
    """Should return PrivyUltraQuotePlugin instance."""
    plugin = get_plugin()
    assert isinstance(plugin, PrivyUltraQuotePlugin)
