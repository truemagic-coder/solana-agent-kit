import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from solders.pubkey import Pubkey

from sakit.utils.kamino import (
    INIT_REFERRER_STATE_AND_SHORT_URL_DISCRIMINATOR,
    INIT_USER_METADATA_DISCRIMINATOR,
    KAMINO_RESERVE_ACCOUNT_DISCRIMINATOR,
    WITHDRAW_REFERRER_FEES_DISCRIMINATOR,
    build_kamino_create_lookup_table_transaction,
    fetch_kamino_reserve_metadata,
    build_kamino_init_referrer_state_and_short_url_instruction,
    build_kamino_init_user_metadata_instruction,
    build_kamino_init_user_metadata_transaction,
    build_kamino_referrer_setup_transaction,
    build_kamino_withdraw_referrer_fees_instruction,
    build_kamino_withdraw_referrer_fees_transaction,
    derive_kamino_lending_market_authority_pda,
    derive_kamino_referrer_state_pda,
    derive_kamino_referrer_token_state_pda,
    derive_kamino_reserve_liquidity_supply_pda,
    derive_kamino_short_url_pda,
    derive_kamino_user_metadata_pda,
    parse_kamino_reserve_metadata,
    validate_kamino_short_url,
)


WALLET = "11111111111111111111111111111112"
REFERRER = "11111111111111111111111111111113"
MARKET = "11111111111111111111111111111114"
RESERVE = "11111111111111111111111111111115"
MINT = "So11111111111111111111111111111111111111112"
LOOKUP_TABLE = "11111111111111111111111111111116"
PYTH = "11111111111111111111111111111117"
SWITCHBOARD = "11111111111111111111111111111118"
TWAP = "11111111111111111111111111111119"
SCOPE = "1111111111111111111111111111111A"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _build_reserve_account_data() -> bytes:
    data = bytearray(4048)
    data[:8] = KAMINO_RESERVE_ACCOUNT_DISCRIMINATOR
    data[32:64] = bytes(Pubkey.from_string(MARKET))
    data[128:160] = bytes(Pubkey.from_string(MINT))
    data[400:432] = bytes(Pubkey.from_string(TOKEN_PROGRAM))
    data[3904:3936] = bytes(Pubkey.from_string(SCOPE))
    data[3952:3984] = bytes(Pubkey.from_string(SWITCHBOARD))
    data[3984:4016] = bytes(Pubkey.from_string(TWAP))
    data[4016:4048] = bytes(Pubkey.from_string(PYTH))
    return bytes(data)


class TestKaminoReferralInstructionBuilders:
    def test_validate_short_url(self):
        assert validate_kamino_short_url("ref_code-1") is None
        assert validate_kamino_short_url("")
        assert validate_kamino_short_url("bad space")
        assert validate_kamino_short_url("x" * 33)

    def test_init_user_metadata_instruction(self):
        instruction = build_kamino_init_user_metadata_instruction(
            owner=WALLET,
            user_lookup_table=LOOKUP_TABLE,
            referrer=REFERRER,
        )

        assert bytes(instruction.data[:8]) == INIT_USER_METADATA_DISCRIMINATOR
        assert instruction.accounts[0].pubkey == Pubkey.from_string(WALLET)
        assert instruction.accounts[2].pubkey == derive_kamino_user_metadata_pda(WALLET)
        assert instruction.accounts[3].pubkey == derive_kamino_user_metadata_pda(REFERRER)
        assert bytes(instruction.data[8:]) == bytes(Pubkey.from_string(LOOKUP_TABLE))

    def test_init_referrer_state_instruction(self):
        instruction = build_kamino_init_referrer_state_and_short_url_instruction(
            referrer=WALLET,
            short_url="kamino_ref",
        )

        assert bytes(instruction.data[:8]) == INIT_REFERRER_STATE_AND_SHORT_URL_DISCRIMINATOR
        assert instruction.accounts[1].pubkey == derive_kamino_referrer_state_pda(WALLET)
        assert instruction.accounts[2].pubkey == derive_kamino_short_url_pda("kamino_ref")
        assert instruction.accounts[3].pubkey == derive_kamino_user_metadata_pda(WALLET)

    def test_withdraw_referrer_fees_instruction(self):
        referrer_token_account = "1111111111111111111111111111111B"
        instruction = build_kamino_withdraw_referrer_fees_instruction(
            referrer=WALLET,
            lending_market=MARKET,
            reserve=RESERVE,
            reserve_liquidity_mint=MINT,
            referrer_token_account=referrer_token_account,
        )

        assert bytes(instruction.data) == WITHDRAW_REFERRER_FEES_DISCRIMINATOR
        assert instruction.accounts[1].pubkey == derive_kamino_referrer_token_state_pda(WALLET, RESERVE)
        assert instruction.accounts[4].pubkey == derive_kamino_reserve_liquidity_supply_pda(RESERVE)
        assert instruction.accounts[6].pubkey == Pubkey.from_string(MARKET)
        assert instruction.accounts[7].pubkey == derive_kamino_lending_market_authority_pda(MARKET)


