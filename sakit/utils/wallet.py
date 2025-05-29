from typing import Dict, List, Optional
import nacl.signing
from solana.rpc.api import Client as SolanaClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solders.transaction import Transaction  # type: ignore
from solders.instruction import Instruction  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.message import Message  # type: ignore
from solders.signature import Signature  # type: ignore

class SolanaTransaction:
    """Transaction parameters for Solana."""

    def __init__(
        self,
        instructions: List[Instruction],
        accounts_to_sign: Optional[List[Keypair]] = None
    ):
        self.instructions = instructions
        self.accounts_to_sign = accounts_to_sign


class SolanaWalletClient:
    """Solana wallet implementation."""

    def __init__(self, client: SolanaClient, keypair: Keypair):
        self.client = client
        self.keypair = keypair

    def sign_message(self, message: bytes) -> Signature:
        signed = nacl.signing.SigningKey(
            self.keypair.secret()).sign(message)
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
            opts=TxOpts(skip_preflight=False, max_retries=10,
                        preflight_commitment=Confirmed),
        )
        self.client.confirm_transaction(result.value, commitment=Confirmed)
        return {"hash": str(result.value)}