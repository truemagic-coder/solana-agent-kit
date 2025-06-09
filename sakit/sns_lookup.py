from typing import Dict, Any, List, Optional
from solana_agent import AutoTool, ToolRegistry
import httpx

class SnsLookupTool(AutoTool):
    def __init__(self, registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="sns_lookup",
            description="Lookup SNS domain with a QuickNode RPC.",
            registry=registry,
        )
        self.quicknode_url = None

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "SNS domain to resolve, e.g. domain.sol",
                }
            },
            "required": ["domain"],
            "additionalProperties": False,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        super().configure(config)
        tool_cfg = config.get("tools", {}).get("sns_lookup", {})
        self.quicknode_url = tool_cfg.get("quicknode_url")

    async def execute(self, domain: str) -> Dict[str, Any]:
        if not self.quicknode_url:
            return {"status": "error", "message": "No quicknode_url configured for SNS lookup."}
        payload = {
            "method": "sns_resolveDomain",
            "params": [domain],
            "id": 1,
            "jsonrpc": "2.0",
        }
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.quicknode_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {"status": "success", "result": data}

class SnsLookupPlugin:
    def __init__(self):
        self.name = "sns_lookup"
        self.config = None
        self.tool_registry = None
        self._tool = None

    @property
    def description(self):
        return "Plugin for resolving SNS domains using a QuickNode endpoint."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self._tool = SnsLookupTool(registry=tool_registry)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        if self._tool:
            self._tool.configure(self.config)

    def get_tools(self) -> List[AutoTool]:
        return [self._tool] if self._tool else []

def get_plugin():
    return SnsLookupPlugin()