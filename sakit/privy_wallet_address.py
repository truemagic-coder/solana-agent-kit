from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx


async def get_privy_embedded_wallet_address(
    user_id: str, app_id: str, app_secret: str
) -> Optional[str]:
    url = f"https://auth.privy.io/api/v1/users/{user_id}"
    headers = {"privy-app-id": app_id}
    auth = (app_id, app_secret)
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, auth=auth, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for acct in data.get("linked_accounts", []):
            if acct.get("connector_type") == "embedded" and acct.get("delegated"):
                return acct["public_key"]
    return None


class PrivyWalletAddressCheckerTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_wallet_address",
            description="Get the wallet address of a Privy delegated embedded wallet.",
            registry=registry,
        )
        self.api_key = None
        self.app_id = None
        self.app_secret = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Privy user id (did) to check delegated embedded wallet balance.",
                }
            },
            "required": ["user_id"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        tool_cfg = config.get("tools", {}).get("privy_balance", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")

    async def execute(self, user_id: str) -> Dict[str, Any]:
        if not all([self.app_id, self.app_secret]):
            return {"status": "error", "message": "Privy config missing."}
        wallet_address = await get_privy_embedded_wallet_address(
            user_id, self.app_id, self.app_secret
        )
        if not wallet_address:
            return {
                "status": "error",
                "message": "No delegated embedded wallet found for user.",
            }
        return {
            "status": "success",
            "result": wallet_address,
        }


class PrivyWalletAddressCheckerPlugin:
    def __init__(self):
        self.name = "privy_wallet_address"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for checking the wallet address of a Privy delegated embedded wallet."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = PrivyWalletAddressCheckerTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return PrivyWalletAddressCheckerPlugin()
