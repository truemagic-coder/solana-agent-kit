"""
Jupiter Ultra swap tool for Privy embedded wallets.

Enables swapping tokens using Jupiter Ultra API via Privy delegated wallets.
"""

import base64
import json
import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

from sakit.utils.ultra import JupiterUltra

logger = logging.getLogger(__name__)


def canonicalize(obj):
    """Canonicalize JSON for Privy signature."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def get_authorization_signature(url, body, privy_app_id, privy_auth_key):
    """Generate Privy authorization signature."""
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
    """Get Privy embedded wallet info for a user."""
    url = f"https://auth.privy.io/api/v1/users/{user_id}"
    headers = {"privy-app-id": app_id}
    auth = (app_id, app_secret)
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, auth=auth, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Privy API error: {resp.text}")
            resp.raise_for_status()
        data = resp.json()
        for acct in data.get("linked_accounts", []):
            if acct.get("connector_type") == "embedded" and acct.get("delegated"):
                return {"wallet_id": acct["id"], "public_key": acct["public_key"]}
    return None


async def privy_sign_and_send(
    wallet_id: str, encoded_tx: str, app_id: str, app_secret: str, privy_auth_key: str
) -> Dict[str, Any]:
    """Sign and send transaction via Privy."""
    url = f"https://api.privy.io/v1/wallets/{wallet_id}/rpc"
    auth_string = f"{app_id}:{app_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    body = {
        "method": "signTransaction",
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
            logger.error(f"Privy API error: {resp.text}")
            resp.raise_for_status()
        return resp.json()


class PrivyUltraTool(AutoTool):
    """Swap tokens using Jupiter Ultra via Privy delegated wallet."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_ultra",
            description="Swap tokens using Jupiter Ultra API via Privy delegated wallet. Provides the best trading experience with MEV protection, optimal slippage, and fast execution.",
            registry=registry,
        )
        self.app_id = None
        self.app_secret = None
        self.signing_key = None
        self.jupiter_api_key = None
        self.referral_account = None
        self.referral_fee = None
        self.payer_private_key = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Privy user id (did)",
                },
                "input_mint": {
                    "type": "string",
                    "description": "The mint address of the token to swap from.",
                },
                "output_mint": {
                    "type": "string",
                    "description": "The mint address of the token to receive.",
                },
                "amount": {
                    "type": "integer",
                    "description": "The amount of input token to swap (in smallest units, e.g., lamports for SOL).",
                },
            },
            "required": ["user_id", "input_mint", "output_mint", "amount"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        tool_cfg = config.get("tools", {}).get("privy_ultra", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")
        self.signing_key = tool_cfg.get("signing_key")
        self.jupiter_api_key = tool_cfg.get("jupiter_api_key")
        self.referral_account = tool_cfg.get("referral_account")
        self.referral_fee = tool_cfg.get("referral_fee")
        self.payer_private_key = tool_cfg.get("payer_private_key")

    async def execute(
        self,
        user_id: str,
        input_mint: str,
        output_mint: str,
        amount: int,
    ) -> Dict[str, Any]:
        if not all([self.app_id, self.app_secret, self.signing_key]):
            return {"status": "error", "message": "Privy config missing."}

        # Get user's embedded wallet
        wallet_info = await get_privy_embedded_wallet(
            user_id, self.app_id, self.app_secret
        )
        if not wallet_info:
            return {
                "status": "error",
                "message": "No delegated embedded wallet found for user.",
            }

        wallet_id = wallet_info["wallet_id"]
        public_key = wallet_info["public_key"]

        try:
            # Check if integrator payer is configured for gasless transactions
            payer_keypair = None
            payer_pubkey = None
            if self.payer_private_key:
                payer_keypair = Keypair.from_base58_string(self.payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Initialize Jupiter Ultra client
            ultra = JupiterUltra(api_key=self.jupiter_api_key)

            # Get swap order
            order = await ultra.get_order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                taker=public_key,
                referral_account=self.referral_account,
                referral_fee=self.referral_fee,
                payer=payer_pubkey,
                close_authority=public_key if payer_pubkey else None,
            )

            if not order.transaction:
                return {
                    "status": "error",
                    "message": "No transaction returned from Jupiter Ultra.",
                }

            # If payer is configured, we need to sign with payer first, then Privy
            tx_to_sign = order.transaction
            if payer_keypair:
                # Payer signs first
                tx_bytes = base64.b64decode(order.transaction)
                transaction = VersionedTransaction.from_bytes(tx_bytes)
                message_bytes = to_bytes_versioned(transaction.message)
                payer_signature = payer_keypair.sign_message(message_bytes)

                # Create partially signed transaction (payer signed, taker placeholder)
                # We need to pass this to Privy for the taker's signature
                partially_signed = VersionedTransaction.populate(
                    transaction.message,
                    [
                        payer_signature,
                        transaction.signatures[1],
                    ],  # Keep taker's placeholder
                )
                tx_to_sign = base64.b64encode(bytes(partially_signed)).decode("utf-8")

            # Sign transaction via Privy
            sign_result = await privy_sign_and_send(
                wallet_id,
                tx_to_sign,
                self.app_id,
                self.app_secret,
                self.signing_key,
            )

            signed_tx = sign_result.get("data", {}).get("signedTransaction")
            if not signed_tx:
                return {
                    "status": "error",
                    "message": "Failed to sign transaction via Privy.",
                    "details": sign_result,
                }

            # Execute the swap via Jupiter Ultra
            execute_result = await ultra.execute_order(
                signed_transaction=signed_tx,
                request_id=order.request_id,
            )

            if execute_result.status == "Success":
                return {
                    "status": "success",
                    "signature": execute_result.signature,
                    "input_amount": execute_result.input_amount_result,
                    "output_amount": execute_result.output_amount_result,
                    "swap_type": order.swap_type,
                    "gasless": order.gasless,
                }
            else:
                return {
                    "status": "error",
                    "message": execute_result.error or "Swap failed",
                    "code": execute_result.code,
                    "signature": execute_result.signature,
                }

        except Exception as e:
            logger.exception(f"Privy Ultra swap failed: {str(e)}")
            return {"status": "error", "message": str(e)}


class PrivyUltraPlugin:
    """Plugin for swapping tokens using Jupiter Ultra via Privy."""

    def __init__(self):
        self.name = "privy_ultra"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for swapping tokens using Jupiter Ultra API via Privy delegated wallet."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = PrivyUltraTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return PrivyUltraPlugin()
