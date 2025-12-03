"""
Jupiter Ultra swap tool for Privy embedded wallets.

Enables swapping tokens using Jupiter Ultra API via Privy delegated wallets.
Uses the official Privy Python SDK for wallet operations.
"""

import base64
import logging
from typing import Dict, Any, List, Optional

from solana_agent import AutoTool, ToolRegistry
from privy import AsyncPrivyAPI
from privy.lib.authorization_signatures import get_authorization_signature
from cryptography.hazmat.primitives import serialization
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

from sakit.utils.ultra import JupiterUltra

logger = logging.getLogger(__name__)


def convert_key_to_pkcs8_pem(key_string: str) -> str:  # pragma: no cover
    """Convert a private key to PKCS#8 PEM format for the Privy SDK.

    The SDK expects keys in PKCS#8 PEM format (-----BEGIN PRIVATE KEY-----).
    This function handles keys in various formats:
    - Already in PKCS#8 PEM base64
    - SEC1 EC format (-----BEGIN EC PRIVATE KEY-----)
    - Raw DER bytes (PKCS#8 or SEC1)

    Returns the base64 content (without headers) in PKCS#8 format.
    """
    # Strip wallet-auth: prefix if present
    private_key_string = key_string.replace("wallet-auth:", "")

    # Try loading as PKCS#8 PEM format first
    try:
        private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_string}\n-----END PRIVATE KEY-----"
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        # Already in correct format, return as-is
        return private_key_string
    except (ValueError, TypeError):
        pass

    # Try as EC PRIVATE KEY (SEC1) format
    try:
        ec_key_pem = f"-----BEGIN EC PRIVATE KEY-----\n{private_key_string}\n-----END EC PRIVATE KEY-----"
        private_key = serialization.load_pem_private_key(
            ec_key_pem.encode("utf-8"), password=None
        )
        # Convert to PKCS#8 format
        pkcs8_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # Extract base64 content (remove headers and newlines)
        pkcs8_pem = pkcs8_bytes.decode("utf-8")
        lines = pkcs8_pem.strip().split("\n")
        base64_content = "".join(lines[1:-1])
        return base64_content
    except (ValueError, TypeError):
        pass

    # Try loading as raw DER bytes
    try:
        der_bytes = base64.b64decode(private_key_string)
        # Try PKCS#8 DER
        try:
            private_key = serialization.load_der_private_key(der_bytes, password=None)
        except (ValueError, TypeError):
            # Try SEC1 DER
            from cryptography.hazmat.primitives.asymmetric import ec

            private_key = ec.derive_private_key(
                int.from_bytes(der_bytes, "big"), ec.SECP256R1()
            )
        # Convert to PKCS#8 PEM format
        pkcs8_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pkcs8_pem = pkcs8_bytes.decode("utf-8")
        lines = pkcs8_pem.strip().split("\n")
        base64_content = "".join(lines[1:-1])
        return base64_content
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Could not load private key. Expected base64-encoded PKCS#8 or SEC1 format. "
            f"Generate with: openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256. Error: {e}"
        )


async def get_privy_embedded_wallet(  # pragma: no cover
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
        raise


async def privy_sign_transaction(  # pragma: no cover
    privy_client: AsyncPrivyAPI,
    wallet_id: str,
    encoded_tx: str,
    signing_key: str,
) -> Dict[str, Any]:
    """Sign a Solana transaction via Privy using the official SDK.

    Uses the wallets.rpc method with method="signTransaction" for Solana.
    The SDK handles authorization signature generation automatically when provided.
    """
    # Convert the key to PKCS#8 format expected by the SDK
    pkcs8_key = convert_key_to_pkcs8_pem(signing_key)

    # Generate the authorization signature using the SDK's utility
    # IMPORTANT: The body must match exactly what the SDK sends to the API
    url = f"https://api.privy.io/v1/wallets/{wallet_id}/rpc"
    body = {
        "method": "signTransaction",
        "params": {"transaction": encoded_tx, "encoding": "base64"},
        "chain_type": "solana",
    }

    # Use SDK's authorization signature helper
    auth_signature = get_authorization_signature(
        url=url,
        body=body,
        method="POST",
        app_id=privy_client.app_id,
        private_key=pkcs8_key,
    )

    # Call the SDK's rpc method for Solana signTransaction
    result = await privy_client.wallets.rpc(
        wallet_id=wallet_id,
        method="signTransaction",
        params={"transaction": encoded_tx, "encoding": "base64"},
        chain_type="solana",
        privy_authorization_signature=auth_signature,
    )

    return {
        "data": {
            "signedTransaction": result.data.signed_transaction if result.data else None
        }
    }


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

    async def execute(  # pragma: no cover
        self,
        user_id: str,
        input_mint: str,
        output_mint: str,
        amount: int,
    ) -> Dict[str, Any]:
        if not all([self.app_id, self.app_secret, self.signing_key]):
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

            wallet_id = wallet_info["wallet_id"]
            public_key = wallet_info["public_key"]

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

            # Sign transaction via Privy using the official SDK
            sign_result = await privy_sign_transaction(
                privy_client,
                wallet_id,
                tx_to_sign,
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
        finally:
            await privy_client.close()


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
