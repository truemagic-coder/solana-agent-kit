"""
Jupiter Recurring API utility functions.

Provides a simplified interface to Jupiter's Recurring API for creating,
canceling, and managing DCA (Dollar Cost Averaging) orders.
"""

import logging
import base64
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import httpx

from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import to_bytes_versioned  # type: ignore

logger = logging.getLogger(__name__)

# Use lite API for no-key access, main API for keyed access with dynamic rate limits
JUPITER_RECURRING_API_LITE = "https://lite-api.jup.ag/recurring/v1"
JUPITER_RECURRING_API_PRO = "https://api.jup.ag/recurring/v1"


@dataclass
class RecurringOrderResponse:
    """Response from Jupiter Recurring /createOrder endpoint."""

    success: bool
    order: Optional[str] = None  # Order account public key
    transaction: Optional[str] = None  # Base64 encoded transaction
    request_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecurringExecuteResponse:
    """Response from Jupiter Recurring /execute endpoint."""

    success: bool
    status: Optional[str] = None
    signature: Optional[str] = None
    error: Optional[str] = None
    code: Optional[int] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecurringCancelResponse:
    """Response from Jupiter Recurring /cancelOrder endpoint."""

    success: bool
    transaction: Optional[str] = None  # Base64 encoded transaction
    request_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


