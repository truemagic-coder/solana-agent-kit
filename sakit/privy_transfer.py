import base64
import logging
from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
from privy import AsyncPrivyAPI
from privy.lib.authorization_signatures import get_authorization_signature
from cryptography.hazmat.primitives import serialization
from sakit.utils.wallet import SolanaWalletClient
from sakit.utils.transfer import TokenTransferManager

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 10**9
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


def _convert_key_to_pkcs8_pem(key_string: str) -> str:  # pragma: no cover
    """Convert a private key to PKCS#8 PEM format for the Privy SDK."""
    private_key_string = key_string.replace("wallet-auth:", "")

    # Try loading as PKCS#8 PEM format first
    try:
        private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_string}\n-----END PRIVATE KEY-----"
        serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        return private_key_string
    except (ValueError, TypeError):
        pass

    # Try as EC PRIVATE KEY (SEC1) format
    try:
        ec_key_pem = f"-----BEGIN EC PRIVATE KEY-----\n{private_key_string}\n-----END EC PRIVATE KEY-----"
        private_key = serialization.load_pem_private_key(
            ec_key_pem.encode("utf-8"), password=None
        )
        pkcs8_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pkcs8_pem = pkcs8_bytes.decode("utf-8")
        lines = pkcs8_pem.strip().split("\n")
        return "".join(lines[1:-1])
    except (ValueError, TypeError):
        pass

    # Try loading as raw DER bytes
    try:
        der_bytes = base64.b64decode(private_key_string)
        try:
            private_key = serialization.load_der_private_key(der_bytes, password=None)
        except (ValueError, TypeError):
            from cryptography.hazmat.primitives.asymmetric import ec

            private_key = ec.derive_private_key(
                int.from_bytes(der_bytes, "big"), ec.SECP256R1()
            )
        pkcs8_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pkcs8_pem = pkcs8_bytes.decode("utf-8")
        lines = pkcs8_pem.strip().split("\n")
        return "".join(lines[1:-1])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Could not load private key: {e}")


async def get_privy_embedded_wallet(  # pragma: no cover
    user_id: str, privy_client: AsyncPrivyAPI
) -> Optional[Dict[str, str]]:
    """Get Privy embedded wallet info for a user.

    Supports both:
    - App-first wallets (SDK-created): connector_type == "embedded" with delegated == True
    - Bot-first wallets (API-created): type == "wallet" with chain_type == "solana"
    """
    try:
        user = await privy_client.users.get(user_id)
        data = user.model_dump() if hasattr(user, "model_dump") else user.__dict__

        # First, try to find embedded wallet with delegation
        for acct in data.get("linked_accounts", []):
            if acct.get("connector_type") == "embedded" and acct.get("delegated"):
                wallet_id = acct.get("id")
                # Use 'address' field if 'public_key' is null (common for API-created wallets)
                address = acct.get("address") or acct.get("public_key")
                if wallet_id and address:
                    return {"wallet_id": wallet_id, "public_key": address}

        # Then, try to find bot-first wallet (API-created via privy_create_wallet)
        # These have type == "wallet" and include chain_type
        for acct in data.get("linked_accounts", []):
            acct_type = acct.get("type", "")
            # Check for Solana embedded wallets created via API
            if acct_type == "wallet" and acct.get("chain_type") == "solana":
                wallet_id = acct.get("id")
                # API wallets use "address" field, SDK wallets use "public_key"
                address = acct.get("address") or acct.get("public_key")
                if wallet_id and address:
                    return {"wallet_id": wallet_id, "public_key": address}
            # Also check for solana_embedded_wallet type
            if "solana" in acct_type.lower() and "embedded" in acct_type.lower():
                wallet_id = acct.get("id")
                address = acct.get("address") or acct.get("public_key")
                if wallet_id and address:
                    return {"wallet_id": wallet_id, "public_key": address}

        return None
    except Exception as e:
        logger.error(f"Error getting Privy embedded wallet: {e}")
        return None


