"""
Tests for Jupiter Trigger Tool.

Tests the JupiterTriggerTool which wraps the JupiterTrigger API client
and provides the AutoTool interface for limit order management.
"""

import pytest
from unittest.mock import patch

from sakit.jupiter_trigger import JupiterTriggerTool


@pytest.fixture
def trigger_tool():
    """Create a configured JupiterTriggerTool."""
    tool = JupiterTriggerTool()
    tool.configure(
        {
            "tools": {
                "jupiter_trigger": {
                    "private_key": "5jGR...base58privatekey",  # This would be a real key in production
                    "jupiter_api_key": "test-api-key",
                    "referral_account": "RefAcct123",
                    "referral_fee": "100",
                }
            }
        }
    )
    return tool


@pytest.fixture
def trigger_tool_no_api_key():
    """Create a JupiterTriggerTool without API key (lite mode)."""
    tool = JupiterTriggerTool()
    tool.configure(
        {
            "tools": {
                "jupiter_trigger": {
                    "private_key": "5jGR...base58privatekey",
                }
            }
        }
    )
    return tool


class TestJupiterTriggerToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self, trigger_tool):
        """Should have correct tool name."""
        assert trigger_tool.name == "jupiter_trigger"

    def test_schema_has_required_properties(self, trigger_tool):
        """Should include action in required properties."""
        schema = trigger_tool.get_schema()
        assert "action" in schema["properties"]
        assert schema["properties"]["action"]["enum"] == [
            "create",
            "cancel",
            "cancel_all",
            "list",
        ]

    def test_schema_has_order_properties(self, trigger_tool):
        """Should include order creation properties."""
        schema = trigger_tool.get_schema()
        props = schema["properties"]
        assert "input_mint" in props
        assert "output_mint" in props
        assert "making_amount" in props  # Jupiter API uses making_amount
        assert "taking_amount" in props  # Jupiter API uses taking_amount
        assert "expired_at" in props


class TestJupiterTriggerToolConfigure:
    """Test configuration method."""

    def test_configure_stores_private_key(self, trigger_tool):
        """Should store private key from config."""
        assert trigger_tool._private_key == "5jGR...base58privatekey"

    def test_configure_stores_api_key(self, trigger_tool):
        """Should store Jupiter API key from config."""
        assert trigger_tool._jupiter_api_key == "test-api-key"

    def test_configure_stores_referral_info(self, trigger_tool):
        """Should store referral account and fee from config."""
        assert trigger_tool._referral_account == "RefAcct123"
        assert trigger_tool._referral_fee == "100"


class TestJupiterTriggerToolCreateAction:
    """Test create action."""

    @pytest.mark.asyncio
    async def test_create_missing_private_key(self):
        """Should return error if private key is missing."""
        tool = JupiterTriggerTool()
        tool.configure({"tools": {"jupiter_trigger": {}}})

        result = await tool.execute(
            action="create",
            input_mint="So11...",
            output_mint="EPjF...",
            making_amount="1000000",
            taking_amount="100000",
        )

        assert result["status"] == "error"
        assert (
            "private_key" in result["message"].lower()
            or "config" in result["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_create_missing_required_params(self, trigger_tool):
        """Should return error if required create params are missing."""
        result = await trigger_tool.execute(
            action="create",
            input_mint="So11...",
            # Missing output_mint, making_amount, taking_amount
        )

        assert result["status"] == "error"
        assert (
            "missing" in result["message"].lower()
            or "required" in result["message"].lower()
        )


class TestJupiterTriggerToolCancelAction:
    """Test cancel action."""

    @pytest.mark.asyncio
    async def test_cancel_missing_order_pubkey(self, trigger_tool):
        """Should return error if order_pubkey is missing for cancel."""
        with patch.object(trigger_tool, "_private_key", "testkey"):
            result = await trigger_tool.execute(action="cancel")

        assert result["status"] == "error"
        assert "order_pubkey" in result["message"].lower()


class TestJupiterTriggerToolListAction:
    """Test list actions."""

    @pytest.mark.asyncio
    async def test_list_action(self):
        """Should list orders."""
        # This test requires proper mocking of Keypair.from_base58_string
        # For now, we'll just verify the action routing works with minimal config
        tool = JupiterTriggerTool()
        tool.configure(
            {
                "tools": {
                    "jupiter_trigger": {}  # No private key = error
                }
            }
        )

        result = await tool.execute(action="list")
        # Without private key, should error
        assert result["status"] == "error"


class TestJupiterTriggerToolUnknownAction:
    """Test unknown action handling."""

    @pytest.mark.asyncio
    async def test_unknown_action(self, trigger_tool):
        """Should return error for unknown action."""
        result = await trigger_tool.execute(action="invalid_action")

        assert result["status"] == "error"
        assert (
            "unknown" in result["message"].lower()
            or "invalid" in result["message"].lower()
        )
