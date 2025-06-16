from typing import Dict, List, Optional
import httpx
import nacl.signing
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solders.transaction import Transaction
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.signature import Signature
from solders.pubkey import Pubkey


class SolanaTransaction:
    """Transaction parameters for Solana."""

    def __init__(
        self,
        instructions: List[Instruction],
        accounts_to_sign: Optional[List[Keypair]] = None,
    ):
        self.instructions = instructions
        self.accounts_to_sign = accounts_to_sign


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
        if pubkey:
            self.pubkey = Pubkey.from_string(pubkey)
        elif keypair:
            self.pubkey = keypair.pubkey()
        if fee_payer:
            self.fee_payer = Keypair.from_base58_string(fee_payer)

    def sign_message(self, message: bytes) -> Signature:
        signed = nacl.signing.SigningKey(self.keypair.secret()).sign(message)
        return Signature.from_bytes(signed.signature)

    def send_transaction(self, transaction: SolanaTransaction) -> Dict[str, str]:
        recent_blockhash = self.client.get_latest_blockhash().value.blockhash
        payer = self.keypair.pubkey()

        ixs = []
        for instruction in transaction.instructions:
            ixs.append(instruction)

        signers = [self.keypair]
        if transaction.accounts_to_sign:
            signers.extend(transaction.accounts_to_sign)

        message = Message(
            instructions=ixs,
            recent_blockhash=recent_blockhash,
            payer=payer,
        )
        tx = Transaction(
            from_keypairs=signers,
            message=message,
            recent_blockhash=recent_blockhash,
        )
        result = self.client.send_transaction(
            tx,
            opts=TxOpts(
                skip_preflight=False, max_retries=10, preflight_commitment=Confirmed
            ),
        )
        self.client.confirm_transaction(result.value, commitment=Confirmed)
        return {"hash": str(result.value)}

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