async def privy_sign_and_send(  # pragma: no cover
    wallet_id: str, encoded_tx: str, privy_client: AsyncPrivyAPI, privy_auth_key: str
) -> Dict[str, Any]:
    """Sign and send a transaction using Privy SDK."""
    try:
        # Convert key to PKCS#8 PEM format for SDK compatibility
        pem_key = _convert_key_to_pkcs8_pem(privy_auth_key)

        # IMPORTANT: The body must match exactly what the SDK sends to the API
        # signAndSendTransaction requires caip2 for Solana
        url = f"https://api.privy.io/v1/wallets/{wallet_id}/rpc"
        body = {
            "method": "signAndSendTransaction",
            "params": {"transaction": encoded_tx, "encoding": "base64"},
            "caip2": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            "chain_type": "solana",
        }
        auth_signature = get_authorization_signature(
            url=url,
            body=body,
            method="POST",
            app_id=privy_client.app_id,
            private_key=pem_key,
        )

        # Use SDK's wallets.rpc method for signAndSendTransaction
        result = await privy_client.wallets.rpc(
            wallet_id=wallet_id,
            method="signAndSendTransaction",
            params={"transaction": encoded_tx, "encoding": "base64"},
            caip2="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            chain_type="solana",
            privy_authorization_signature=auth_signature,
        )

        return (
            result.model_dump() if hasattr(result, "model_dump") else {"data": result}
        )
    except Exception as e:
        logger.error(f"Privy sign and send failed: {e}")
        raise


class PrivyTransferTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_transfer",
            description="Transfer SOL or SPL tokens using Privy delegated wallet.",
            registry=registry,
        )
        self.app_id = None
        self.app_secret = None
        self.signing_key = None
        self.rpc_url = None
        self.fee_payer = None
        self.fee_percentage = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Privy user id (did)"},
                "to_address": {
                    "type": "string",
                    "description": "Recipient wallet address",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to transfer (in SOL or token units)",
                },
                "mint": {
                    "type": "string",
                    "description": "Token mint address",
                },
                "memo": {
                    "type": "string",
                    "description": "Optional memo for the transaction",
                    "default": "",
                },
            },
            "required": ["user_id", "to_address", "amount", "mint", "memo"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        tool_cfg = config.get("tools", {}).get("privy_transfer", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")
        self.signing_key = tool_cfg.get("signing_key")
        self.rpc_url = tool_cfg.get("rpc_url")
        self.fee_payer = tool_cfg.get("fee_payer")
        self.fee_percentage = tool_cfg.get("fee_percentage", 0.85)  # Default 0.85% fee

    async def execute(
        self,
        user_id: str,
        to_address: str,
        amount: float,
        mint: str,
        memo: str = "",
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

        # Create SDK client
        privy_client = AsyncPrivyAPI(
            app_id=self.app_id,
            app_secret=self.app_secret,
        )

        wallet_info = await get_privy_embedded_wallet(user_id, privy_client)
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
            if "helius" in self.rpc_url:  # pragma: no cover
                provider = "helius"
            transaction = await TokenTransferManager.transfer(
                wallet,
                to_address,
                amount,
                mint,
                provider,
                True,
                self.fee_percentage,
                memo,
            )
            encoded_transaction = base64.b64encode(bytes(transaction)).decode("utf-8")
            result = await privy_sign_and_send(
                wallet_id,
                encoded_transaction,
                privy_client,
                self.signing_key,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            logger.exception(f"Privy transfer failed: {str(e)}")
            return {"status": "error", "message": str(e)}


class PrivyTransferPlugin:
    def __init__(self):
        self.name = "privy_transfer"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for transferring SOL or SPL tokens using Privy delegated wallet."

    def initialize(self, tool_registry: ToolRegistry) -> None:  # pragma: no cover
        self.tool_registry = tool_registry
        self._tool = PrivyTransferTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:  # pragma: no cover
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:  # pragma: no cover
        return [self._tool] if self._tool else []


def get_plugin():  # pragma: no cover
    return PrivyTransferPlugin()
