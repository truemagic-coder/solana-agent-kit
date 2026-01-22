import asyncio
import logging
from typing import Dict, Any, List, Optional

import httpx
from solana_agent import AutoTool, ToolRegistry

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.starpay.cards"
FINAL_STATUSES = {"completed", "failed", "expired"}
SENSITIVE_KEYS = {
    "cardnumber",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "pin",
    "expiry",
    "exp",
    "expmonth",
    "expyear",
    "expiration",
    "expirationmonth",
    "expirationyear",
}


def _normalize_key(key: str) -> str:
    return "".join(ch.lower() for ch in key if ch.isalnum() or ch == "_")


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for k, v in value.items():
            key_norm = _normalize_key(k)
            if key_norm in SENSITIVE_KEYS:
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = _redact_sensitive(v)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


class StarpayCardsTool(AutoTool):
    """Issue SOL-funded Starpay Cards and check status."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="starpay_cards",
            description=(
                "Create Starpay Cards orders, check status, and calculate pricing. "
                "Actions: 'create_order', 'check_status', 'price', 'poll_status'."
            ),
            registry=registry,
        )
        self._api_key: Optional[str] = None
        self._base_url: str = DEFAULT_BASE_URL

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_order", "check_status", "price", "poll_status"],
                    "description": "Action to perform.",
                },
                "amount": {
                    "type": "number",
                    "description": "Card value in USD (5-10000).",
                    "default": 0,
                },
                "card_type": {
                    "type": "string",
                    "enum": ["visa", "mastercard", ""],
                    "description": "Card type for order creation.",
                    "default": "",
                },
                "email": {
                    "type": "string",
                    "description": "Customer email for order creation.",
                    "default": "",
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID for status checks.",
                    "default": "",
                },
                "poll_interval_seconds": {
                    "type": "number",
                    "description": "Polling interval in seconds (10-30 recommended).",
                    "default": 10,
                },
                "poll_timeout_seconds": {
                    "type": "number",
                    "description": "Polling timeout in seconds.",
                    "default": 600,
                },
            },
            "required": [
                "action",
                "amount",
                "card_type",
                "email",
                "order_id",
                "poll_interval_seconds",
                "poll_timeout_seconds",
            ],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("starpay_cards", {})
        self._api_key = tool_cfg.get("api_key")
        self._base_url = tool_cfg.get("base_url", DEFAULT_BASE_URL)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.request(
                method, url, params=params, json=json_body, headers=headers
            )

    async def _create_order(
        self, amount: float, card_type: str, email: str
    ) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/v1/cards/order",
            json_body={"amount": amount, "cardType": card_type, "email": email},
        )
        if response.status_code != 200:
            logger.error(
                "Starpay Cards API error: %s %s", response.status_code, response.text
            )
            return {
                "status": "error",
                "message": f"Starpay Cards API error: {response.status_code}",
                "details": response.text,
            }
        return {"status": "success", "result": _redact_sensitive(response.json())}

    async def _check_status(self, order_id: str) -> Dict[str, Any]:
        response = await self._request(
            "GET",
            "/api/v1/cards/order/status",
            params={"orderId": order_id},
        )
        if response.status_code != 200:
            logger.error(
                "Starpay Cards API error: %s %s", response.status_code, response.text
            )
            return {
                "status": "error",
                "message": f"Starpay Cards API error: {response.status_code}",
                "details": response.text,
            }
        return {"status": "success", "result": _redact_sensitive(response.json())}

    async def _price(self, amount: float) -> Dict[str, Any]:
        response = await self._request(
            "GET",
            "/api/v1/cards/price",
            params={"amount": amount},
        )
        if response.status_code != 200:
            logger.error(
                "Starpay Cards API error: %s %s", response.status_code, response.text
            )
            return {
                "status": "error",
                "message": f"Starpay Cards API error: {response.status_code}",
                "details": response.text,
            }
        return {"status": "success", "result": _redact_sensitive(response.json())}

    async def _poll_status(
        self,
        order_id: str,
        poll_interval_seconds: float,
        poll_timeout_seconds: float,
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        start = loop.time()
        while True:
            result = await self._check_status(order_id)
            if result.get("status") == "error":
                return result
            status = result.get("result", {}).get("status")
            if status in FINAL_STATUSES:
                return {
                    "status": "success",
                    "result": result.get("result"),
                }
            if loop.time() - start >= poll_timeout_seconds:
                return {
                    "status": "error",
                    "message": "Polling timed out before completion.",
                }
            await asyncio.sleep(max(0.01, poll_interval_seconds))

    async def execute(
        self,
        action: str,
        amount: float,
        card_type: str,
        email: str,
        order_id: str,
        poll_interval_seconds: float = 10,
        poll_timeout_seconds: float = 600,
    ) -> Dict[str, Any]:
        if not self._api_key:
            return {"status": "error", "message": "API key not configured."}

        if action == "create_order":
            if not all([amount, card_type, email]):
                return {
                    "status": "error",
                    "message": "amount, card_type, and email are required for create_order.",
                }
            return await self._create_order(amount, card_type, email)

        if action == "check_status":
            if not order_id:
                return {"status": "error", "message": "order_id is required."}
            return await self._check_status(order_id)

        if action == "price":
            if not amount:
                return {"status": "error", "message": "amount is required."}
            return await self._price(amount)

        if action == "poll_status":
            if not order_id:
                return {"status": "error", "message": "order_id is required."}
            return await self._poll_status(
                order_id, poll_interval_seconds, poll_timeout_seconds
            )

        return {"status": "error", "message": "Invalid action."}


class StarpayCardsPlugin:
    def __init__(self):
        self.name = "starpay_cards"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for issuing Starpay Cards and checking status."

    def initialize(self, tool_registry: ToolRegistry) -> None:  # pragma: no cover
        self.tool_registry = tool_registry
        self._tool = StarpayCardsTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:  # pragma: no cover
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:  # pragma: no cover
        return [self._tool] if self._tool else []


def get_plugin():  # pragma: no cover
    return StarpayCardsPlugin()
