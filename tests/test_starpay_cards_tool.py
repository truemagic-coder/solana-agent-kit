"""
Tests for Star Cards Tool.
"""

import httpx
import pytest
import respx

from sakit.starpay_cards import StarpayCardsTool


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
