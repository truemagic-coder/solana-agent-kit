import logging
import based58
from solana.rpc.commitment import Confirmed, Finalized
from solders.transaction import Transaction, VersionedTransaction
from solders.pubkey import Pubkey
from solders.message import Message, to_bytes_versioned
from solders.compute_budget import set_compute_unit_limit
from solders.system_program import TransferParams, transfer
from solders.null_signer import NullSigner
from solders.instruction import Instruction
from spl.token.async_client import AsyncToken
from spl.token.instructions import (
    transfer_checked as spl_transfer,
    TransferCheckedParams as SPLTransferParams,
)
from sakit.utils.wallet import SolanaWalletClient

LAMPORTS_PER_SOL = 10**9
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


def make_memo_instruction(memo: str) -> Instruction:
    return Instruction(
        program_id=Pubkey.from_string(MEMO_PROGRAM_ID),
        accounts=[],
        data=memo.encode("utf-8"),
    )

class TokenTransferManager:
    @staticmethod
    async def transfer(
        wallet: SolanaWalletClient,
        to: str,
        amount: float,
        mint: str,
        provider: str = None,
        no_signer: bool = False,
        fee_percentage: float = 0.85,
        memo: str = "",
    ) -> Transaction:
        """
        Transfer SOL, SPL, or Token2022 tokens to a recipient.

        :param wallet: An instance of SolanaWalletClient
        :param to: Recipient's public key
        :param amount: Amount to transfer
        :param mint: Optional mint address for SPL or Token2022 token
        :param provider: Provider for the transaction, default is None
        :param no_signer: If True, doesn't sign the transaction with the wallet's keypair
        :param fee_percentage: Percentage of the transfer amount to be used as a fee (default is 0.85% for SOL transfers)
        :param memo: Optional memo for the transaction
        :return: Transaction object ready for submission
        """
        try:
            # Convert to PublicKey objects
            to_pubkey = Pubkey.from_string(to)
            wallet_pubkey = wallet.pubkey
            wallet_keypair = wallet.keypair

            if mint == "So11111111111111111111111111111111111111112":
                ixs = []
                ix_transfer = transfer(
                    TransferParams(
                        from_pubkey=wallet_pubkey,
                        to_pubkey=to_pubkey,
                        lamports=int(amount * LAMPORTS_PER_SOL),
                    )
                )
                ixs.append(ix_transfer)

                if memo:
                    ix_memo = make_memo_instruction(memo)
                    ixs.append(ix_memo)

                if wallet.fee_payer:
                    ix_fee = transfer(
                        TransferParams(
                            from_pubkey=wallet_pubkey,
                            to_pubkey=wallet.fee_payer.pubkey(),
                            lamports=int(amount * LAMPORTS_PER_SOL * (fee_percentage / 100)),
                        )
                    )
                    ixs.append(ix_fee)

                if no_signer:
                    blockhash_response = await wallet.client.get_latest_blockhash(
                        commitment=Finalized,
                    )
                    recent_blockhash = blockhash_response.value.blockhash
                    msg = Message.new_with_blockhash(
                        instructions=ixs,
                        payer=wallet_pubkey,
                        blockhash=recent_blockhash,
                    )
                    sig = NullSigner(wallet_pubkey).sign_message(
                        to_bytes_versioned(msg)
                    )
                    transaction = VersionedTransaction.populate(
                        message=msg,
                        signatures=[sig],
                    )
                    return transaction

                blockhash_response = await wallet.client.get_latest_blockhash(
                    commitment=Finalized,
                )
                recent_blockhash = blockhash_response.value.blockhash

                msg = Message(
                    instructions=ixs,
                    payer=wallet_pubkey,
                )

                transaction = Transaction(
                    from_keypairs=[wallet_keypair],
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
                    instructions=[*ixs, compute_budget_ix],
                    payer=wallet_pubkey,
                )

                blockhash_response = await wallet.client.get_latest_blockhash(
                    commitment=Finalized,
                )
                recent_blockhash = blockhash_response.value.blockhash

                new_transaction = Transaction(
                    from_keypairs=[wallet_keypair],
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

                return new_transaction

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
                    wallet.client, mint_pubkey, program_id, wallet.fee_payer
                )

                from_ata = (
                    (await token.get_accounts_by_owner(wallet_pubkey)).value[0].pubkey
                )
                to_ata = (await token.get_accounts_by_owner(to_pubkey)).value[0].pubkey

                mint_info = await token.get_mint_info()
                adjusted_amount = int(amount * (10**mint_info.decimals))

                ixs = []
                ix_spl = spl_transfer(
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
                ixs.append(ix_spl)

                if wallet.fee_payer:
                    to_fee_ata = (await token.get_accounts_by_owner(wallet.fee_payer.pubkey())).value[0].pubkey
                    fee_amount = int(amount * (10**mint_info.decimals) * (fee_percentage / 100))
                    ix_fee = spl_transfer(
                        SPLTransferParams(
                            program_id=program_id,
                            source=from_ata,
                            mint=mint_pubkey,
                            dest=to_fee_ata,
                            owner=wallet_pubkey,
                            amount=fee_amount,
                            decimals=mint_info.decimals,
                        )
                    )
                    ixs.append(ix_fee)

                    webhook_fee = transfer(
                        TransferParams(
                            from_pubkey=wallet_pubkey,
                            to_pubkey=wallet.fee_payer.pubkey(),
                            lamports=int(0.0001 * LAMPORTS_PER_SOL),
                        )
                    )
                    ixs.append(webhook_fee)

                if memo:
                    ix_memo = make_memo_instruction(memo)
                    ixs.append(ix_memo)

                if no_signer:
                    blockhash_response = await wallet.client.get_latest_blockhash(
                        commitment=Finalized,
                    )
                    recent_blockhash = blockhash_response.value.blockhash
                    msg = Message.new_with_blockhash(
                        instructions=ixs,
                        payer=wallet_pubkey,
                        blockhash=recent_blockhash,
                    )
                    sig = NullSigner(wallet_pubkey).sign_message(
                        to_bytes_versioned(msg)
                    )
                    transaction = VersionedTransaction.populate(
                        message=msg,
                        signatures=[sig],
                    )
                    return transaction

                blockhash_response = await wallet.client.get_latest_blockhash(
                    commitment=Finalized,
                )
                recent_blockhash = blockhash_response.value.blockhash

                msg = Message(
                    instructions=ixs,
                    payer=wallet_pubkey,
                )

                transaction = Transaction(
                    from_keypairs=[wallet_keypair],
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
                    instructions=[*ixs, compute_budget_ix],
                    payer=wallet_pubkey,
                )

                blockhash_response = await wallet.client.get_latest_blockhash(
                    commitment=Finalized,
                )
                recent_blockhash = blockhash_response.value.blockhash

                new_transaction = Transaction(
                    from_keypairs=[wallet_keypair],
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
                return new_transaction

        except Exception as e:
            logging.exception(f"Transfer failed: {str(e)}")
            raise RuntimeError(f"Transfer failed: {str(e)}")
