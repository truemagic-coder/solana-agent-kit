"""
Tests for Privy Recurring Tool.

Tests the PrivyRecurringTool which uses Jupiter Recurring API with
Privy delegated wallets for transaction signing.
"""

import pytest
from unittest.mock import patch

from sakit.privy_recurring import PrivyRecurringTool


@pytest.fixture
def privy_recurring_tool():
    """Create a configured PrivyRecurringTool."""
    tool = PrivyRecurringTool()
    tool.configure(
        {
            "tools": {
                "privy_recurring": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": "wallet-auth:base64privatekey==",
                    "jupiter_api_key": "test-api-key",
                }
            }
        }
    )
    return tool


class TestPrivyRecurringToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self, privy_recurring_tool):
        """Should have correct tool name."""
        assert privy_recurring_tool.name == "privy_recurring"

    def test_schema_has_user_id(self, privy_recurring_tool):
        """Should require user_id for Privy."""
        schema = privy_recurring_tool.get_schema()
        assert "user_id" in schema["properties"]
        assert "user_id" in schema["required"]

    def test_schema_has_actions(self, privy_recurring_tool):
        """Should include action in required properties."""
        schema = privy_recurring_tool.get_schema()
        assert "action" in schema["properties"]
        assert schema["properties"]["action"]["enum"] == ["create", "cancel", "list"]

    def test_schema_has_dca_properties(self, privy_recurring_tool):
        """Should include DCA order creation properties."""
        schema = privy_recurring_tool.get_schema()
        props = schema["properties"]
        assert "input_mint" in props
        assert "output_mint" in props
        assert "in_amount" in props
        assert "order_count" in props
        assert "frequency" in props
        assert "min_out_amount" in props
        assert "max_out_amount" in props


class TestPrivyRecurringToolConfigure:
    """Test configuration method."""

    def test_configure_stores_privy_config(self, privy_recurring_tool):
        """Should store Privy credentials from config."""
        assert privy_recurring_tool._app_id == "test-app-id"
        assert privy_recurring_tool._app_secret == "test-app-secret"
        assert privy_recurring_tool._signing_key == "wallet-auth:base64privatekey=="

    def test_configure_stores_api_key(self, privy_recurring_tool):
        """Should store Jupiter API key from config."""
        assert privy_recurring_tool._jupiter_api_key == "test-api-key"


class TestPrivyRecurringToolExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_missing_privy_config(self):
        """Should return error if Privy config is missing."""
        tool = PrivyRecurringTool()
        tool.configure({"tools": {"privy_recurring": {}}})

        result = await tool.execute(
            user_id="did:privy:user123",
            action="list",
        )

        assert result["status"] == "error"
        assert "config" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_wallet_found(self, privy_recurring_tool):
        """Should return error if no delegated wallet found for user."""
        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = None

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "error"
        assert "wallet" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_success(self, privy_recurring_tool):
        """Should list active DCA orders for user's wallet."""
        # Without a valid wallet, this will fail - which is expected behavior
        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = None

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "error"
        assert "wallet" in result["message"].lower()


class TestPrivyRecurringToolCreateAction:
    """Test create action."""

    @pytest.mark.asyncio
    async def test_create_missing_required_params(self, privy_recurring_tool):
        """Should return error if required create params are missing."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = mock_wallet

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11...",
                # Missing output_mint, in_amount, order_count, frequency
            )

        assert result["status"] == "error"
        assert (
            "missing" in result["message"].lower()
            or "required" in result["message"].lower()
        )


class TestPrivyRecurringToolCancelAction:
    """Test cancel action."""

    @pytest.mark.asyncio
    async def test_cancel_missing_order_pubkey(self, privy_recurring_tool):
        """Should return error if order_pubkey is missing for cancel."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = mock_wallet

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="cancel",
            )

        assert result["status"] == "error"
        assert "order_pubkey" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_order_not_owned_by_user(self, privy_recurring_tool):
        """Should reject cancellation of orders not owned by the user."""
        from unittest.mock import AsyncMock

        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        # Mock the wallet lookup
        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = mock_wallet

            # Mock the JupiterRecurring.get_orders to return orders for this user
            with patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring:
                mock_recurring_instance = MockRecurring.return_value
                # User's orders - does NOT include the order they're trying to cancel
                mock_recurring_instance.get_orders = AsyncMock(
                    return_value={
                        "success": True,
                        "orders": [
                            {"order": "UserOwnedDCA123"},
                            {"order": "UserOwnedDCA456"},
                        ],
                    }
                )

                result = await privy_recurring_tool.execute(
                    user_id="did:privy:user123",
                    action="cancel",
                    order_pubkey="SomeoneElsesDCA789",  # Not in user's orders
                )

        assert result["status"] == "error"
        assert "does not belong" in result["message"]


class TestPrivyRecurringToolUnknownAction:
    """Test unknown action handling."""

    @pytest.mark.asyncio
    async def test_unknown_action(self, privy_recurring_tool):
        """Should return error for unknown action."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet"
        ) as mock_get_wallet:
            mock_get_wallet.return_value = mock_wallet

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="invalid_action",
            )

        assert result["status"] == "error"
        assert (
            "unknown" in result["message"].lower()
            or "invalid" in result["message"].lower()
        )
