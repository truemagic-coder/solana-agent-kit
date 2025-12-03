"""
Jupiter Ultra swap tool for Solana wallets.

Enables swapping tokens using Jupiter Ultra API with a Solana keypair.
"""

import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
from solders.keypair import Keypair

from sakit.utils.ultra import JupiterUltra, sign_ultra_transaction

logger = logging.getLogger(__name__)


class SolanaUltraTool(AutoTool):
    """Swap tokens using Jupiter Ultra with a Solana keypair."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="solana_ultra",
            description="Swap tokens using Jupiter Ultra API. Provides the best trading experience with MEV protection, optimal slippage, and fast execution.",
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
            "required": ["input_mint", "output_mint", "amount"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("solana_ultra", {})
        self._private_key = tool_cfg.get("private_key")
        self._jupiter_api_key = tool_cfg.get("jupiter_api_key")
        self._referral_account = tool_cfg.get("referral_account")
        self._referral_fee = tool_cfg.get("referral_fee")
        self._payer_private_key = tool_cfg.get("payer_private_key")

    async def execute(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
    ) -> Dict[str, Any]:
        if not self._private_key:
            return {"status": "error", "message": "Private key not configured."}

        try:
            keypair = Keypair.from_base58_string(self._private_key)
            taker = str(keypair.pubkey())

            # Check if integrator payer is configured for gasless transactions
            payer_keypair = None
            payer_pubkey = None
            if self._payer_private_key:  # pragma: no cover
                payer_keypair = Keypair.from_base58_string(self._payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Initialize Jupiter Ultra client
            ultra = JupiterUltra(api_key=self._jupiter_api_key)

            # Get swap order
            order = await ultra.get_order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                taker=taker,
                referral_account=self._referral_account,
                referral_fee=self._referral_fee,
                payer=payer_pubkey,
                close_authority=taker if payer_pubkey else None,
            )

            if not order.transaction:
                return {
                    "status": "error",
                    "message": "No transaction returned from Jupiter Ultra.",
                }

            # Sign the transaction
            signed_tx = sign_ultra_transaction(
                transaction_base64=order.transaction,
                sign_message_func=keypair.sign_message,
                payer_sign_func=payer_keypair.sign_message if payer_keypair else None,
            )

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
            logger.exception(f"Solana Ultra swap failed: {str(e)}")
            return {"status": "error", "message": str(e)}


class SolanaUltraPlugin:
    """Plugin for swapping tokens using Jupiter Ultra."""

    def __init__(self):
        self.name = "solana_ultra"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for swapping tokens using Jupiter Ultra API."

    def initialize(self, tool_registry: ToolRegistry) -> None:  # pragma: no cover
        self.tool_registry = tool_registry
        self._tool = SolanaUltraTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:  # pragma: no cover
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:  # pragma: no cover
        return [self._tool] if self._tool else []


def get_plugin():  # pragma: no cover
    return SolanaUltraPlugin()
