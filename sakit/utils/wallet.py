from typing import Optional
import httpx
import nacl.signing
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.signature import Signature
from solders.pubkey import Pubkey


class SolanaWalletClient:
    """Solana wallet implementation."""

    def __init__(
        self,
        rpc_url: str,
        keypair: Optional[Keypair] = None,
        pubkey: Optional[str] = None,
        fee_payer: Optional[str] = None,
    ):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        self.keypair = keypair
        self.pubkey = pubkey
        self.fee_payer = None
        if pubkey:
            self.pubkey = Pubkey.from_string(pubkey)
        elif keypair:
            self.pubkey = keypair.pubkey()
        if fee_payer:
            self.fee_payer = Keypair.from_base58_string(fee_payer)

    def sign_message(self, message: bytes) -> Signature:
        signed = nacl.signing.SigningKey(self.keypair.secret()).sign(message)
        return Signature.from_bytes(signed.signature)

    async def get_priority_fee_estimate_helius(
        self,
        serialized_transaction: str,
    ) -> int:
        """
        Get the priority fee estimate from Helius.

        :param serialized_transaction: The base64-encoded serialized transaction.
        :return: The estimated priority fee (int).
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getPriorityFeeEstimate",
            "params": [
                {
                    "transaction": serialized_transaction,
                    "options": {"recommended": True},
                }
            ],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Fee estimation failed: {result['error']}")
            return int(result["result"]["priorityFeeEstimate"])
