"""
Tests for Privy Ultra Tool.

Tests the PrivyUltraTool which swaps tokens using Jupiter Ultra API
via Privy delegated wallets.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sakit.privy_ultra import (
    PrivyUltraTool,
    PrivyUltraPlugin,
    get_privy_embedded_wallet,
    get_plugin,
)


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

    def test_plugin_configure(self):
        """Should configure the tool after initialization."""
        plugin = PrivyUltraPlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)

        config = {
            "tools": {
                "privy_ultra": {
                    "app_id": "test-app",
                    "app_secret": "test-secret",
                    "signing_key": "wallet-auth:test-key",
                }
            }
        }
        plugin.configure(config)

        assert plugin.config == config
        assert plugin._tool.app_id == "test-app"


class TestGetPrivyEmbeddedWallet:
    """Test get_privy_embedded_wallet function."""

    @pytest.mark.asyncio
    async def test_finds_embedded_delegated_wallet(self):
        """Should find embedded delegated wallet with address field."""
        # Create a mock account with the expected attributes
        mock_account = MagicMock()
        mock_account.type = "wallet"
        mock_account.id = "wallet-123"
        mock_account.connector_type = "embedded"
        mock_account.delegated = True
        mock_account.address = "WalletAddress123"
        mock_account.public_key = None
        mock_account.chain_type = None

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_account]

        mock_privy_client = AsyncMock()
        mock_privy_client.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy_client, "did:privy:user123")

        assert result is not None
        assert result["wallet_id"] == "wallet-123"
        assert result["public_key"] == "WalletAddress123"

    @pytest.mark.asyncio
    async def test_finds_bot_first_wallet(self):
        """Should find bot-first wallet (API-created)."""
        mock_account = MagicMock()
        mock_account.type = "wallet"
        mock_account.id = "bot-wallet-456"
        mock_account.connector_type = None
        mock_account.delegated = False
        mock_account.chain_type = "solana"
        mock_account.address = "BotWalletAddress456"
        mock_account.public_key = None

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_account]

        mock_privy_client = AsyncMock()
        mock_privy_client.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy_client, "did:privy:user123")

        assert result is not None
        assert result["wallet_id"] == "bot-wallet-456"
        assert result["public_key"] == "BotWalletAddress456"

    @pytest.mark.asyncio
    async def test_finds_solana_embedded_wallet_type(self):
        """Should find solana_embedded_wallet type."""
        mock_account = MagicMock()
        mock_account.type = "solana_embedded_wallet"
        mock_account.id = "solana-wallet-789"
        mock_account.connector_type = None
        mock_account.delegated = False
        mock_account.chain_type = None
        mock_account.address = "SolanaWalletAddress789"
        mock_account.public_key = None

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_account]

        mock_privy_client = AsyncMock()
        mock_privy_client.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy_client, "did:privy:user123")

        assert result is not None
        assert result["wallet_id"] == "solana-wallet-789"
        assert result["public_key"] == "SolanaWalletAddress789"

    @pytest.mark.asyncio
    async def test_returns_none_for_no_suitable_wallet(self):
        """Should return None when no suitable wallet found."""
        mock_account = MagicMock()
        mock_account.type = "email"
        mock_account.connector_type = None
        mock_account.delegated = False
        mock_account.chain_type = None

        mock_user = MagicMock()
        mock_user.linked_accounts = [mock_account]

        mock_privy_client = AsyncMock()
        mock_privy_client.users.get = AsyncMock(return_value=mock_user)

        result = await get_privy_embedded_wallet(mock_privy_client, "did:privy:user123")

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_on_api_error(self):
        """Should raise exception on API error."""
        mock_privy_client = AsyncMock()
        mock_privy_client.users.get = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        with pytest.raises(Exception):
            await get_privy_embedded_wallet(mock_privy_client, "did:privy:user123")


class TestPrivyUltraToolExecuteSuccess:
    """Test successful execute paths."""

    TEST_EC_KEY_SEC1 = "MHcCAQEEIH6phbwVBTxg+QYJMSqHXcLoiTpmO163WjA8Td/+DqQ3oAoGCCqGSM49AwEHoUQDQgAEoY29/uiiWfItIYBAmejKuM17a0GackAbFG4sNs1ObTUilKQ2V/7WkTRC0xk7IgLwCRUI1e/Yk5wQFCjlajvilw=="

    @pytest.fixture
    def configured_ultra_tool(self):
        """Create a fully configured PrivyUltraTool."""
        tool = PrivyUltraTool()
        tool.configure(
            {
                "tools": {
                    "privy_ultra": {
                        "app_id": "test-app-id",
                        "app_secret": "test-app-secret",
                        "signing_key": f"wallet-auth:{self.TEST_EC_KEY_SEC1}",
                        "jupiter_api_key": "test-jupiter-key",
                        "referral_account": "RefAcct123",
                        "referral_fee": 50,
                    }
                }
            }
        )
        return tool

    @pytest.mark.asyncio
    async def test_execute_successful_swap(self, configured_ultra_tool):
        """Should successfully execute a swap."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "WalletPubkey123",
        }

        mock_order = MagicMock()
        mock_order.transaction = "mock-transaction-base64"
        mock_order.request_id = "req-123"
        mock_order.swap_type = "ExactIn"
        mock_order.gasless = False

        mock_execute_result = MagicMock()
        mock_execute_result.status = "Success"
        mock_execute_result.signature = "sig-456"
        mock_execute_result.input_amount_result = 1000000000
        mock_execute_result.output_amount_result = 50000000

        mock_sign_result = {"data": {"signedTransaction": "signed-tx-base64"}}

        with (
            patch(
                "sakit.privy_ultra.get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet_info,
            ),
            patch("sakit.privy_ultra.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra.privy_sign_transaction",
                new_callable=AsyncMock,
                return_value=mock_sign_result,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.get_order = AsyncMock(return_value=mock_order)
            mock_instance.execute_order = AsyncMock(return_value=mock_execute_result)
            MockUltra.return_value = mock_instance

            result = await configured_ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "success"
            assert result["signature"] == "sig-456"
            assert result["input_amount"] == 1000000000
            assert result["output_amount"] == 50000000

    @pytest.mark.asyncio
    async def test_execute_swap_failure_from_jupiter(self, configured_ultra_tool):
        """Should return error when Jupiter swap fails."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "WalletPubkey123",
        }

        mock_order = MagicMock()
        mock_order.transaction = "mock-transaction-base64"
        mock_order.request_id = "req-123"

        mock_execute_result = MagicMock()
        mock_execute_result.status = "Failed"
        mock_execute_result.error = "Insufficient balance"
        mock_execute_result.code = "INSUFFICIENT_FUNDS"
        mock_execute_result.signature = None

        mock_sign_result = {"data": {"signedTransaction": "signed-tx-base64"}}

        with (
            patch(
                "sakit.privy_ultra.get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet_info,
            ),
            patch("sakit.privy_ultra.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra.privy_sign_transaction",
                new_callable=AsyncMock,
                return_value=mock_sign_result,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.get_order = AsyncMock(return_value=mock_order)
            mock_instance.execute_order = AsyncMock(return_value=mock_execute_result)
            MockUltra.return_value = mock_instance

            result = await configured_ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "Insufficient balance" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_privy_signing_failure(self, configured_ultra_tool):
        """Should return error when Privy signing fails."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "WalletPubkey123",
        }

        mock_order = MagicMock()
        mock_order.transaction = "mock-transaction-base64"
        mock_order.request_id = "req-123"

        # No signedTransaction in response
        mock_sign_result = {"data": {}}

        with (
            patch(
                "sakit.privy_ultra.get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet_info,
            ),
            patch("sakit.privy_ultra.JupiterUltra") as MockUltra,
            patch(
                "sakit.privy_ultra.privy_sign_transaction",
                new_callable=AsyncMock,
                return_value=mock_sign_result,
            ),
        ):
            mock_instance = AsyncMock()
            mock_instance.get_order = AsyncMock(return_value=mock_order)
            MockUltra.return_value = mock_instance

            result = await configured_ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "sign" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, configured_ultra_tool):
        """Should handle exceptions gracefully."""
        mock_wallet_info = {
            "wallet_id": "wallet-123",
            "public_key": "WalletPubkey123",
        }

        with (
            patch(
                "sakit.privy_ultra.get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet_info,
            ),
            patch("sakit.privy_ultra.JupiterUltra") as MockUltra,
        ):
            mock_instance = AsyncMock()
            mock_instance.get_order = AsyncMock(side_effect=Exception("Network error"))
            MockUltra.return_value = mock_instance

            result = await configured_ultra_tool.execute(
                user_id="did:privy:user123",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1000000000,
            )

            assert result["status"] == "error"
            assert "Network error" in result["message"]


class TestGetPlugin:
    """Test get_plugin function."""

    def test_get_plugin_returns_instance(self):
        """Should return a PrivyUltraPlugin instance."""
        plugin = get_plugin()
        assert isinstance(plugin, PrivyUltraPlugin)
        assert plugin.name == "privy_ultra"
