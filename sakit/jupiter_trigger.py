"""
Jupiter Trigger (Limit Order) tool for Solana Agent Kit.

Enables creating, canceling, and managing limit orders using Jupiter Trigger API.
"""

import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
from solders.keypair import Keypair  # type: ignore

from sakit.utils.trigger import JupiterTrigger, sign_trigger_transaction

logger = logging.getLogger(__name__)


class JupiterTriggerTool(AutoTool):
    """Create and manage limit orders using Jupiter Trigger API."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="jupiter_trigger",
            description=(
                "Create and manage limit orders on Solana using Jupiter Trigger API. "
                "Actions: 'create' (new limit order), 'cancel' (cancel specific order), "
                "'cancel_all' (cancel all orders), 'list' (view orders). "
                "For cancel, first use 'list' action to get the order public key."
            ),
            registry=registry,
        )
        self._private_key: Optional[str] = None
        self._jupiter_api_key: Optional[str] = None
        self._referral_account: Optional[str] = None
        self._referral_fee: Optional[int] = None
        self._payer_private_key: Optional[str] = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
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
                    "description": "Token mint to sell (required for 'create'). Pass empty string if not needed.",
                    "default": "",
                },
                "output_mint": {
                    "type": "string",
                    "description": "Token mint to buy (required for 'create'). Pass empty string if not needed.",
                    "default": "",
                },
                "making_amount": {
                    "type": "string",
                    "description": "Amount of input token to sell in base units (required for 'create'). Pass empty string if not needed.",
                    "default": "",
                },
                "taking_amount": {
                    "type": "string",
                    "description": "Amount of output token to receive in base units (required for 'create'). Pass empty string if not needed.",
                    "default": "",
                },
                "expired_at": {
                    "type": "string",
                    "description": "Unix timestamp when order expires (optional for 'create'). Pass empty string if not needed.",
                    "default": "",
                },
                "order_pubkey": {
                    "type": "string",
                    "description": "Order public key to cancel (required for 'cancel'). Get this from 'list' action. Pass empty string if not needed.",
                    "default": "",
                },
                "wallet_address": {
                    "type": "string",
                    "description": "Wallet address to query orders for (optional for 'list', defaults to configured wallet). Pass empty string if not needed.",
                    "default": "",
                },
            },
            "required": [
                "action",
                "input_mint",
                "output_mint",
                "making_amount",
                "taking_amount",
                "expired_at",
                "order_pubkey",
                "wallet_address",
            ],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("jupiter_trigger", {})
        self._private_key = tool_cfg.get("private_key")
        self._jupiter_api_key = tool_cfg.get("jupiter_api_key")
        self._referral_account = tool_cfg.get("referral_account")
        self._referral_fee = tool_cfg.get("referral_fee")
        self._payer_private_key = tool_cfg.get("payer_private_key")

    async def execute(
        self,
        action: str,
        input_mint: Optional[str] = None,
        output_mint: Optional[str] = None,
        making_amount: Optional[str] = None,
        taking_amount: Optional[str] = None,
        expired_at: Optional[str] = None,
        order_pubkey: Optional[str] = None,
        wallet_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        action = action.lower().strip()
        trigger = JupiterTrigger(api_key=self._jupiter_api_key)

        if action == "create":
            return await self._create_order(
                trigger,
                input_mint,
                output_mint,
                making_amount,
                taking_amount,
                expired_at,
            )
        elif action == "cancel":  # pragma: no cover
            return await self._cancel_order(trigger, order_pubkey)
        elif action == "cancel_all":  # pragma: no cover
            return await self._cancel_all_orders(trigger)
        elif action == "list":  # pragma: no cover
            return await self._list_orders(trigger, wallet_address)
        else:  # pragma: no cover
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Valid actions: create, cancel, cancel_all, list",
            }

    async def _create_order(  # pragma: no cover
        self,
        trigger: JupiterTrigger,
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

        if not self._private_key:
            return {"status": "error", "message": "Private key not configured."}

        try:
            keypair = Keypair.from_base58_string(self._private_key)
            maker = str(keypair.pubkey())

            # Check if integrator payer is configured for gasless transactions
            payer_keypair = None
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Create order
            result = await trigger.create_order(
                input_mint=input_mint,
                output_mint=output_mint,
                maker=maker,
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

            # Sign the transaction
            signed_tx = sign_trigger_transaction(
                transaction_base64=result.transaction,
                sign_message_func=keypair.sign_message,
                payer_sign_func=payer_keypair.sign_message if payer_keypair else None,
            )

            # Execute
            exec_result = await trigger.execute(signed_tx, result.request_id)

            if not exec_result.success:
                return {"status": "error", "message": exec_result.error}

            return {
                "status": "success",
                "action": "create",
                "order_pubkey": result.order,
                "signature": exec_result.signature,
                "message": f"Limit order created. Order pubkey: {result.order}",
            }

        except Exception as e:
            logger.exception(f"Failed to create trigger order: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _cancel_order(  # pragma: no cover
        self,
        trigger: JupiterTrigger,
        order_pubkey: Optional[str],
    ) -> Dict[str, Any]:
        if not order_pubkey:
            return {
                "status": "error",
                "message": "Missing required parameter: order_pubkey. Use 'list' action first to get order pubkeys.",
            }

        if not self._private_key:
            return {"status": "error", "message": "Private key not configured."}

        try:
            keypair = Keypair.from_base58_string(self._private_key)
            maker = str(keypair.pubkey())

            # Verify the order belongs to this user before attempting to cancel
            orders_result = await trigger.get_orders(user=maker, order_status="active")
            if orders_result.get("success", False):
                user_orders = [
                    o.get("order") or o.get("orderPubkey")
                    for o in orders_result.get("orders", [])
                ]
                if order_pubkey not in user_orders:
                    return {
                        "status": "error",
                        "message": f"Order {order_pubkey} does not belong to this wallet or is not active.",
                    }

            payer_keypair = None
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            result = await trigger.cancel_order(
                maker=maker,
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

            signed_tx = sign_trigger_transaction(
                transaction_base64=result.transaction,
                sign_message_func=keypair.sign_message,
                payer_sign_func=payer_keypair.sign_message if payer_keypair else None,
            )

            exec_result = await trigger.execute(signed_tx, result.request_id)

            if not exec_result.success:
                return {"status": "error", "message": exec_result.error}

            return {
                "status": "success",
                "action": "cancel",
                "order_pubkey": order_pubkey,
                "signature": exec_result.signature,
                "message": f"Order {order_pubkey} cancelled.",
            }

        except Exception as e:
            logger.exception(f"Failed to cancel trigger order: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _cancel_all_orders(
        self, trigger: JupiterTrigger
    ) -> Dict[str, Any]:  # pragma: no cover
        if not self._private_key:
            return {"status": "error", "message": "Private key not configured."}

        try:
            keypair = Keypair.from_base58_string(self._private_key)
            maker = str(keypair.pubkey())

            payer_keypair = None
            payer_pubkey = None
            if self._payer_private_key:
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Get all active orders first
            orders_result = await trigger.get_orders(user=maker, order_status="active")

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

            # Cancel all orders
            result = await trigger.cancel_orders(
                maker=maker,
                orders=None,  # None = cancel all
                payer=payer_pubkey,
            )

            if not result.success:
                return {"status": "error", "message": result.error}

            if not result.transactions:
                return {
                    "status": "error",
                    "message": "No transactions returned from Jupiter.",
                }

            # Sign and execute each transaction batch
            signatures = []
            for tx_base64 in result.transactions:
                signed_tx = sign_trigger_transaction(
                    transaction_base64=tx_base64,
                    sign_message_func=keypair.sign_message,
                    payer_sign_func=payer_keypair.sign_message
                    if payer_keypair
                    else None,
                )
                exec_result = await trigger.execute(signed_tx, result.request_id)
                if exec_result.success and exec_result.signature:
                    signatures.append(exec_result.signature)

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

    async def _list_orders(  # pragma: no cover
        self,
        trigger: JupiterTrigger,
        wallet_address: Optional[str],
    ) -> Dict[str, Any]:
        try:
            if wallet_address:
                wallet = wallet_address
            elif self._private_key:
                keypair = Keypair.from_base58_string(self._private_key)
                wallet = str(keypair.pubkey())
            else:
                return {
                    "status": "error",
                    "message": "Either wallet_address parameter or private_key config required.",
                }

            result = await trigger.get_orders(user=wallet, order_status="active")

            if not result.get("success", False):
                return {
                    "status": "error",
                    "message": result.get("error", "Failed to fetch orders"),
                }

            orders = result.get("orders", [])

            # Format orders for easy reading
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
                "wallet": wallet,
                "order_count": len(formatted_orders),
                "orders": formatted_orders,
                "message": f"Found {len(formatted_orders)} active orders."
                if formatted_orders
                else "No active orders.",
            }

        except Exception as e:
            logger.exception(f"Failed to list trigger orders: {str(e)}")
            return {"status": "error", "message": str(e)}


class JupiterTriggerPlugin:
    """Plugin for creating and managing limit orders using Jupiter Trigger."""

    def __init__(self):
        self.name = "jupiter_trigger"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):  # pragma: no cover
        return (
            "Plugin for creating and managing limit orders using Jupiter Trigger API."
        )

    def initialize(self, tool_registry: ToolRegistry) -> None:  # pragma: no cover
        self.tool_registry = tool_registry
        self._tool = JupiterTriggerTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:  # pragma: no cover
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:  # pragma: no cover
        return [self._tool] if self._tool else []


def get_plugin():  # pragma: no cover
    return JupiterTriggerPlugin()
