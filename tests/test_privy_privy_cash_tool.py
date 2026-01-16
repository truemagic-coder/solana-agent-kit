"""Tests for PrivyPrivyCashTool."""

import pytest
import respx
from httpx import Response

from sakit.privy_privy_cash import PrivyPrivyCashTool, PrivyPrivyCashPlugin, get_plugin


@pytest.fixture
def cash_tool():
    tool = PrivyPrivyCashTool()
    tool.configure({"tools": {"privy_privy_cash": {"api_key": "test-api-key"}}})
    return tool


@pytest.fixture
def cash_tool_no_key():
    tool = PrivyPrivyCashTool()
    tool.configure({})
    return tool


class TestPrivyPrivyCashToolSchema:
    def test_tool_name(self, cash_tool):
        assert cash_tool.name == "privy_privy_cash"

    def test_schema_has_required_properties(self, cash_tool):
        schema = cash_tool.get_schema()
        assert "action" in schema["properties"]
        assert "wallet_id" in schema["properties"]
        assert "amount" in schema["properties"]
        assert "recipient" in schema["properties"]
        assert "token" in schema["properties"]


class TestPrivyPrivyCashToolExecute:
    @pytest.mark.asyncio
    async def test_unknown_action(self, cash_tool):
        result = await cash_tool.execute(action="nope")
        assert result["success"] is False
        assert "unknown action" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_deposit_missing_params(self, cash_tool):
        result = await cash_tool.execute(action="deposit", wallet_id="", amount=0)
        assert result["success"] is False
        assert "wallet_id" in result["error"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_transfer_success(self, cash_tool):
        respx.post("https://cash.solana-agent.com/transfer").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        result = await cash_tool.execute(
            action="transfer",
            wallet_id="wallet-123",
            amount=1.25,
            recipient="recipient-abc",
            token="SOL",
        )
        assert result["success"] is True
        assert result["data"]["status"] == "ok"

    @pytest.mark.asyncio
    @respx.mock
    async def test_balance_success(self, cash_tool):
        respx.post("https://cash.solana-agent.com/balance").mock(
            return_value=Response(200, json={"status": "ok", "balance": 2.5})
        )
        result = await cash_tool.execute(
            action="balance",
            wallet_id="wallet-123",
            token="USDC",
        )
        assert result["success"] is True
        assert result["data"]["balance"] == 2.5


class TestPrivyPrivyCashPlugin:
    def test_get_plugin(self):
        plugin = get_plugin()
        assert isinstance(plugin, PrivyPrivyCashPlugin)
        assert plugin.name == "privy_privy_cash"
