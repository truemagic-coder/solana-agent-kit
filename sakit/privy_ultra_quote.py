"""
Jupiter Ultra swap quote tool for Privy embedded wallets.

Provides a preview of swap details (slippage, price impact, amounts) without executing.
"""

import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
from privy import AsyncPrivyAPI
from solders.keypair import Keypair

from sakit.utils.ultra import JupiterUltra
from sakit.utils.wallet import sanitize_privy_user_id


logger = logging.getLogger(__name__)


async def get_privy_embedded_wallet(
    privy_client: AsyncPrivyAPI, user_id: str
) -> Optional[Dict[str, str]]:
    """Get Privy embedded wallet info for a user using the official SDK.

    Supports both:
    - App-first wallets (SDK-created): connector_type == "embedded" with delegated == True
    - Bot-first wallets (API-created): type == "wallet" with chain_type == "solana"
    """
    try:
        user = await privy_client.users.get(user_id)
        linked_accounts = user.linked_accounts or []
        logger.info(f"Privy user {user_id} has {len(linked_accounts)} linked accounts")

        # Log all account types for debugging
        for i, acct in enumerate(linked_accounts):
            acct_type = getattr(acct, "type", "unknown")
            connector_type = getattr(acct, "connector_type", "none")
            chain_type = getattr(acct, "chain_type", "none")
            delegated = getattr(acct, "delegated", False)
            has_id = hasattr(acct, "id") and acct.id is not None
            has_address = hasattr(acct, "address") and acct.address is not None
            has_public_key = hasattr(acct, "public_key") and acct.public_key is not None
            logger.info(
                f"  Account {i}: type={acct_type}, connector_type={connector_type}, "
                f"chain_type={chain_type}, delegated={delegated}, "
                f"has_id={has_id}, has_address={has_address}, has_public_key={has_public_key}"
            )

        # First, try to find embedded wallet with delegation
        for acct in linked_accounts:
            if getattr(acct, "connector_type", None) == "embedded" and getattr(
                acct, "delegated", False
            ):
                wallet_id = getattr(acct, "id", None)
                # Use 'address' field if 'public_key' is null (common for API-created wallets)
                address = getattr(acct, "address", None) or getattr(
                    acct, "public_key", None
                )
                if wallet_id and address:
                    logger.info(
                        f"Found embedded delegated wallet: {wallet_id}, address: {address}"
                    )
                    return {"wallet_id": wallet_id, "public_key": address}

        # Then, try to find bot-first wallet (API-created via privy_create_wallet)
        # These have type == "wallet" and include chain_type
        for acct in linked_accounts:
            acct_type = getattr(acct, "type", "")
            # Check for Solana embedded wallets created via API
            if acct_type == "wallet" and getattr(acct, "chain_type", None) == "solana":
                wallet_id = getattr(acct, "id", None)
                # API wallets use "address" field, SDK wallets use "public_key"
                address = getattr(acct, "address", None) or getattr(
                    acct, "public_key", None
                )
                if wallet_id and address:
                    logger.info(
                        f"Found bot-first wallet: {wallet_id}, address: {address}"
                    )
                    return {"wallet_id": wallet_id, "public_key": address}
            # Also check for solana_embedded_wallet type
            if (
                acct_type
                and "solana" in acct_type.lower()
                and "embedded" in acct_type.lower()
            ):
                wallet_id = getattr(acct, "id", None)
                address = getattr(acct, "address", None) or getattr(
                    acct, "public_key", None
                )
                if wallet_id and address:
                    logger.info(
                        f"Found solana_embedded_wallet: {wallet_id}, address: {address}"
                    )
                    return {"wallet_id": wallet_id, "public_key": address}

        logger.warning(f"No suitable wallet found for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"Privy API error getting user {user_id}: {e}")
        return None


logger = logging.getLogger(__name__)


class PrivyUltraQuoteTool(AutoTool):
    """Get a swap quote from Jupiter Ultra via Privy delegated wallet."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_ultra_quote",
            description="Get a quote for swapping tokens using Jupiter Ultra API via Privy delegated wallet. Shows slippage, price impact, and amounts before executing the swap.",
            registry=registry,
        )
        self.app_id = None
        self.app_secret = None
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
                    "description": "Privy user id (DID like 'did:privy:xxx'). Get this from privy_get_user_by_telegram's 'result.user_id' field. REQUIRED.",
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
        tool_cfg = config.get("tools", {}).get("privy_ultra_quote", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")
        self.jupiter_api_key = tool_cfg.get("jupiter_api_key")
        self.referral_account = tool_cfg.get("referral_account")
        self.referral_fee = tool_cfg.get("referral_fee")
        self.payer_private_key = tool_cfg.get("payer_private_key")

    async def execute(  # pragma: no cover
        self,
        user_id: str,
        input_mint: str,
        output_mint: str,
        amount: int,
    ) -> Dict[str, Any]:
        # Sanitize user_id to handle LLM formatting errors
        user_id = sanitize_privy_user_id(user_id) or user_id

        if not all([self.app_id, self.app_secret]):
            return {"status": "error", "message": "Privy config missing."}

        # Create Privy client using the official SDK
        privy_client = AsyncPrivyAPI(
            app_id=self.app_id,
            app_secret=self.app_secret,
        )

        try:
            # Get user's embedded wallet
            wallet_info = await get_privy_embedded_wallet(privy_client, user_id)
            if not wallet_info:
                return {
                    "status": "error",
                    "message": "No delegated embedded wallet found for user.",
                }

            public_key = wallet_info["public_key"]

            # Check if integrator payer is configured for gasless transactions
            payer_pubkey = None
            if self.payer_private_key:
                payer_keypair = Keypair.from_base58_string(self.payer_private_key)
                payer_pubkey = str(payer_keypair.pubkey())

            # Initialize Jupiter Ultra client
            ultra = JupiterUltra(api_key=self.jupiter_api_key)

            # Get swap quote (doesn't execute, just shows details)
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

            # Format price impact as percentage with sign
            price_impact_str = ""
            if order.price_impact is not None:
                price_impact_str = f"{order.price_impact:.2f}%"

            # Format USD values
            in_usd_str = f"${order.in_usd_value:.2f}" if order.in_usd_value else None
            out_usd_str = f"${order.out_usd_value:.2f}" if order.out_usd_value else None

            # Return quote details without executing
            return {
                "status": "success",
                "input_mint": order.input_mint,
                "output_mint": order.output_mint,
                "in_amount": order.in_amount,
                "out_amount": order.out_amount,
                "in_usd_value": in_usd_str,
                "out_usd_value": out_usd_str,
                "slippage_bps": order.slippage_bps,
                "price_impact_pct": price_impact_str,
                "swap_type": order.swap_type,
                "gasless": order.gasless,
                "message": "Preview only - no transaction executed. Call privy_ultra to execute the swap.",
            }

        except Exception as e:
            logger.exception(f"Privy Ultra quote failed: {str(e)}")
            return {"status": "error", "message": str(e)}
        finally:
            await privy_client.close()


class PrivyUltraQuotePlugin:
    """Plugin for getting swap quotes via Privy using Jupiter Ultra."""

    def __init__(self):
        self.name = "privy_ultra_quote"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for getting swap quotes using Jupiter Ultra API via Privy."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = PrivyUltraQuoteTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return PrivyUltraQuotePlugin()
