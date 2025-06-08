import logging
import base64
from typing import Optional
import httpx

from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from solders.null_signer import NullSigner
from spl.token.async_client import AsyncToken
from sakit.utils.wallet import SolanaWalletClient

JUP_API = "https://quote-api.jup.ag/v6"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class TradeManager:
    @staticmethod
    async def trade(
        wallet: SolanaWalletClient,
        output_mint: str,
        input_amount: float,
        input_mint: str = None,
        slippage_bps: int = 300,
        jupiter_url: Optional[str] = None,
        no_signer: bool = False,
    ) -> VersionedTransaction:
        """
        Swap tokens using Jupiter Exchange.

        Args:
            wallet: SolanaWalletClient instance.
            output_mint (str): Target token mint address.
            input_amount (float): Amount to swap.
            input_mint (str): Source token mint address (default: SOL).
            slippage_bps (int): Slippage tolerance in basis points (default: 300 = 3%).
            jupiter_url (str): Jupiter API base URL.
            no_signer (bool): If True, does not sign the transaction with the wallet's keypair.

        Returns:
            VersionedTransaction: Signed transaction ready for submission.

        Raises:
            Exception: If the swap fails.
        """
        try:
            if (
                input_mint is None
                or input_mint == "So11111111111111111111111111111111111111112"
            ):
                # Default to SOL
                input_mint = "So11111111111111111111111111111111111111112"
                adjusted_amount = int(input_amount * (10**9))  # SOL has 9 decimals

            else:
                mint_pubkey = Pubkey.from_string(input_mint)
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

                mint_info = await token.get_mint_info()
                adjusted_amount = int(input_amount * (10**mint_info.decimals))

            if jupiter_url is None:
                jupiter_url = JUP_API

            quote_url = (
                f"{jupiter_url}/quote?"
                f"inputMint={input_mint}"
                f"&outputMint={output_mint}"
                f"&amount={adjusted_amount}"
                f"&slippageBps={slippage_bps}"
                f"&onlyDirectRoutes=true"
                f"&maxAccounts=20"
            )

            async with httpx.AsyncClient() as client:
                quote_response = await client.get(quote_url)
                if quote_response.status_code != 200:
                    raise Exception(
                        f"Failed to fetch quote: {quote_response.status_code}"
                    )
                quote_data = quote_response.json()

                swap_response = await client.post(
                    f"{jupiter_url}/swap",
                    json={
                        "quoteResponse": quote_data,
                        "userPublicKey": str(wallet.pubkey),
                        "wrapAndUnwrapSol": True,
                        "dynamicComputeUnitLimit": True,
                        "prioritizationFeeLamports": "auto",
                    },
                )
                if swap_response.status_code != 200:
                    raise Exception(
                        f"Failed to fetch swap transaction: {swap_response.status_code}"
                    )
                swap_data = swap_response.json()

            swap_transaction_buf = base64.b64decode(swap_data["swapTransaction"])
            transaction = VersionedTransaction.from_bytes(swap_transaction_buf)

            if no_signer:
                signature = NullSigner(wallet.pubkey).sign_message(
                    to_bytes_versioned(transaction.message)
                )
                signed_transaction = VersionedTransaction.populate(
                    transaction.message, [signature]
                )
                return signed_transaction

            signature = wallet.sign_message(to_bytes_versioned(transaction.message))
            signed_transaction = VersionedTransaction.populate(
                transaction.message, [signature]
            )

            return signed_transaction

        except Exception as e:
            logging.exception(f"Swap failed: {str(e)}")
            raise Exception(f"Swap failed: {str(e)}")