class TestKaminoReferralTransactionBuilders:
    def test_parse_reserve_metadata(self):
        metadata = parse_kamino_reserve_metadata(
            reserve=RESERVE,
            account_data=_build_reserve_account_data(),
        )

        assert metadata.lending_market == MARKET
        assert metadata.reserve == RESERVE
        assert metadata.reserve_liquidity_mint == MINT
        assert metadata.token_program_id == TOKEN_PROGRAM
        assert metadata.scope_prices == SCOPE
        assert metadata.switchboard_price_oracle == SWITCHBOARD
        assert metadata.switchboard_twap_oracle == TWAP
        assert metadata.pyth_oracle == PYTH

    @pytest.mark.asyncio
    async def test_fetch_reserve_metadata(self):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.get_account_info = AsyncMock(
            return_value=MagicMock(value=MagicMock(data=_build_reserve_account_data()))
        )

        with patch("sakit.utils.kamino.AsyncClient", return_value=mock_client):
            metadata = await fetch_kamino_reserve_metadata(
                rpc_url="https://rpc.example.com",
                reserve=RESERVE,
            )

        assert metadata.reserve_liquidity_mint == MINT
        assert metadata.token_program_id == TOKEN_PROGRAM

    @pytest.mark.asyncio
    async def test_create_lookup_table_transaction(self):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with (
            patch("sakit.utils.kamino.AsyncClient", return_value=mock_client),
            patch(
                "sakit.utils.kamino._build_create_lookup_table_instruction",
                new=AsyncMock(return_value=(MagicMock(name="create_lut_ix"), Pubkey.from_string(LOOKUP_TABLE))),
            ),
            patch(
                "sakit.utils.kamino._compile_placeholder_transaction",
                new=AsyncMock(return_value={"status": "success", "transaction": "tx-base64"}),
            ) as mock_compile,
        ):
            result = await build_kamino_create_lookup_table_transaction(
                rpc_url="https://rpc.example.com",
                wallet_public_key=WALLET,
            )

        assert result["status"] == "success"
        assert result["user_lookup_table"] == LOOKUP_TABLE
        assert len(mock_compile.await_args.args[2]) == 1

    @pytest.mark.asyncio
    async def test_init_user_metadata_auto_creates_lookup_table(self):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with (
            patch("sakit.utils.kamino.AsyncClient", return_value=mock_client),
            patch("sakit.utils.kamino._account_exists", new=AsyncMock(return_value=False)),
            patch(
                "sakit.utils.kamino._build_create_lookup_table_instruction",
                new=AsyncMock(return_value=(MagicMock(name="create_lut_ix"), Pubkey.from_string(LOOKUP_TABLE))),
            ),
            patch(
                "sakit.utils.kamino._compile_placeholder_transaction",
                new=AsyncMock(return_value={"status": "success", "transaction": "tx-base64"}),
            ) as mock_compile,
        ):
            result = await build_kamino_init_user_metadata_transaction(
                rpc_url="https://rpc.example.com",
                wallet_public_key=WALLET,
            )

        assert result["status"] == "success"
        assert result["user_lookup_table"] == LOOKUP_TABLE
        instructions = mock_compile.await_args.args[2]
        assert len(instructions) == 2
        assert bytes(instructions[1].data[:8]) == INIT_USER_METADATA_DISCRIMINATOR

    @pytest.mark.asyncio
    async def test_referrer_setup_prepends_user_metadata_init(self):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with (
            patch("sakit.utils.kamino.AsyncClient", return_value=mock_client),
            patch("sakit.utils.kamino._account_exists", new=AsyncMock(side_effect=[False, False])),
            patch(
                "sakit.utils.kamino._build_create_lookup_table_instruction",
                new=AsyncMock(return_value=(MagicMock(name="create_lut_ix"), Pubkey.from_string(LOOKUP_TABLE))),
            ),
            patch(
                "sakit.utils.kamino._compile_placeholder_transaction",
                new=AsyncMock(return_value={"status": "success", "transaction": "tx-base64"}),
            ) as mock_compile,
        ):
            result = await build_kamino_referrer_setup_transaction(
                rpc_url="https://rpc.example.com",
                wallet_public_key=WALLET,
                short_url="kamino_ref",
            )

        assert result["status"] == "success"
        assert result["user_lookup_table"] == LOOKUP_TABLE
        instructions = mock_compile.await_args.args[2]
        assert len(instructions) == 3
        assert bytes(instructions[1].data[:8]) == INIT_USER_METADATA_DISCRIMINATOR
        assert bytes(instructions[2].data[:8]) == INIT_REFERRER_STATE_AND_SHORT_URL_DISCRIMINATOR

    @pytest.mark.asyncio
    async def test_withdraw_referrer_fees_prepends_setup_instructions(self):
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with (
            patch("sakit.utils.kamino.AsyncClient", return_value=mock_client),
            patch("sakit.utils.kamino._resolve_token_program_pubkey", new=AsyncMock(return_value=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))),
            patch("sakit.utils.kamino._account_exists", new=AsyncMock(side_effect=[False, False])),
            patch(
                "sakit.utils.kamino._compile_placeholder_transaction",
                new=AsyncMock(return_value={"status": "success", "transaction": "tx-base64"}),
            ) as mock_compile,
        ):
            result = await build_kamino_withdraw_referrer_fees_transaction(
                rpc_url="https://rpc.example.com",
                wallet_public_key=WALLET,
                lending_market=MARKET,
                reserve=RESERVE,
                reserve_liquidity_mint=MINT,
                pyth_oracle=PYTH,
                switchboard_price_oracle=SWITCHBOARD,
                switchboard_twap_oracle=TWAP,
                scope_prices=SCOPE,
            )

        assert result["status"] == "success"
        instructions = mock_compile.await_args.args[2]
        assert len(instructions) == 4
        assert bytes(instructions[1].data[:8]) != b""
        assert bytes(instructions[3].data) == WITHDRAW_REFERRER_FEES_DISCRIMINATOR
