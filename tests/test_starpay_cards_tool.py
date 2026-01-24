"""
Tests for Star Cards Tool.
"""

import httpx
import pytest
import respx
from unittest.mock import MagicMock

from sakit.starpay_cards import (
    StarpayCardsPlugin,
    StarpayCardsTool,
    _normalize_key,
    _redact_sensitive,
)


@pytest.fixture
def star_cards_tool():
    tool = StarpayCardsTool()
    tool.configure({"tools": {"starpay_cards": {"api_key": "test-key"}}})
    return tool


class TestStarCardsToolSchema:
    def test_tool_name(self, star_cards_tool):
        assert star_cards_tool.name == "starpay_cards"

    def test_schema_has_action(self, star_cards_tool):
        schema = star_cards_tool.get_schema()
        assert "action" in schema["properties"]
        assert "action" in schema["required"]


class TestStarCardsToolHelpers:
    def test_normalize_key(self):
        assert _normalize_key("Card-Number") == "cardnumber"
        assert _normalize_key("Exp Month") == "expmonth"
        assert _normalize_key("cvv") == "cvv"

    def test_redact_sensitive_nested(self):
        payload = {
            "cardNumber": "4111111111111111",
            "cvv": "123",
            "payment": {"pan": "4000000000000002", "amount": 10},
            "cards": [
                {"cvc": "999", "expiry": "12/29"},
                {"card_number": "5555555555554444"},
            ],
        }
        redacted = _redact_sensitive(payload)
        assert redacted["cardNumber"] == "[REDACTED]"
        assert redacted["cvv"] == "[REDACTED]"
        assert redacted["payment"]["pan"] == "[REDACTED]"
        assert redacted["payment"]["amount"] == 10
        assert redacted["cards"][0]["cvc"] == "[REDACTED]"
        assert redacted["cards"][0]["expiry"] == "[REDACTED]"
        assert redacted["cards"][1]["card_number"] == "[REDACTED]"


