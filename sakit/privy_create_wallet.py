"""
Privy Create Wallet Tool.

Creates a new Solana wallet for a Privy user with optional additional signers.
Used for bot-first Telegram bot flows where wallets are created server-side.
"""

import base64
import logging
from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx


async def create_privy_wallet(  # pragma: no cover
    user_id: str,
    app_id: str,
    app_secret: str,
    chain_type: str = "solana",
    signer_id: Optional[str] = None,
    policy_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a new wallet for a Privy user.

    Args:
        user_id: The Privy user ID (did:privy:...)
        app_id: Privy app ID
        app_secret: Privy app secret
        chain_type: The chain type (solana, ethereum, etc.)
        signer_id: Optional key quorum ID to add as additional signer
        policy_ids: Optional list of policy IDs to apply to the signer

    Returns:
        Dict with wallet data including id, address, chain_type
    """
    url = "https://api.privy.io/v1/wallets"
    auth_string = f"{app_id}:{app_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "privy-app-id": app_id,
        "Content-Type": "application/json",
    }

    body: Dict[str, Any] = {
        "chain_type": chain_type,
        "owner": {"user_id": user_id},
    }

    # Add additional signer if provided (for bot delegation)
    if signer_id:
        body["additional_signers"] = [
            {
                "signer_id": signer_id,
                "override_policy_ids": policy_ids or [],
            }
        ]

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code != 200:
            logging.error(f"Privy create wallet error: {resp.text}")
            resp.raise_for_status()
        return resp.json()


class PrivyCreateWalletTool(AutoTool):
    """Tool for creating a new Solana wallet for a Privy user."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="privy_create_wallet",
            description="Create a new Solana wallet for a Privy user with optional bot delegation. Used for bot-first Telegram bot flows.",
            registry=registry,
        )
        self.app_id = None
        self.app_secret = None
        self.signer_id = None
        self.policy_ids = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The Privy user ID (did:privy:...) to create a wallet for.",
                },
                "chain_type": {
                    "type": "string",
                    "description": "The blockchain type. Defaults to 'solana'.",
                    "enum": ["solana", "ethereum"],
                    "default": "solana",
                },
                "add_bot_signer": {
                    "type": "boolean",
                    "description": "Whether to add the bot as an additional signer for delegation. Defaults to true.",
                    "default": True,
                },
            },
            "required": ["user_id", "chain_type", "add_bot_signer"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        tool_cfg = config.get("tools", {}).get("privy_create_wallet", {})
        self.app_id = tool_cfg.get("app_id")
        self.app_secret = tool_cfg.get("app_secret")
        self.signer_id = tool_cfg.get("signer_id")  # Key quorum ID for bot
        self.policy_ids = tool_cfg.get("policy_ids", [])  # Optional policies

    async def execute(
        self,
        user_id: str,
        chain_type: str = "solana",
        add_bot_signer: bool = True,
    ) -> Dict[str, Any]:
        if not all([self.app_id, self.app_secret]):
            return {
                "status": "error",
                "message": "Privy config missing (app_id, app_secret).",
            }

        # Only require signer_id if add_bot_signer is True
        if add_bot_signer and not self.signer_id:
            return {
                "status": "error",
                "message": "Privy config missing signer_id for bot delegation.",
            }

        try:
            signer = self.signer_id if add_bot_signer else None
            policies = self.policy_ids if add_bot_signer else None

            wallet_data = await create_privy_wallet(
                user_id=user_id,
                app_id=self.app_id,
                app_secret=self.app_secret,
                chain_type=chain_type,
                signer_id=signer,
                policy_ids=policies,
            )
            return {
                "status": "success",
                "result": {
                    "wallet_id": wallet_data.get("id"),
                    "address": wallet_data.get("address"),
                    "chain_type": wallet_data.get("chain_type"),
                    "created_at": wallet_data.get("created_at"),
                    "owner_id": wallet_data.get("owner_id"),
                    "additional_signers": wallet_data.get("additional_signers", []),
                },
            }
        except httpx.HTTPStatusError as e:  # pragma: no cover
            logging.exception(f"Privy create wallet failed: {str(e)}")
            return {
                "status": "error",
                "message": f"HTTP error: {e.response.status_code} - {e.response.text}",
            }
        except Exception as e:  # pragma: no cover
            logging.exception(f"Privy create wallet failed: {str(e)}")
            return {"status": "error", "message": str(e)}


class PrivyCreateWalletPlugin:
    """Plugin for creating Privy wallets with bot delegation."""

    def __init__(self):
        self.name = "privy_create_wallet"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for creating Solana wallets for Privy users with optional bot delegation."

    def initialize(self, tool_registry: ToolRegistry) -> None:  # pragma: no cover
        self.tool_registry = tool_registry
        self._tool = PrivyCreateWalletTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:  # pragma: no cover
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:  # pragma: no cover
        return [self._tool] if self._tool else []


def get_plugin():  # pragma: no cover
    return PrivyCreateWalletPlugin()
