"""
Jupiter Trigger (Limit Order) tool for Privy delegated wallets.

Enables creating, canceling, and managing limit orders using Jupiter Trigger API
with Privy embedded wallets.
"""

import base64
import json
import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from solders.keypair import Keypair  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import to_bytes_versioned  # type: ignore

from sakit.utils.trigger import JupiterTrigger

logger = logging.getLogger(__name__)


def _canonicalize(obj):
    """Canonicalize JSON for Privy signature."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _get_authorization_signature(url, body, privy_app_id, privy_auth_key):
    """Generate Privy authorization signature."""
    payload = {
        "version": 1,
        "method": "POST",
        "url": url,
        "body": body,
        "headers": {"privy-app-id": privy_app_id},
    }
    serialized_payload = _canonicalize(payload)
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


async def _get_privy_embedded_wallet(
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
            return None
        data = resp.json()
        for acct in data.get("linked_accounts", []):
            if acct.get("connector_type") == "embedded" and acct.get("delegated"):
                return {"wallet_id": acct["id"], "public_key": acct["public_key"]}
    return None


async def _privy_sign_transaction(
    wallet_id: str,
    encoded_tx: str,
    app_id: str,
    app_secret: str,
    privy_auth_key: str,
) -> Optional[str]:
    """Sign transaction via Privy."""
    url = f"https://api.privy.io/v1/wallets/{wallet_id}/rpc"
    auth_string = f"{app_id}:{app_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    body = {
        "method": "signTransaction",
        "caip2": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
        "params": {"transaction": encoded_tx, "encoding": "base64"},
    }
    signature = _get_authorization_signature(
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
            return None
        result = resp.json()
        return result.get("data", {}).get("signedTransaction")


class PrivyTriggerTool(AutoTool):
    """Create and manage limit orders using Jupiter Trigger API with Privy wallets."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_trigger",
            description=(
                "Create and manage limit orders on Solana using Jupiter Trigger API with Privy delegated wallets. "
                "Actions: 'create' (new limit order), 'cancel' (cancel specific order), "
                "'cancel_all' (cancel all orders), 'list' (view orders). "
                "For cancel, first use 'list' action to get the order public key."
            ),
            registry=registry,
        )
        self._app_id: Optional[str] = None
        self._app_secret: Optional[str] = None
        self._signing_key: Optional[str] = None
        self._jupiter_api_key: Optional[str] = None
        self._referral_account: Optional[str] = None
        self._referral_fee: Optional[int] = None
        self._payer_private_key: Optional[str] = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Privy user id (did) for the delegated wallet.",
                },
                "action": {
                    "type": "string",
                    "enum": ["create", "cancel", "cancel_all", "list"],
                    "description": (
                        "Action to perform: 'create' (new limit order), "
                        "'cancel' (cancel specific order by pubkey), "
                        "'cancel_all' (cancel all open orders), "
                        "'list' (view active orders)"
                    ),
                },
                "input_mint": {
                    "type": "string",
                    "description": "Token mint to sell (required for 'create').",
                },
                "output_mint": {
                    "type": "string",
                    "description": "Token mint to buy (required for 'create').",
                },
                "making_amount": {
                    "type": "string",
                    "description": "Amount of input token to sell in base units (required for 'create').",
                },
                "taking_amount": {
                    "type": "string",
                    "description": "Amount of output token to receive in base units (required for 'create').",
                },
                "expired_at": {
                    "type": "string",
                    "description": "Unix timestamp when order expires (optional for 'create').",
                },
                "order_pubkey": {
                    "type": "string",
                    "description": "Order public key to cancel (required for 'cancel'). Get this from 'list' action.",
                },
            },
            "required": ["user_id", "action"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("privy_trigger", {})
        self._app_id = tool_cfg.get("app_id")
        self._app_secret = tool_cfg.get("app_secret")
        self._signing_key = tool_cfg.get("signing_key")
        self._jupiter_api_key = tool_cfg.get("jupiter_api_key")
        self._referral_account = tool_cfg.get("referral_account")
        self._referral_fee = tool_cfg.get("referral_fee")
        self._payer_private_key = tool_cfg.get("payer_private_key")

    async def execute(
        self,
        user_id: str,
        action: str,
        input_mint: Optional[str] = None,
        output_mint: Optional[str] = None,
        making_amount: Optional[str] = None,
        taking_amount: Optional[str] = None,
        expired_at: Optional[str] = None,
        order_pubkey: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not all([self._app_id, self._app_secret, self._signing_key]):
            return {"status": "error", "message": "Privy config missing."}

        # Get user's embedded wallet
        wallet_info = await _get_privy_embedded_wallet(
            user_id, self._app_id, self._app_secret
        )
        if not wallet_info:
            return {
                "status": "error",
                "message": "No delegated embedded wallet found for user.",
            }

        wallet_id = wallet_info["wallet_id"]
        public_key = wallet_info["public_key"]

        action = action.lower().strip()
        trigger = JupiterTrigger(api_key=self._jupiter_api_key)

        if action == "create":
            return await self._create_order(
                trigger,
                wallet_id,
                public_key,
                input_mint,
                output_mint,
                making_amount,
                taking_amount,
                expired_at,
            )
        elif action == "cancel":
            return await self._cancel_order(
                trigger, wallet_id, public_key, order_pubkey
            )
        elif action == "cancel_all":
            return await self._cancel_all_orders(trigger, wallet_id, public_key)
        elif action == "list":
            return await self._list_orders(trigger, public_key)
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Valid actions: create, cancel, cancel_all, list",
            }

    async def _sign_and_execute(
        self,
        trigger: JupiterTrigger,
        wallet_id: str,
        transaction_base64: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Sign with payer (if configured) and Privy, then execute."""
        try:
            tx_to_sign = transaction_base64

            # If payer is configured, sign with payer first
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                tx_bytes = base64.b64decode(transaction_base64)
                transaction = VersionedTransaction.from_bytes(tx_bytes)
                message_bytes = to_bytes_versioned(transaction.message)
                payer_signature = payer_keypair.sign_message(message_bytes)

                # Create partially signed transaction
                partially_signed = VersionedTransaction.populate(
                    transaction.message,
                    [payer_signature, transaction.signatures[1]],
                )
                tx_to_sign = base64.b64encode(bytes(partially_signed)).decode("utf-8")

            # Sign with Privy
            signed_tx = await _privy_sign_transaction(
                wallet_id,
                tx_to_sign,
                self._app_id,
                self._app_secret,
                self._signing_key,
            )

            if not signed_tx:
                return {
                    "status": "error",
                    "message": "Failed to sign transaction via Privy.",
                }

            # Execute
            exec_result = await trigger.execute(signed_tx, request_id)

            if not exec_result.success:
                return {"status": "error", "message": exec_result.error}

            return {"status": "success", "signature": exec_result.signature}

        except Exception as e:
            logger.exception(f"Failed to sign and execute: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _create_order(
        self,
        trigger: JupiterTrigger,
        wallet_id: str,
        public_key: str,
        input_mint: Optional[str],
        output_mint: Optional[str],
        making_amount: Optional[str],
        taking_amount: Optional[str],
        expired_at: Optional[str],
    ) -> Dict[str, Any]:
        if not all([input_mint, output_mint, making_amount, taking_amount]):
            return {
                "status": "error",
                "message": "Missing required parameters: input_mint, output_mint, making_amount, taking_amount",
            }

        try:
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            result = await trigger.create_order(
                input_mint=input_mint,
                output_mint=output_mint,
                maker=public_key,
                making_amount=making_amount,
                taking_amount=taking_amount,
                payer=payer_pubkey,
                expired_at=expired_at,
                fee_bps=self._referral_fee,
                fee_account=self._referral_account,
            )

            if not result.success:
                return {"status": "error", "message": result.error}

            if not result.transaction:
                return {
                    "status": "error",
                    "message": "No transaction returned from Jupiter.",
                }

            exec_result = await self._sign_and_execute(
                trigger, wallet_id, result.transaction, result.request_id
            )

            if exec_result["status"] != "success":
                return exec_result

            return {
                "status": "success",
                "action": "create",
                "order_pubkey": result.order,
                "signature": exec_result["signature"],
                "message": f"Limit order created. Order pubkey: {result.order}",
            }

        except Exception as e:
            logger.exception(f"Failed to create trigger order: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _cancel_order(
        self,
        trigger: JupiterTrigger,
        wallet_id: str,
        public_key: str,
        order_pubkey: Optional[str],
    ) -> Dict[str, Any]:
        if not order_pubkey:
            return {
                "status": "error",
                "message": "Missing required parameter: order_pubkey. Use 'list' action first to get order pubkeys.",
            }

        try:
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            result = await trigger.cancel_order(
                maker=public_key,
                order=order_pubkey,
                payer=payer_pubkey,
            )

            if not result.success:
                return {"status": "error", "message": result.error}

            if not result.transaction:
                return {
                    "status": "error",
                    "message": "No transaction returned from Jupiter.",
                }

            exec_result = await self._sign_and_execute(
                trigger, wallet_id, result.transaction, result.request_id
            )

            if exec_result["status"] != "success":
                return exec_result

            return {
                "status": "success",
                "action": "cancel",
                "order_pubkey": order_pubkey,
                "signature": exec_result["signature"],
                "message": f"Order {order_pubkey} cancelled.",
            }

        except Exception as e:
            logger.exception(f"Failed to cancel trigger order: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _cancel_all_orders(
        self,
        trigger: JupiterTrigger,
        wallet_id: str,
        public_key: str,
    ) -> Dict[str, Any]:
        try:
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Get active orders first
            orders_result = await trigger.get_orders(
                user=public_key, order_status="active"
            )

            if not orders_result.get("success", False):
                return {
                    "status": "error",
                    "message": orders_result.get("error", "Failed to fetch orders"),
                }

            orders = orders_result.get("orders", [])
            if not orders:
                return {
                    "status": "success",
                    "action": "cancel_all",
                    "cancelled_count": 0,
                    "message": "No active orders to cancel.",
                }

            result = await trigger.cancel_orders(
                maker=public_key,
                orders=None,
                payer=payer_pubkey,
            )

            if not result.success:
                return {"status": "error", "message": result.error}

            if not result.transactions:
                return {
                    "status": "error",
                    "message": "No transactions returned from Jupiter.",
                }

            signatures = []
            for tx_base64 in result.transactions:
                exec_result = await self._sign_and_execute(
                    trigger, wallet_id, tx_base64, result.request_id
                )
                if exec_result["status"] == "success":
                    signatures.append(exec_result["signature"])

            return {
                "status": "success",
                "action": "cancel_all",
                "cancelled_count": len(orders),
                "signatures": signatures,
                "message": f"Cancelled {len(orders)} orders.",
            }

        except Exception as e:
            logger.exception(f"Failed to cancel all trigger orders: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _list_orders(
        self,
        trigger: JupiterTrigger,
        public_key: str,
    ) -> Dict[str, Any]:
        try:
            result = await trigger.get_orders(user=public_key, order_status="active")

            if not result.get("success", False):
                return {
                    "status": "error",
                    "message": result.get("error", "Failed to fetch orders"),
                }

            orders = result.get("orders", [])

            formatted_orders = []
            for order in orders:
                formatted_orders.append(
                    {
                        "order_pubkey": order.get("order") or order.get("orderPubkey"),
                        "input_mint": order.get("inputMint"),
                        "output_mint": order.get("outputMint"),
                        "making_amount": order.get("makingAmount"),
                        "taking_amount": order.get("takingAmount"),
                        "filled_making_amount": order.get("filledMakingAmount"),
                        "filled_taking_amount": order.get("filledTakingAmount"),
                        "expired_at": order.get("expiredAt"),
                        "created_at": order.get("createdAt"),
                    }
                )

            return {
                "status": "success",
                "action": "list",
                "wallet": public_key,
                "order_count": len(formatted_orders),
                "orders": formatted_orders,
                "message": f"Found {len(formatted_orders)} active orders."
                if formatted_orders
                else "No active orders.",
            }

        except Exception as e:
            logger.exception(f"Failed to list trigger orders: {str(e)}")
            return {"status": "error", "message": str(e)}


class PrivyTriggerPlugin:
    """Plugin for creating and managing limit orders using Jupiter Trigger with Privy wallets."""

    def __init__(self):
        self.name = "privy_trigger"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for creating and managing limit orders using Jupiter Trigger API with Privy delegated wallets."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = PrivyTriggerTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return PrivyTriggerPlugin()