class TestStarCardsToolExecute:
    @pytest.mark.asyncio
    async def test_create_order_success(self, star_cards_tool):
        with respx.mock:
            respx.post("https://www.starpay.cards/api/v1/cards/order").respond(
                200,
                json={
                    "orderId": "abc123",
                    "status": "pending",
                    "payment": {"address": "SOL_ADDR", "amountSol": 0.2},
                    "cardNumber": "4111111111111111",
                    "cvv": "123",
                },
            )
            result = await star_cards_tool.execute(
                action="create_order",
                amount=50,
                card_type="visa",
                email="customer@example.com",
                order_id="",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "success"
            assert result["result"]["orderId"] == "abc123"
            assert result["result"]["cardNumber"] == "[REDACTED]"
            assert result["result"]["cvv"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_price_success(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/price").respond(
                200, json={"pricing": {"customerPrice": 53.75}}
            )
            result = await star_cards_tool.execute(
                action="price",
                amount=50,
                card_type="",
                email="",
                order_id="",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "success"
            assert result["result"]["pricing"]["customerPrice"] == 53.75

    @pytest.mark.asyncio
    async def test_check_status_success(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/order/status").respond(
                200, json={"status": "pending"}
            )
            result = await star_cards_tool.execute(
                action="check_status",
                amount=0,
                card_type="",
                email="",
                order_id="abc123",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "success"
            assert result["result"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_poll_status_completes(self, star_cards_tool):
        with respx.mock:
            route = respx.get("https://www.starpay.cards/api/v1/cards/order/status")
            route.mock(
                side_effect=[
                    httpx.Response(200, json={"status": "pending"}),
                    httpx.Response(200, json={"status": "completed"}),
                ]
            )
            result = await star_cards_tool.execute(
                action="poll_status",
                amount=0,
                card_type="",
                email="",
                order_id="abc123",
                poll_interval_seconds=0.01,
                poll_timeout_seconds=1,
            )
            assert result["status"] == "success"
            assert result["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        tool = StarpayCardsTool()
        tool.configure({"tools": {"starpay_cards": {}}})
        result = await tool.execute(
            action="price",
            amount=50,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "API key" in result["message"]

    @pytest.mark.asyncio
    async def test_create_order_missing_fields(self, star_cards_tool):
        result = await star_cards_tool.execute(
            action="create_order",
            amount=0,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "create_order" in result["message"]

    @pytest.mark.asyncio
    async def test_check_status_missing_order_id(self, star_cards_tool):
        result = await star_cards_tool.execute(
            action="check_status",
            amount=0,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "order_id" in result["message"]

    @pytest.mark.asyncio
    async def test_price_missing_amount(self, star_cards_tool):
        result = await star_cards_tool.execute(
            action="price",
            amount=0,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "amount" in result["message"]

    @pytest.mark.asyncio
    async def test_poll_status_missing_order_id(self, star_cards_tool):
        result = await star_cards_tool.execute(
            action="poll_status",
            amount=0,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "order_id" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_action(self, star_cards_tool):
        result = await star_cards_tool.execute(
            action="nope",
            amount=0,
            card_type="",
            email="",
            order_id="",
            poll_interval_seconds=10,
            poll_timeout_seconds=600,
        )
        assert result["status"] == "error"
        assert "Invalid action" in result["message"]

    @pytest.mark.asyncio
    async def test_create_order_api_error(self, star_cards_tool):
        with respx.mock:
            respx.post("https://www.starpay.cards/api/v1/cards/order").respond(
                500, text="Server error"
            )
            result = await star_cards_tool.execute(
                action="create_order",
                amount=50,
                card_type="visa",
                email="customer@example.com",
                order_id="",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "error"
            assert result["message"].startswith("Starpay Cards API error")

    @pytest.mark.asyncio
    async def test_check_status_api_error(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/order/status").respond(
                500, text="Server error"
            )
            result = await star_cards_tool.execute(
                action="check_status",
                amount=0,
                card_type="",
                email="",
                order_id="abc123",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "error"
            assert result["message"].startswith("Starpay Cards API error")

    @pytest.mark.asyncio
    async def test_price_api_error(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/price").respond(
                500, text="Server error"
            )
            result = await star_cards_tool.execute(
                action="price",
                amount=50,
                card_type="",
                email="",
                order_id="",
                poll_interval_seconds=10,
                poll_timeout_seconds=600,
            )
            assert result["status"] == "error"
            assert result["message"].startswith("Starpay Cards API error")

    @pytest.mark.asyncio
    async def test_poll_status_timeout(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/order/status").respond(
                200, json={"status": "pending"}
            )
            result = await star_cards_tool.execute(
                action="poll_status",
                amount=0,
                card_type="",
                email="",
                order_id="abc123",
                poll_interval_seconds=0.01,
                poll_timeout_seconds=0,
            )
            assert result["status"] == "error"
            assert "timed out" in result["message"]

    @pytest.mark.asyncio
    async def test_poll_status_api_error(self, star_cards_tool):
        with respx.mock:
            respx.get("https://www.starpay.cards/api/v1/cards/order/status").respond(
                500, text="Server error"
            )
            result = await star_cards_tool.execute(
                action="poll_status",
                amount=0,
                card_type="",
                email="",
                order_id="abc123",
                poll_interval_seconds=0.01,
                poll_timeout_seconds=1,
            )
            assert result["status"] == "error"
            assert result["message"].startswith("Starpay Cards API error")


class TestStarCardsPlugin:
    def test_plugin_name(self):
        plugin = StarpayCardsPlugin()
        assert plugin.name == "starpay_cards"

    def test_plugin_description(self):
        plugin = StarpayCardsPlugin()
        assert "starpay" in plugin.description.lower()

    def test_plugin_get_tools_empty_before_init(self):
        plugin = StarpayCardsPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize_and_configure(self):
        plugin = StarpayCardsPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)
        plugin.configure({"tools": {"starpay_cards": {"api_key": "test-key"}}})

        assert plugin._tool is not None
        tools = plugin.get_tools()
        assert len(tools) == 1
