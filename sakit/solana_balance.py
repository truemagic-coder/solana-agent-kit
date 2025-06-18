import logging
from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx


def summarize_alphavybe_balances(api_response: Dict[str, Any]) -> str:
    lines = []
    sol = api_response.get("solBalance")
    sol_usd = api_response.get("solBalanceUsd")
    staked_sol = api_response.get("stakedSolBalance")
    staked_sol_usd = api_response.get("stakedSolBalanceUsd")
    active_staked_sol = api_response.get("activeStakedSolBalance")
    active_staked_sol_usd = api_response.get("activeStakedSolBalanceUsd")
    total_usd = api_response.get("totalTokenValueUsd")
    total_usd_change = api_response.get("totalTokenValueUsd1dChange")
    owner = api_response.get("ownerAddress")

    lines.append(f"Wallet: {owner}")
    if sol is not None:
        lines.append(f"SOL balance: {sol} (~${sol_usd})")
    if staked_sol is not None:
        lines.append(f"Staked SOL: {staked_sol} (~${staked_sol_usd})")
    if active_staked_sol is not None:
        lines.append(
            f"Active Staked SOL: {active_staked_sol} (~${active_staked_sol_usd})"
        )
    if total_usd is not None:
        lines.append(
            f"Total wallet value: ${total_usd} (24h change: {total_usd_change})"
        )

    tokens = api_response.get("data", [])
    if tokens:
        lines.append("Top tokens:")
        for token in tokens[:10]:
            name = token.get("name") or token.get("symbol") or token.get("mintAddress")
            amount = token.get("amount")
            symbol = token.get("symbol") or ""
            value_usd = token.get("valueUsd")
            verified = "✅" if token.get("verified") else "❌"
            lines.append(f"  - {name} ({symbol}): {amount} (${value_usd}) {verified}")
    else:
        lines.append("No SPL tokens found.")
    return "\n".join(lines)


class AlphaVybeBalanceCheckerTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="solana_balance",
            description="Check SOL and SPL token balances for a wallet using AlphaVybe API.",
            registry=registry,
        )
        self.api_key = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet_address": {
                    "type": "string",
                    "description": "The wallet public key (base58 address) to check.",
                }
            },
            "required": ["wallet_address"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("solana_balance", {})
        self.api_key = tool_cfg.get("api_key")

    async def execute(self, wallet_address: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "error", "message": "AlphaVybe API key not configured."}
        url = f"https://api.vybenetwork.xyz/account/token-balance/{wallet_address}?limit=10&sortByDesc=valueUsd"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers, timeout=15)
                    if resp.status_code >= 500:
                        raise httpx.HTTPStatusError("Server error", request=resp.request, response=resp)
                    resp.raise_for_status()
                    data = resp.json()
                    summary = summarize_alphavybe_balances(data)
                    return {
                        "status": "success",
                        "result": summary,
                    }
            except httpx.HTTPStatusError as e:
                if resp.status_code >= 500 and attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(1)
                    continue
                logging.exception(f"AlphaVybe balance check error: {e}")
                return {"status": "error", "message": str(e)}
            except Exception as e:
                logging.exception(f"AlphaVybe balance check error: {e}")
                return {"status": "error", "message": str(e)}

class AlphaVybeBalanceCheckerPlugin:
    def __init__(self):
        self.name = "solana_balance"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for checking SOL and SPL token balances for a wallet using AlphaVybe API."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = AlphaVybeBalanceCheckerTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return AlphaVybeBalanceCheckerPlugin()
