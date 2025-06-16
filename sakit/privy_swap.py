import base64
import json
import logging
from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sakit.utils.wallet import SolanaWalletClient
from sakit.utils.swap import TradeManager


def canonicalize(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def get_authorization_signature(url, body, privy_app_id, privy_auth_key):
    payload = {
        "version": 1,
        "method": "POST",
        "url": url,
        "body": body,
        "headers": {"privy-app-id": privy_app_id},
    }
    serialized_payload = canonicalize(payload)
    private_key_string = privy_auth_key.replace("wallet-auth:", "")
    private_key_pem = (
        f"-----BEGIN PRIVATE KEY-----\n{private_key_string}\n-----END PRIVATE KEY-----"
    )
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )
    signature = private_key.sign(
        serialized_payload.encode("utf-8"), ec.ECDSA(hashes.SHA256())
    )
    return base64.b64encode(signature).decode("utf-8")


async def get_privy_embedded_wallet(
    user_id: str, app_id: str, app_secret: str
) -> Optional[Dict[str, str]]:
    url = f"https://auth.privy.io/api/v1/users/{user_id}"
    headers = {"privy-app-id": app_id}
    auth = (app_id, app_secret)
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, auth=auth, timeout=10)
        if resp.status_code != 200:
            logging.error(f"Privy API error: {resp.text}")
            resp.raise_for_status()
        data = resp.json()
        for acct in data.get("linked_accounts", []):
            if acct.get("connector_type") == "embedded" and acct.get("delegated"):
                return {"wallet_id": acct["id"], "public_key": acct["public_key"]}
    return None


async def privy_sign_and_send(
    wallet_id: str, encoded_tx: str, app_id: str, app_secret: str, privy_auth_key: str
) -> Dict[str, Any]:
    url = f"https://api.privy.io/v1/wallets/{wallet_id}/rpc"
    auth_string = f"{app_id}:{app_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    body = {
        "method": "signAndSendTransaction",
        "caip2": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
        "params": {"transaction": encoded_tx, "encoding": "base64"},
    }
    signature = get_authorization_signature(
        url=url, body=body, privy_app_id=app_id, privy_auth_key=privy_auth_key
    )
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "privy-app-id": app_id,
        "privy-authorization-signature": signature,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=body, timeout=20)
        if resp.status_code != 200:
            logging.error(f"Privy API error: {resp.text}")
            resp.raise_for_status()
        return resp.json()


class PrivySwapTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_swap",
            description="Swap tokens using Jupiter via Privy delegated wallet.",
            registry=registry,
        )
        self.app_id = None
        self.app_secret = None
        self.signing_key = None
        self.rpc_url = None
        self.jupiter_url = None
        self.fee_payer = None
        self.fee_percentage = 0.85  # Default fee percentage (0.85% = 0.0085)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Privy user id (did)"},
                "output_mint": {
                    "type": "string",
                    "description": "The mint address of the token to receive.",
                },
                "input_amount": {
                    "type": "number",
                    "description": "The amount of the input token to swap.",
                },
                "input_mint": {
                    "type": "string",
                    "description": "The mint address of the token to swap from.",
                },
            },
            "required": ["user_id", "output_mint", "input_amount", "input_mint"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        tool_cfg = config.get("tools", {}).get("privy_swap", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")
        self.signing_key = tool_cfg.get("signing_key")
        self.rpc_url = tool_cfg.get("rpc_url")
        self.jupiter_url = tool_cfg.get("jupiter_url")
        self.fee_payer = tool_cfg.get("fee_payer")
        self.fee_percentage = tool_cfg.get("fee_percentage", 0.85)  # Default 0.85% fee

    async def execute(
        self,
        user_id: str,
        output_mint: str,
        input_amount: float,
        input_mint: str,
        slippage_bps: int = 300,
    ) -> Dict[str, Any]:
        if not all(
            [
                self.app_id,
                self.app_secret,
                self.signing_key,
                self.rpc_url,
                self.fee_payer,
            ]
        ):
            return {"status": "error", "message": "Privy config missing."}
        wallet_info = await get_privy_embedded_wallet(
            user_id, self.app_id, self.app_secret
        )
        if not wallet_info:
            return {
                "status": "error",
                "message": "No delegated embedded wallet found for user.",
            }
        wallet_id = wallet_info["wallet_id"]
        try:
            wallet = SolanaWalletClient(
                self.rpc_url, None, wallet_info["public_key"], self.fee_payer
            )
            provider = None
            if "helius" in self.rpc_url:
                provider = "helius"
            transaction = await TradeManager.trade(
                wallet,
                output_mint,
                input_amount,
                input_mint,
                slippage_bps,
                self.jupiter_url,
                True,
                provider,
                self.fee_percentage,
            )
            encoded_transaction = base64.b64encode(bytes(transaction)).decode("utf-8")
            result = await privy_sign_and_send(
                wallet_id,
                encoded_transaction,
                self.app_id,
                self.app_secret,
                self.signing_key,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            logging.exception(f"Privy swap failed: {str(e)}")
            return {"status": "error", "message": str(e)}


class PrivySwapPlugin:
    def __init__(self):
        self.name = "privy_swap"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for swapping tokens using Jupiter via Privy delegated wallet."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = PrivySwapTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return PrivySwapPlugin()
