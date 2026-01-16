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

    def test_configure_base_url_override(self):
        tool = PrivyPrivyCashTool()
        tool.configure(
            {
                "tools": {
                    "privy_privy_cash": {
                        "api_key": "test-api-key",
                        "base_url": "https://example.com",
                    }
                }
            }
        )
        assert tool.base_url == "https://example.com"


class TestPrivyPrivyCashToolExecute:
    @pytest.mark.asyncio
    async def test_missing_api_key(self, cash_tool_no_key):
        result = await cash_tool_no_key.execute(
            action="balance",
            wallet_id="wallet-123",
            token="SOL",
        )
        assert result["success"] is False
        assert "api key" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unknown_action(self, cash_tool):
        result = await cash_tool.execute(action="nope")
        assert result["success"] is False
        assert "unknown action" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_token(self, cash_tool):
        result = await cash_tool.execute(
            action="balance",
            wallet_id="wallet-123",
            token="BAD",
        )
        assert result["success"] is False
        assert "token must" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_deposit_missing_params(self, cash_tool):
        result = await cash_tool.execute(action="deposit", wallet_id="", amount=0)
        assert result["success"] is False
        assert "wallet_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_transfer_invalid_amount(self, cash_tool):
        result = await cash_tool.execute(
            action="transfer",
            wallet_id="wallet-123",
            amount=0,
            recipient="recipient-abc",
            token="SOL",
        )
        assert result["success"] is False
        assert "amount must be" in result["error"].lower()

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
    async def test_deposit_success(self, cash_tool):
        respx.post("https://cash.solana-agent.com/deposit").mock(
            return_value=Response(200, json={"status": "ok", "deposit": "done"})
        )
        result = await cash_tool.execute(
            action="deposit",
            wallet_id="wallet-123",
            amount=2.0,
            token="USDC",
        )
        assert result["success"] is True
        assert result["data"]["deposit"] == "done"

    @pytest.mark.asyncio
    @respx.mock
    async def test_withdraw_success(self, cash_tool):
        respx.post("https://cash.solana-agent.com/withdraw").mock(
            return_value=Response(200, json={"status": "ok", "withdraw": "done"})
        )
        result = await cash_tool.execute(
            action="withdraw",
            wallet_id="wallet-123",
            amount=1.0,
            recipient="recipient-abc",
            token="SOL",
        )
        assert result["success"] is True
        assert result["data"]["withdraw"] == "done"

    @pytest.mark.asyncio
    @respx.mock
    async def test_balance_api_error(self, cash_tool):
        respx.post("https://cash.solana-agent.com/balance").mock(
            return_value=Response(500, text="fail")
        )
        result = await cash_tool.execute(
            action="balance",
            wallet_id="wallet-123",
            token="USDC",
        )
        assert result["success"] is False
        assert "api error" in result["error"].lower()

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
