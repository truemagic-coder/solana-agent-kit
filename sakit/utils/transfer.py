import logging
from solana.rpc.commitment import Confirmed
from solders.transaction import Transaction  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.message import Message  # type: ignore
from solders.system_program import TransferParams, transfer
from spl.token.async_client import AsyncToken
from sakit.utils.wallet import SolanaWalletClient

LAMPORTS_PER_SOL = 10**9

class TokenTransferManager:
    @staticmethod
    async def transfer(wallet: SolanaWalletClient, to: str, amount: float, mint: str = None) -> str:
        """
        Transfer SOL or SPL tokens to a recipient.

        :param wallet: An instance of SolanaWalletClient
        :param to: Recipient's public key
        :param amount: Amount to transfer
        :param mint: Optional mint address for SPL tokens
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

                signature = await wallet.client.send_transaction(transaction)
                return signature.value

            else:
                mint_pubkey = Pubkey.from_string(mint)
                program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

                token = AsyncToken(wallet.client, mint_pubkey,
                                    program_id, wallet.keypair)

                from_ata = (await token.get_accounts_by_owner(wallet_pubkey)).value[0].pubkey
                to_ata = (await token.get_accounts_by_owner(to_pubkey)).value[0].pubkey

                mint_info = await token.get_mint_info()
                adjusted_amount = int(amount * (10**mint_info.decimals))

                blockhash_response = await wallet.client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash

                sig = await token.transfer_checked(
                    from_ata,
                    to_ata,
                    wallet.keypair.pubkey(),
                    adjusted_amount,
                    mint_info.decimals,
                    None,
                    None,
                    recent_blockhash,
                )
                return sig.value

        except Exception as e:
            logging.error(f"Transfer failed: {str(e)}")
            raise RuntimeError(f"Transfer failed: {str(e)}")
