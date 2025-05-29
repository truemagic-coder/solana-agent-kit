import logging
import base64
import httpx

from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import to_bytes_versioned
from solana.rpc.types import TxOpts
from spl.token.async_client import AsyncToken
from sakit.utils.wallet import SolanaWalletClient

JUP_API = "https://quote-api.jup.ag/v6"

class TradeManager:
    @staticmethod
    async def trade(
        wallet: SolanaWalletClient,
        output_mint: str,
        input_amount: float,
        input_mint: str = None,
        slippage_bps: int = 300,
        jupiter_url: str = JUP_API,
    ) -> str:
        """
        Swap tokens using Jupiter Exchange.

        Args:
            wallet: SolanaWalletClient instance.
            output_mint (str): Target token mint address.
            input_amount (float): Amount to swap.
            input_mint (str): Source token mint address (default: SOL).
            slippage_bps (int): Slippage tolerance in basis points (default: 300 = 3%).
            jupiter_url (str): Jupiter API base URL.

        Returns:
            str: Transaction signature.

        Raises:
            Exception: If the swap fails.
        """
        try:
            if input_mint is None or input_mint == "So11111111111111111111111111111111111111112":
                # Default to SOL
                input_mint = "So11111111111111111111111111111111111111112"
                adjusted_amount = int(input_amount * (10**9))  # SOL has 9 decimals

            else:
                mint_pubkey = Pubkey.from_string(input_mint)
                program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

                token = AsyncToken(wallet.client, mint_pubkey,
                                    program_id, wallet.keypair)
            
                mint_info = await token.get_mint_info()
                adjusted_amount = int(input_amount * (10**mint_info.decimals))

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
                        "userPublicKey": str(wallet.keypair.pubkey()),
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

            signature = wallet.sign_message(to_bytes_versioned(transaction.message))
            signed_transaction = VersionedTransaction.populate(
                transaction.message, [signature])

            tx_resp = await wallet.client.send_transaction(
                signed_transaction,
                opts=TxOpts(preflight_commitment=Confirmed,
                            skip_preflight=False, max_retries=3),
            )
            tx_id = tx_resp.value

            return str(tx_id)

        except Exception as e:
            logging.error(f"Swap failed: {str(e)}")
            raise Exception(f"Swap failed: {str(e)}")