class JupiterRecurring:
    """Jupiter Recurring API client for DCA orders."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Jupiter Recurring client.

        Args:
            api_key: Optional Jupiter API key for dynamic rate limits
            base_url: Optional custom base URL (auto-selects based on api_key if not provided)
        """
        if base_url:
            self.base_url = base_url
        elif api_key:
            self.base_url = JUPITER_RECURRING_API_PRO
        else:
            self.base_url = JUPITER_RECURRING_API_LITE

        self.api_key = api_key
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["x-api-key"] = api_key

    async def create_order(
        self,
        input_mint: str,
        output_mint: str,
        user: str,
        in_amount: str,
        order_count: int,
        frequency: str,
        payer: Optional[str] = None,
        min_out_amount: Optional[str] = None,
        max_out_amount: Optional[str] = None,
        start_at: Optional[str] = None,
    ) -> RecurringOrderResponse:
        """
        Create a new time-based recurring (DCA) order.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            user: User wallet address
            in_amount: Total amount of input token to deposit (in base units as string)
            order_count: Total number of orders to execute
            frequency: Time between each order in seconds (as string, e.g., "3600" for hourly)
            payer: Optional payer wallet address for gasless (defaults to user)
            min_out_amount: Optional minimum output amount per order
            max_out_amount: Optional maximum output amount per order
            start_at: Optional start time in unix seconds (as string)

        Returns:
            RecurringOrderResponse with transaction to sign
        """
        body = {
            "user": user,
            "payer": payer or user,
            "inputMint": input_mint,
            "outputMint": output_mint,
            "params": {
                "depositAmount": in_amount,
                "orderCount": order_count,
                "frequency": frequency,
            },
        }

        if min_out_amount:
            body["params"]["minOutAmount"] = min_out_amount
        if max_out_amount:
            body["params"]["maxOutAmount"] = max_out_amount
        if start_at:
            body["params"]["startAt"] = start_at

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/createOrder",
                    json=body,
                    headers=self._headers,
                )

                if response.status_code != 200:
                    return RecurringOrderResponse(
                        success=False,
                        error=f"Failed to create recurring order: {response.status_code} - {response.text}",
                    )

                data = response.json()

                return RecurringOrderResponse(
                    success=True,
                    order=data.get("order", ""),
                    transaction=data.get("transaction", ""),
                    request_id=data.get("requestId", ""),
                    raw_response=data,
                )
        except Exception as e:
            logger.exception("Failed to create recurring order")
            return RecurringOrderResponse(success=False, error=str(e))

    async def cancel_order(
        self,
        user: str,
        order: str,
        payer: Optional[str] = None,
    ) -> RecurringCancelResponse:
        """
        Cancel a recurring order.

        Args:
            user: User wallet address
            order: Order account public key to cancel
            payer: Optional payer wallet address for gasless

        Returns:
            RecurringCancelResponse with transaction to sign
        """
        body = {
            "user": user,
            "order": order,
        }
        if payer:
            body["payer"] = payer

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/cancelOrder",
                    json=body,
                    headers=self._headers,
                )

                if response.status_code != 200:
                    return RecurringCancelResponse(
                        success=False,
                        error=f"Failed to cancel recurring order: {response.status_code} - {response.text}",
                    )

                data = response.json()

                return RecurringCancelResponse(
                    success=True,
                    transaction=data.get("transaction", ""),
                    request_id=data.get("requestId", ""),
                    raw_response=data,
                )
        except Exception as e:
            logger.exception("Failed to cancel recurring order")
            return RecurringCancelResponse(success=False, error=str(e))

    async def execute(
        self,
        signed_transaction: str,
        request_id: str,
    ) -> RecurringExecuteResponse:
        """
        Execute a signed recurring order transaction.

        Args:
            signed_transaction: Base64 encoded signed transaction
            request_id: Request ID from create/cancel response

        Returns:
            RecurringExecuteResponse with execution result
        """
        payload = {
            "signedTransaction": signed_transaction,
            "requestId": request_id,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/execute",
                    json=payload,
                    headers=self._headers,
                )

                if response.status_code != 200:
                    return RecurringExecuteResponse(
                        success=False,
                        error=f"Failed to execute recurring order: {response.status_code} - {response.text}",
                    )

                data = response.json()
                status = data.get("status", "")

                return RecurringExecuteResponse(
                    success=status.lower() == "success",
                    status=status,
                    signature=data.get("signature"),
                    error=data.get("error"),
                    code=data.get("code", 0),
                    raw_response=data,
                )
        except Exception as e:
            logger.exception("Failed to execute recurring order")
            return RecurringExecuteResponse(success=False, error=str(e))

    async def get_orders(
        self,
        user: str,
        order_status: str = "active",
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Get recurring orders for a user.

        Args:
            user: User wallet address
            order_status: "active" or "history"
            page: Page number for pagination

        Returns:
            Orders data with pagination info
        """
        params = {
            "user": user,
            "orderStatus": order_status,
            "page": str(page),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/getRecurringOrders",
                    params=params,
                    headers=self._headers,
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to get recurring orders: {response.status_code} - {response.text}",
                        "orders": [],
                    }

                data = response.json()
                return {
                    "success": True,
                    "orders": data.get("orders", []),
                    "total": data.get("total", 0),
                    "page": data.get("page", 1),
                }
        except Exception as e:
            logger.exception("Failed to get recurring orders")
            return {"success": False, "error": str(e), "orders": []}


def sign_recurring_transaction(
    transaction_base64: str,
    sign_message_func,
    payer_sign_func=None,
) -> str:
    """
    Sign a Jupiter Recurring transaction.

    Args:
        transaction_base64: Base64 encoded transaction
        sign_message_func: Function that signs a message and returns signature (user)
        payer_sign_func: Optional function for payer signature (for gasless)

    Returns:
        Base64 encoded signed transaction
    """
    transaction_bytes = base64.b64decode(transaction_base64)
    transaction = VersionedTransaction.from_bytes(transaction_bytes)

    message_bytes = to_bytes_versioned(transaction.message)

    if payer_sign_func:
        # Gasless: payer signs first, then user
        payer_signature = payer_sign_func(message_bytes)
        user_signature = sign_message_func(message_bytes)
        signed_transaction = VersionedTransaction.populate(
            transaction.message, [payer_signature, user_signature]
        )
    else:
        # Normal: only user signs
        signature = sign_message_func(message_bytes)
        signed_transaction = VersionedTransaction.populate(
            transaction.message, [signature]
        )

    return base64.b64encode(bytes(signed_transaction)).decode("utf-8")
