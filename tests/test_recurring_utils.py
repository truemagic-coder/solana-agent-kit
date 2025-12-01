"""
Tests for Jupiter Recurring utility module.

Tests the JupiterRecurring API client which handles creating, canceling,
and managing DCA orders via Jupiter's Recurring API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sakit.utils.recurring import (
    JupiterRecurring,
    RecurringOrderResponse,
    RecurringExecuteResponse,
    RecurringCancelResponse,
)


@pytest.fixture
def recurring_lite():
    """Create a JupiterRecurring client using lite API (no key)."""
    return JupiterRecurring(api_key=None)


@pytest.fixture
def recurring_pro():
    """Create a JupiterRecurring client using pro API (with key)."""
    return JupiterRecurring(api_key="test-api-key")


class TestJupiterRecurringInit:
    """Test JupiterRecurring initialization."""

    def test_lite_api_url(self, recurring_lite):
        """Should use lite API when no API key provided."""
        assert "lite-api.jup.ag" in recurring_lite.base_url

    def test_pro_api_url(self, recurring_pro):
        """Should use pro API when API key provided."""
        assert recurring_pro.base_url.startswith("https://api.jup.ag")
        assert "lite" not in recurring_pro.base_url

    def test_pro_api_key_stored(self, recurring_pro):
        """Should store API key for pro API."""
        assert recurring_pro.api_key == "test-api-key"

    def test_lite_no_api_key(self, recurring_lite):
        """Should have no API key for lite API."""
        assert recurring_lite.api_key is None


class TestRecurringCreateOrder:
    """Test create_order method."""

    @pytest.mark.asyncio
    async def test_create_time_order_success(self, recurring_lite):
        """Should return RecurringOrderResponse on successful order creation."""
        mock_response = {
            "order": "dcaorder123",
            "transaction": "base64encodedtx==",
            "requestId": "req123",
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                user="WalletPubkey123",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",  # hourly
            )

            assert isinstance(result, RecurringOrderResponse)
            assert result.success is True
            assert result.order == "dcaorder123"
            assert result.transaction == "base64encodedtx=="
            assert result.request_id == "req123"

    @pytest.mark.asyncio
    async def test_create_order_with_payer(self, recurring_lite):
        """Should include payer parameter for gasless transactions."""
        mock_response = {
            "order": "dcaorder123",
            "transaction": "base64encodedtx==",
            "requestId": "req123",
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_response_obj = MagicMock(status_code=200, json=lambda: mock_response)
            mock_instance.post = AsyncMock(return_value=mock_response_obj)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            await recurring_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                user="WalletPubkey123",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
                payer="PayerPubkey123",
            )

            call_args = mock_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload.get("payer") == "PayerPubkey123"

    @pytest.mark.asyncio
    async def test_create_order_with_min_max_amounts(self, recurring_lite):
        """Should include minOutAmount and maxOutAmount when provided."""
        mock_response = {
            "order": "dcaorder123",
            "transaction": "base64encodedtx==",
            "requestId": "req123",
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_response_obj = MagicMock(status_code=200, json=lambda: mock_response)
            mock_instance.post = AsyncMock(return_value=mock_response_obj)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            await recurring_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                user="WalletPubkey123",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
                min_out_amount="90000",
                max_out_amount="110000",
            )

            call_args = mock_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            # min/max amounts are in nested params object
            assert payload.get("params", {}).get("minOutAmount") == "90000"
            assert payload.get("params", {}).get("maxOutAmount") == "110000"

    @pytest.mark.asyncio
    async def test_create_order_api_error(self, recurring_lite):
        """Should return error response when API returns non-200."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=400, text="Bad Request")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.create_order(
                input_mint="invalid",
                output_mint="invalid",
                user="invalid",
                in_amount="0",
                order_count=0,
                frequency="0",
            )

            assert isinstance(result, RecurringOrderResponse)
            assert result.success is False
            assert result.error is not None


class TestRecurringExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, recurring_lite):
        """Should return RecurringExecuteResponse on successful execution."""
        mock_response = {
            "signature": "txsig123",
            "status": "Success",  # Note: API returns "Success" not lowercase
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.execute(
                signed_transaction="base64signedtx==",
                request_id="req123",
            )

            assert isinstance(result, RecurringExecuteResponse)
            assert result.success is True
            assert result.signature == "txsig123"

    @pytest.mark.asyncio
    async def test_execute_failure(self, recurring_lite):
        """Should handle execution failure."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=500, text="Internal Server Error")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.execute(
                signed_transaction="base64signedtx==",
                request_id="req123",
            )

            assert isinstance(result, RecurringExecuteResponse)
            assert result.success is False


class TestRecurringCancelOrder:
    """Test cancel_order method."""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, recurring_lite):
        """Should return RecurringCancelResponse on successful cancellation."""
        mock_response = {
            "transaction": "base64canceltx==",
            "requestId": "cancelreq123",
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.cancel_order(
                user="WalletPubkey123",
                order="dcaorder123",
            )

            assert isinstance(result, RecurringCancelResponse)
            assert result.success is True
            assert result.transaction == "base64canceltx=="


class TestRecurringGetOrders:
    """Test get_orders method."""

    @pytest.mark.asyncio
    async def test_get_orders_active(self, recurring_lite):
        """Should return active DCA orders for a user."""
        mock_response = {
            "orders": [
                {
                    "orderPubkey": "dcaorder1",
                    "inputMint": "So11...",
                    "outputMint": "EPjF...",
                    "depositAmount": "1000000000",
                    "orderCount": 10,
                    "executedCount": 3,
                    "frequency": "3600",
                    "status": "active",
                }
            ]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.get_orders(
                user="WalletPubkey123",
                order_status="active",
            )

            assert result.get("success") is True
            assert len(result.get("orders", [])) == 1
            order = result["orders"][0]
            assert order.get("orderPubkey") == "dcaorder1"
            assert order.get("orderCount") == 10
            assert order.get("executedCount") == 3

    @pytest.mark.asyncio
    async def test_get_orders_api_error(self, recurring_lite):
        """Should handle API errors gracefully."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=MagicMock(status_code=500, text="Internal Server Error")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await recurring_lite.get_orders(
                user="WalletPubkey123",
                order_status="active",
            )

            assert result.get("success") is False
            assert "error" in result
