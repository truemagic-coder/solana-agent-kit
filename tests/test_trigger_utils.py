"""
Tests for Jupiter Trigger utility module.

Tests the JupiterTrigger API client which handles creating, canceling,
and managing limit orders via Jupiter's Trigger API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sakit.utils.trigger import (
    JupiterTrigger,
    TriggerOrderResponse,
    TriggerExecuteResponse,
    TriggerCancelResponse,
)


@pytest.fixture
def trigger_lite():
    """Create a JupiterTrigger client using lite API (no key)."""
    return JupiterTrigger(api_key=None)


@pytest.fixture
def trigger_pro():
    """Create a JupiterTrigger client using pro API (with key)."""
    return JupiterTrigger(api_key="test-api-key")


class TestJupiterTriggerInit:
    """Test JupiterTrigger initialization."""

    def test_lite_api_url(self, trigger_lite):
        """Should use lite API when no API key provided."""
        assert "lite-api.jup.ag" in trigger_lite.base_url

    def test_pro_api_url(self, trigger_pro):
        """Should use pro API when API key provided."""
        assert trigger_pro.base_url.startswith("https://api.jup.ag")
        assert "lite" not in trigger_pro.base_url

    def test_pro_api_key_stored(self, trigger_pro):
        """Should store API key for pro API."""
        assert trigger_pro.api_key == "test-api-key"

    def test_lite_no_api_key(self, trigger_lite):
        """Should have no API key for lite API."""
        assert trigger_lite.api_key is None


class TestTriggerCreateOrder:
    """Test create_order method."""

    @pytest.mark.asyncio
    async def test_create_order_success(self, trigger_lite):
        """Should return TriggerOrderResponse on successful order creation."""
        mock_response = {
            "order": "order123",
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

            result = await trigger_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                maker="WalletPubkey123",
                making_amount="1000000",
                taking_amount="100000",
            )

            assert isinstance(result, TriggerOrderResponse)
            assert result.success is True
            assert result.order == "order123"
            assert result.transaction == "base64encodedtx=="
            assert result.request_id == "req123"

    @pytest.mark.asyncio
    async def test_create_order_with_expiry(self, trigger_lite):
        """Should include expiredAt parameter when provided."""
        mock_response = {
            "order": "order123",
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

            await trigger_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                maker="WalletPubkey123",
                making_amount="1000000",
                taking_amount="100000",
                expired_at="1700000000",
            )

            # Verify the call was made with expiredAt in params
            call_args = mock_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload.get("params", {}).get("expiredAt") == "1700000000"

    @pytest.mark.asyncio
    async def test_create_order_with_payer(self, trigger_lite):
        """Should include payer parameter for gasless transactions."""
        mock_response = {
            "order": "order123",
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

            await trigger_lite.create_order(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                maker="WalletPubkey123",
                making_amount="1000000",
                taking_amount="100000",
                payer="PayerPubkey123",
            )

            call_args = mock_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload.get("payer") == "PayerPubkey123"

    @pytest.mark.asyncio
    async def test_create_order_api_error(self, trigger_lite):
        """Should return error response when API returns non-200."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=400, text="Bad Request")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await trigger_lite.create_order(
                input_mint="invalid",
                output_mint="invalid",
                maker="invalid",
                making_amount="0",
                taking_amount="0",
            )

            assert isinstance(result, TriggerOrderResponse)
            assert result.success is False
            assert result.error is not None


class TestTriggerExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, trigger_lite):
        """Should return TriggerExecuteResponse on successful execution."""
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

            result = await trigger_lite.execute(
                signed_transaction="base64signedtx==",
                request_id="req123",
            )

            assert isinstance(result, TriggerExecuteResponse)
            assert result.success is True
            assert result.signature == "txsig123"

    @pytest.mark.asyncio
    async def test_execute_failure(self, trigger_lite):
        """Should handle execution failure."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=500, text="Internal Server Error")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await trigger_lite.execute(
                signed_transaction="base64signedtx==",
                request_id="req123",
            )

            assert isinstance(result, TriggerExecuteResponse)
            assert result.success is False


class TestTriggerCancelOrder:
    """Test cancel_order method."""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, trigger_lite):
        """Should return TriggerCancelResponse on successful cancellation."""
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

            result = await trigger_lite.cancel_order(
                maker="WalletPubkey123",
                order="order123",
            )

            assert isinstance(result, TriggerCancelResponse)
            assert result.success is True
            assert result.transaction == "base64canceltx=="


class TestTriggerCancelOrders:
    """Test cancel_orders (batch) method."""

    @pytest.mark.asyncio
    async def test_cancel_orders_success(self, trigger_lite):
        """Should cancel multiple orders in batch."""
        mock_response = {
            "transactions": ["base64batchcanceltx1==", "base64batchcanceltx2=="],
            "requestId": "batchreq123",
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await trigger_lite.cancel_orders(
                maker="WalletPubkey123",
                orders=["order1", "order2", "order3"],
            )

            # cancel_orders returns TriggerCancelMultipleResponse
            assert result.success is True
            assert len(result.transactions) == 2


class TestTriggerGetOrders:
    """Test get_orders method."""

    @pytest.mark.asyncio
    async def test_get_orders_active(self, trigger_lite):
        """Should return active orders for a maker."""
        mock_response = {
            "orders": [
                {
                    "orderPubkey": "order1",
                    "inputMint": "So11...",
                    "outputMint": "EPjF...",
                    "makingAmount": "1000000",
                    "takingAmount": "100000",
                    "status": "active",
                }
            ],
            "total": 1,
            "page": 1,
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await trigger_lite.get_orders(
                user="WalletPubkey123",
                order_status="active",
            )

            assert result.get("success") is True
            assert len(result.get("orders", [])) == 1

    @pytest.mark.asyncio
    async def test_get_orders_history(self, trigger_lite):
        """Should return order history."""
        mock_response = {
            "orders": [
                {"orderPubkey": "order1", "status": "filled"},
                {"orderPubkey": "order2", "status": "cancelled"},
            ],
            "total": 2,
            "page": 1,
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: mock_response)
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_instance

            result = await trigger_lite.get_orders(
                user="WalletPubkey123",
                order_status="history",
            )

            assert result.get("success") is True
            assert len(result.get("orders", [])) == 2
