import logging
import based58
from solana.rpc.commitment import Confirmed
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.message import Message
from solders.compute_budget import set_compute_unit_limit
from solders.system_program import TransferParams, transfer
from spl.token.async_client import AsyncToken
from spl.token.instructions import (
    transfer_checked as spl_transfer,
    TransferCheckedParams as SPLTransferParams,
)
from sakit.utils.wallet import SolanaWalletClient

LAMPORTS_PER_SOL = 10**9
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class TokenTransferManager:
    @staticmethod
    async def transfer(
        wallet: SolanaWalletClient,
        to: str,
        amount: float,
        mint: str = None,
        provider: str = None,
    ) -> str:
        """
        Transfer SOL, SPL, or Token2022 tokens to a recipient.

        :param wallet: An instance of SolanaWalletClient
        :param to: Recipient's public key
        :param amount: Amount to transfer
        :param mint: Optional mint address for SPL tokens
        :param provider: Provider for the transaction, default is None
        :return: transaction signature
        """
        try:
            # Convert to PublicKey objects
            to_pubkey = Pubkey.from_string(to)
            wallet_pubkey = wallet.keypair.pubkey()

            if mint is None:
                # Transfer native SOL
                ix = transfer(
                    TransferParams(
                        from_pubkey=wallet_pubkey,
                        to_pubkey=to_pubkey,
                        lamports=int(amount * LAMPORTS_PER_SOL),
                    )
                )

                blockhash_response = await wallet.client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash

                msg = Message(
                    instructions=[ix],
                    payer=wallet_pubkey,
                )

                transaction = Transaction(
                    from_keypairs=[wallet.keypair],
                    message=msg,
                    recent_blockhash=recent_blockhash,
                )

                cu_units = (
                    await wallet.client.simulate_transaction(
                        transaction, commitment=Confirmed
                    )
                ).value.units_consumed

                compute_budget_ix = set_compute_unit_limit(int(cu_units + 100_000))

                new_msg = Message(
                    instructions=[ix, compute_budget_ix],
                    payer=wallet_pubkey,
                )

                new_transaction = Transaction(
                    from_keypairs=[wallet.keypair],
                    message=new_msg,
                    recent_blockhash=recent_blockhash,
                )

                if provider == "helius":
                    encoded_transaction = based58.b58encode(
                        bytes(new_transaction), based58.Alphabet.DEFAULT
                    ).decode("utf-8")

                    priority_fee = await wallet.get_priority_fee_estimate_helius(
                        encoded_transaction
                    )

                    new_transaction.message.instructions.insert(
                        0,
                        set_compute_unit_limit(priority_fee),
                    )

                signature = await wallet.client.send_transaction(new_transaction)
                return signature.value

            else:
                mint_pubkey = Pubkey.from_string(mint)
                resp = await wallet.client.get_account_info(mint_pubkey)
                owner = str(resp.value.owner)
                if owner == SPL_TOKEN_PROGRAM_ID:
                    program_id = Pubkey.from_string(SPL_TOKEN_PROGRAM_ID)
                elif owner == TOKEN_2022_PROGRAM_ID:
                    program_id = Pubkey.from_string(TOKEN_2022_PROGRAM_ID)
                else:
                    raise ValueError(
                        f"Unsupported token program: {owner}. Supported programs are SPL Token and Token 2022."
                    )

                token = AsyncToken(
                    wallet.client, mint_pubkey, program_id, wallet.keypair
                )

                from_ata = (
                    (await token.get_accounts_by_owner(wallet_pubkey)).value[0].pubkey
                )
                to_ata = (await token.get_accounts_by_owner(to_pubkey)).value[0].pubkey

                mint_info = await token.get_mint_info()
                adjusted_amount = int(amount * (10**mint_info.decimals))

                ix = spl_transfer(
                    SPLTransferParams(
                        program_id=program_id,
                        source=from_ata,
                        mint=mint_pubkey,
                        dest=to_ata,
                        owner=wallet_pubkey,
                        amount=adjusted_amount,
                        decimals=mint_info.decimals,
                    )
                )

                blockhash_response = await wallet.client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash

                msg = Message(
                    instructions=[ix],
                    payer=wallet_pubkey,
                )

                transaction = Transaction(
                    from_keypairs=[wallet.keypair],
                    message=msg,
                    recent_blockhash=recent_blockhash,
                )

                cu_units = (
                    await wallet.client.simulate_transaction(
                        transaction, commitment=Confirmed
                    )
                ).value.units_consumed

                compute_budget_ix = set_compute_unit_limit(int(cu_units + 100_000))

                new_msg = Message(
                    instructions=[ix, compute_budget_ix],
                    payer=wallet_pubkey,
                )

                new_transaction = Transaction(
                    from_keypairs=[wallet.keypair],
                    message=new_msg,
                    recent_blockhash=recent_blockhash,
                )

                if provider == "helius":
                    encoded_transaction = based58.b58encode(
                        bytes(new_transaction), based58.Alphabet.DEFAULT
                    ).decode("utf-8")

                    priority_fee = await wallet.get_priority_fee_estimate_helius(
                        encoded_transaction
                    )

                    new_transaction.message.instructions.insert(
                        0,
                        set_compute_unit_limit(priority_fee),
                    )

                signature = await wallet.client.send_transaction(new_transaction)
                return signature.value

        except Exception as e:
            logging.exception(f"Transfer failed: {str(e)}")
            raise RuntimeError(f"Transfer failed: {str(e)}")
