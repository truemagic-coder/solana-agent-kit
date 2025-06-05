from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
from solders.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from sakit.utils.wallet import SolanaWalletClient
from sakit.utils.swap import TradeManager


class SolanaTradeTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="solana_swap",
            description="Swap tokens using Jupiter Exchange on Solana.",
            registry=registry,
        )
        self._rpc_url: Optional[str] = None
        self._jupiter_url: Optional[str] = None
        self._private_key: Optional[str] = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
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
                    "description": "The mint address of the token to swap from. If not provided, defaults to SOL.",
                },
            },
            "required": ["output_mint", "input_amount", "input_mint"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("solana_swap", {})
        self._rpc_url = tool_cfg.get("rpc_url")
        self._jupiter_url = tool_cfg.get("jupiter_url", "https://quote-api.jup.ag/v6")
        self._private_key = tool_cfg.get("private_key")

    async def execute(
        self,
        output_mint: str,
        input_amount: float,
        input_mint: Optional[str] = None,
        slippage_bps: int = 300,
    ) -> Dict[str, Any]:
        if not self._rpc_url or not self._jupiter_url:
            return {"status": "error", "message": "RPC or Jupiter URL not configured."}
        if not self._private_key:
            return {"status": "error", "message": "Private key not configured."}
        keypair = Keypair.from_base58_string(self._private_key)
        wallet = SolanaWalletClient(self._rpc_url, keypair)
        try:
            transaction = await TradeManager.trade(
                wallet,
                output_mint,
                input_amount,
                input_mint,
                slippage_bps,
                jupiter_url=self._jupiter_url,
            )
            tx_resp = await wallet.client.send_transaction(
                transaction,
                opts=TxOpts(
                    preflight_commitment=Confirmed, skip_preflight=False, max_retries=3
                ),
            )
            tx_id = tx_resp.value
            sig = str(tx_id)

            return {"status": "success", "signature": sig}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class SolanaTradePlugin:
    def __init__(self):
        self.name = "solana_swap"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for swapping tokens using Jupiter Exchange."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = SolanaTradeTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []


def get_plugin():
    return SolanaTradePlugin()
