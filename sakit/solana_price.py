import logging
from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx


def summarize_birdeye_price(api_response: Dict[str, Any], address: str) -> str:
    if not api_response.get("success"):
        return f"Failed to fetch price for {address}."
    data = api_response.get("data", {})
    value = data.get("value")
    price_change = data.get("priceChange24h")
    liquidity = data.get("liquidity")
    update_time = data.get("updateHumanTime")
    lines = [
        f"Token address: {address}",
        f"Current price: {value}",
        f"24h price change: {price_change}%",
        f"Liquidity: {liquidity}",
        f"Last updated: {update_time}",
    ]
    return "\n".join(lines)


class BirdeyePriceCheckerTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="solana_price",
            description="Get the current price and liquidity for a Solana token using Birdeye API.",
            registry=registry,
        )
        self.api_key = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The SPL token mint address to check price for.",
                }
            },
            "required": ["address"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("solana_price", {})
        self.api_key = tool_cfg.get("api_key")

    async def execute(self, address: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "error", "message": "Birdeye API key not configured."}
        url = f"https://public-api.birdeye.so/defi/price?include_liquidity=true&address={address}"
        headers = {
            "accept": "application/json",
            "x-chain": "solana",
            "X-API-KEY": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                summary = summarize_birdeye_price(data, address)
                return {
                    "status": "success",
                    "result": summary,
                }
        except Exception as e:
            logging.exception(f"Birdeye price check error: {e}")
            return {"status": "error", "message": str(e)}


class BirdeyePriceCheckerPlugin:
    def __init__(self):
        self.name = "solana_price"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for checking Solana token price and liquidity using Birdeye API."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = BirdeyePriceCheckerTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return BirdeyePriceCheckerPlugin()
