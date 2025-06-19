import logging
import base64
from typing import Optional, List
import httpx

from solders.pubkey import Pubkey
from solana.rpc.commitment import Finalized
from solders.transaction import VersionedTransaction
from solders.message import (
    to_bytes_versioned,
    MessageV0,
)
from spl.token.instructions import (
    transfer_checked as spl_transfer,
    TransferCheckedParams as SPLTransferParams,
)
from solders.address_lookup_table_account import AddressLookupTableAccount
from solders.null_signer import NullSigner
from solders.instruction import Instruction, AccountMeta
from solders.system_program import TransferParams, transfer
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.signature import Signature
from sakit.utils.wallet import SolanaWalletClient

JUP_API = "https://quote-api.jup.ag/v6"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
LAMPORTS_PER_SOL = 10**9

class TradeManager:
    @staticmethod
    def parse_address_table_lookups(addresses):
        if not addresses:
            return []
        if isinstance(addresses, str):
            addresses = [addresses]
        # Use empty addresses for simulation/compilation
        return [AddressLookupTableAccount(Pubkey.from_string(addr), []) for addr in addresses]

    @staticmethod
    def parse_instruction(ix_obj) -> Instruction:
        program_id = Pubkey.from_string(ix_obj["programId"])
        accounts = [
            AccountMeta(
                pubkey=Pubkey.from_string(acc["pubkey"]),
                is_signer=acc["isSigner"],
                is_writable=acc["isWritable"],
            )
            for acc in ix_obj["accounts"]
        ]
        data = base64.b64decode(ix_obj["data"])
        return Instruction(program_id=program_id, accounts=accounts, data=data)

    @staticmethod
    def parse_instruction_list(ix_list) -> List[Instruction]:
        return [TradeManager.parse_instruction(ix) for ix in ix_list]

    @staticmethod
    async def trade(
        wallet: SolanaWalletClient,
        output_mint: str,
        input_amount: float,
        input_mint: str = None,
        slippage_bps: int = 300,
        jupiter_url: Optional[str] = None,
        no_signer: bool = False,
        provider: Optional[str] = None,
        fee_percentage: float = 0.85,
    ) -> VersionedTransaction:
        """
        Swap tokens using Jupiter Exchange, with compute budget and optional priority fee (if provider == 'helius').
        """
        try:
            if input_mint == "So11111111111111111111111111111111111111112":
                adjusted_amount = int(input_amount * LAMPORTS_PER_SOL)
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
                from spl.token.async_client import AsyncToken
                token = AsyncToken(wallet.client, mint_pubkey, program_id, wallet.fee_payer)
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

                swap_instructions_response = await client.post(
                    f"{jupiter_url}/swap-instructions",
                    json={
                        "quoteResponse": quote_data,
                        "userPublicKey": str(wallet.pubkey),
                        "wrapAndUnwrapSol": True,
                        "dynamicComputeUnitLimit": True,
                        "prioritizationFeeLamports": "auto",
                    },
                )
                if swap_instructions_response.status_code != 200:
                    raise Exception(
                        f"Failed to fetch swap instructions: {swap_instructions_response.status_code}"
                    )
                swap_instructions_data = swap_instructions_response.json()

            # Build all instructions in order
            instructions = []

            # 1. Compute budget instructions (if present)
            has_cu = (
                "computeBudgetInstructions" in swap_instructions_data
                and swap_instructions_data["computeBudgetInstructions"]
            )
            if has_cu:
                instructions += TradeManager.parse_instruction_list(swap_instructions_data["computeBudgetInstructions"])

            # 2. Setup instructions (if present)
            if "setupInstructions" in swap_instructions_data and swap_instructions_data["setupInstructions"]:
                instructions += TradeManager.parse_instruction_list(swap_instructions_data["setupInstructions"])

            # 3. Fee instruction (if wallet.fee_payer)
            if wallet.fee_payer:
                if input_mint == "So11111111111111111111111111111111111111112":
                    ix_fee = transfer(
                        TransferParams(
                            from_pubkey=wallet.pubkey,
                            to_pubkey=wallet.fee_payer.pubkey(),
                            lamports=int(input_amount * LAMPORTS_PER_SOL * (fee_percentage / 100)),
                        )
                    )
                    instructions.append(ix_fee)
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

                    from_ata = (
                        (await token.get_accounts_by_owner(wallet.pubkey)).value[0].pubkey
                    )
                    mint_info = await token.get_mint_info()
                    adjusted_amount = int(input_amount * (10**mint_info.decimals))

                    to_fee_ata = (await token.get_accounts_by_owner(wallet.fee_payer.pubkey())).value[0].pubkey
                    fee_amount = int(adjusted_amount * (fee_percentage / 100))
                    ix_fee = spl_transfer(
                        SPLTransferParams(
                            program_id=program_id,
                            source=from_ata,
                            mint=mint_pubkey,
                            dest=to_fee_ata,
                            owner=wallet.pubkey,
                            amount=fee_amount,
                            decimals=mint_info.decimals,
                        )
                    )
                    instructions.append(ix_fee)

                    webhook_fee = transfer(
                        TransferParams(
                            from_pubkey=wallet.pubkey,
                            to_pubkey=wallet.fee_payer.pubkey(),
                            lamports=int(0.0001 * LAMPORTS_PER_SOL),
                        )
                    )
                    instructions.append(webhook_fee)

            # 4. Swap instruction (required)
            swap_instruction = TradeManager.parse_instruction(swap_instructions_data["swapInstruction"])
            instructions.append(swap_instruction)

            # 5. Cleanup instruction (if present)
            if "cleanupInstruction" in swap_instructions_data and swap_instructions_data["cleanupInstruction"]:
                instructions.append(TradeManager.parse_instruction(swap_instructions_data["cleanupInstruction"]))

            # 6. Other instructions (if present)
            if "otherInstructions" in swap_instructions_data and swap_instructions_data["otherInstructions"]:
                instructions += TradeManager.parse_instruction_list(swap_instructions_data["otherInstructions"])

            # Address lookup tables
            address_table_lookups = TradeManager.parse_address_table_lookups(
                swap_instructions_data.get("addressLookupTableAddresses", [])
            )

            # Simulate to estimate compute units (only if Jupiter did NOT provide CU instructions)
            if not has_cu:
                blockhash_response = await wallet.client.get_latest_blockhash(commitment=Finalized)
                recent_blockhash = blockhash_response.value.blockhash

                msg = MessageV0.try_compile(
                    wallet.pubkey,
                    instructions,
                    [],
                    recent_blockhash,
                )
                transaction = VersionedTransaction.populate(msg, [Signature.default()])
                cu_units = (
                    await wallet.client.simulate_transaction(
                        transaction, sig_verify=False
                    )
                ).value.units_consumed or 1_400_000

                compute_budget_ix = set_compute_unit_limit(int(cu_units + 100_000))

                # Priority fee (helius)
                priority_fee_ix = None
                if provider == "helius":
                    priority_fee = swap_instructions_data.get("prioritizationFeeLamports", 0)
                    if priority_fee and priority_fee > 0:
                        priority_fee_ix = set_compute_unit_price(priority_fee)

                # Insert compute budget and priority fee at the start
                instructions_with_cu = [compute_budget_ix]
                if priority_fee_ix:
                    instructions_with_cu.append(priority_fee_ix)
                instructions_with_cu += instructions
            else:
                instructions_with_cu = instructions

            # Re-compile with compute budget and priority fee, now with address_table_lookups
            blockhash_response = await wallet.client.get_latest_blockhash(commitment=Finalized)
            recent_blockhash = blockhash_response.value.blockhash

            msg_final = MessageV0.try_compile(
                wallet.pubkey,
                instructions_with_cu,
                address_table_lookups,
                recent_blockhash,
            )

            # Sign and return the transaction
            if no_signer:
                signature = NullSigner(wallet.pubkey).sign_message(to_bytes_versioned(msg_final))
                signed_transaction = VersionedTransaction.populate(msg_final, [signature])
                return signed_transaction

            signature = wallet.sign_message(to_bytes_versioned(msg_final))
            signed_transaction = VersionedTransaction.populate(msg_final, [signature])
            return signed_transaction

        except Exception as e:
            logging.exception(f"Swap failed: {str(e)}")
            raise Exception(f"Swap failed: {str(e)}")