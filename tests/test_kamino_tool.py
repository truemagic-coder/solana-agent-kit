"""Tests for the Kamino tool."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.transaction import VersionedTransaction

from sakit.kamino import KaminoPlugin, KaminoTool, get_plugin


def _make_unsigned_transaction_base64(signer: Keypair) -> str:
    message = MessageV0.try_compile(
        payer=signer.pubkey(),
        instructions=[],
        address_lookup_table_accounts=[],
        recent_blockhash=Hash.default(),
    )
    unsigned_transaction = VersionedTransaction.populate(
        message,
        [signer.sign_message(bytes(message))],
    )
    return base64.b64encode(bytes(unsigned_transaction)).decode("utf-8")


@pytest.fixture
def kamino_tool():
    referrer_signer = Keypair()
    tool = KaminoTool()
    tool.configure(
        {
            "tools": {
                "kamino": {
                    "private_key": "5jGR...base58privatekey",
                    "rpc_url": "https://mainnet.helius-rpc.com/?api-key=test-key",
                    "referrer_private_key": str(referrer_signer),
                }
            }
        }
    )
    return tool


class TestKaminoToolSchema:
    def test_tool_name(self, kamino_tool):
        assert kamino_tool.name == "kamino"

    def test_schema_has_key_actions(self, kamino_tool):
        schema = kamino_tool.get_schema()
        assert "borrow_deposit" in schema["properties"]["action"]["enum"]
        assert "api_post" in schema["properties"]["action"]["enum"]
        assert "setup_referrer" not in schema["properties"]["action"]["enum"]
        assert "withdraw_referrer_fees" not in schema["properties"]["action"]["enum"]


class TestKaminoToolExecute:
    @pytest.mark.asyncio
    async def test_missing_private_key_for_transaction_action(self):
        tool = KaminoTool()
        tool.configure({"tools": {"kamino": {"rpc_url": "https://rpc.example.com"}}})

        result = await tool.execute(action="earn_deposit", kvault="vault", amount="1.0")

        assert result["status"] == "error"
        assert "private" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_vaults_success(self, kamino_tool):
        with patch("sakit.kamino.KaminoAPI") as MockKamino:
            mock_api = MagicMock()
            mock_api.list_vaults = AsyncMock(return_value={"success": True, "data": [{"vault": "A"}]})
            MockKamino.return_value = mock_api

            result = await kamino_tool.execute(action="list_vaults")

        assert result["status"] == "success"
        assert result["action"] == "list_vaults"
        assert result["data"][0]["vault"] == "A"

    @pytest.mark.asyncio
    async def test_user_obligations_requires_market_and_user(self, kamino_tool):
        result = await kamino_tool.execute(action="user_obligations", market="", user_pubkey="")

        assert result["status"] == "error"
        assert "market" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_api_get_invalid_params_json(self, kamino_tool):
        result = await kamino_tool.execute(
            action="api_get",
            path="/oracles/prices",
            params_json="[]",
        )

        assert result["status"] == "error"
        assert "json object" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_borrow_deposit_success(self, kamino_tool):
        signer = Keypair()
        transaction_base64 = _make_unsigned_transaction_base64(signer)

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch("sakit.kamino.KaminoAPI") as MockKamino,
            patch("sakit.kamino.get_fresh_blockhash", new_callable=AsyncMock) as mock_blockhash,
            patch("sakit.kamino.send_raw_transaction_with_priority", new_callable=AsyncMock) as mock_send,
            patch("sakit.kamino.replace_blockhash_in_transaction") as mock_replace,
        ):
            MockKeypair.from_base58_string.return_value = signer
            mock_api = MagicMock()
            mock_api.build_borrow_deposit = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction=transaction_base64,
                    request_id="req-1",
                    raw_response={"transaction": transaction_base64},
                )
            )
            MockKamino.return_value = mock_api
            mock_blockhash.return_value = {"blockhash": str(Hash.default())}
            mock_replace.return_value = transaction_base64
            mock_send.return_value = {"success": True, "signature": "sig-123"}

            result = await kamino_tool.execute(
                action="borrow_deposit",
                market="market-1",
                reserve="reserve-1",
                amount="2.0",
                referrer="referrer-wallet",
                referral_code="ref-abc",
            )

        assert result["status"] == "success"
        assert result["signature"] == "sig-123"
        assert result["request_id"] == "req-1"
        assert result["referrer"] == "referrer-wallet"
        assert result["referral_code"] == "ref-abc"

        call = mock_api.build_borrow_deposit.await_args
        assert call.kwargs["referrer"] == "referrer-wallet"
        assert call.kwargs["referral_code"] == "ref-abc"

    @pytest.mark.asyncio
    async def test_borrow_deposit_uses_config_referral_defaults(self, kamino_tool):
        signer = Keypair()
        transaction_base64 = _make_unsigned_transaction_base64(signer)

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch("sakit.kamino.KaminoAPI") as MockKamino,
            patch("sakit.kamino.get_fresh_blockhash", new_callable=AsyncMock) as mock_blockhash,
            patch("sakit.kamino.send_raw_transaction_with_priority", new_callable=AsyncMock) as mock_send,
            patch("sakit.kamino.replace_blockhash_in_transaction") as mock_replace,
        ):
            MockKeypair.from_base58_string.return_value = signer
            mock_api = MagicMock()
            mock_api.build_borrow_deposit = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction=transaction_base64,
                    request_id="req-defaults",
                    raw_response={"transaction": transaction_base64},
                )
            )
            MockKamino.return_value = mock_api
            mock_blockhash.return_value = {"blockhash": str(Hash.default())}
            mock_replace.return_value = transaction_base64
            mock_send.return_value = {"success": True, "signature": "sig-defaults"}

            result = await kamino_tool.execute(
                action="borrow_deposit",
                market="market-1",
                reserve="reserve-1",
                amount="2.0",
            )

        assert result["status"] == "success"
        assert result["referrer"] == kamino_tool._managed_referrer
        assert result["referral_code"] is None
        call = mock_api.build_borrow_deposit.await_args
        assert call.kwargs["referrer"] == result["referrer"]
        assert call.kwargs["referral_code"] is None

    @pytest.mark.asyncio
    async def test_transaction_action_bubbles_kamino_error(self, kamino_tool):
        signer = Keypair()

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch("sakit.kamino.KaminoAPI") as MockKamino,
        ):
            MockKeypair.from_base58_string.return_value = signer
            mock_api = MagicMock()
            mock_api.build_earn_deposit = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    transaction=None,
                    error="kamino rejected request",
                    raw_response={},
                )
            )
            MockKamino.return_value = mock_api

            result = await kamino_tool.execute(
                action="earn_deposit",
                kvault="vault-1",
                amount="1.0",
            )

        assert result["status"] == "error"
        assert "kamino rejected request" in result["message"]

    @pytest.mark.asyncio
    async def test_setup_referrer_success(self, kamino_tool):
        signer = Keypair()

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch(
                "sakit.kamino.build_kamino_referrer_setup_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "referrer_state": "state-1",
                        "referrer_short_url": "short-1",
                    }
                ),
            ) as mock_setup,
            patch.object(kamino_tool, "_sign_and_send", new=AsyncMock(return_value={"status": "success", "signature": "sig-setup"})),
        ):
            MockKeypair.from_base58_string.return_value = signer

            result = await kamino_tool.execute(
                action="setup_referrer",
                short_url="kamino_ref",
                user_lookup_table="11111111111111111111111111111116",
            )

        assert result["status"] == "success"
        assert result["signature"] == "sig-setup"
        assert result["referrer_state"] == "state-1"
        assert result["short_url"] == "kamino_ref"
        assert mock_setup.await_args.kwargs["short_url"] == "kamino_ref"

    @pytest.mark.asyncio
    async def test_create_user_lookup_table_success(self, kamino_tool):
        signer = Keypair()

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch(
                "sakit.kamino.build_kamino_create_lookup_table_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "user_lookup_table": "lut-1",
                    }
                ),
            ) as mock_create,
            patch.object(
                kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-lut"}),
            ),
        ):
            MockKeypair.from_base58_string.return_value = signer
            result = await kamino_tool.execute(action="create_user_lookup_table")

        assert result["status"] == "success"
        assert result["signature"] == "sig-lut"
        assert result["user_lookup_table"] == "lut-1"
        assert mock_create.await_count == 1

    @pytest.mark.asyncio
    async def test_init_user_metadata_uses_config_default_referrer(self, kamino_tool):
        signer = Keypair()

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch(
                "sakit.kamino.build_kamino_init_user_metadata_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "user_lookup_table": "lut-1",
                    }
                ),
            ) as mock_init,
            patch.object(
                kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-meta"}),
            ),
        ):
            MockKeypair.from_base58_string.return_value = signer
            result = await kamino_tool.execute(action="init_user_metadata")

        assert result["status"] == "success"
        assert result["referrer"] == kamino_tool._managed_referrer
        assert mock_init.await_args.kwargs["referrer"] == kamino_tool._managed_referrer

    @pytest.mark.asyncio
    async def test_borrow_deposit_runs_internal_referral_automation_when_configured(self):
        user_signer = Keypair()
        referrer_signer = Keypair()
        tool = KaminoTool()
        tool.configure(
            {
                "tools": {
                    "kamino": {
                        "private_key": "user-private-key",
                        "rpc_url": "https://mainnet.helius-rpc.com/?api-key=test-key",
                        "referrer_private_key": str(referrer_signer),
                    }
                }
            }
        )

        with (
            patch("sakit.kamino.Keypair") as MockKeypair,
            patch("sakit.kamino.KaminoAPI") as MockKamino,
            patch(
                "sakit.kamino.fetch_kamino_reserve_metadata",
                new=AsyncMock(
                    return_value=MagicMock(
                        lending_market="market-1",
                        reserve="reserve-1",
                        reserve_liquidity_mint="mint-1",
                        pyth_oracle="",
                        switchboard_price_oracle="",
                        switchboard_twap_oracle="",
                        scope_prices="",
                        token_program_id="token-program-1",
                    )
                ),
            ) as mock_metadata,
            patch(
                "sakit.kamino.build_kamino_withdraw_referrer_fees_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "withdraw-tx",
                    }
                ),
            ) as mock_withdraw,
            patch.object(
                tool,
                "_sign_and_send",
                new=AsyncMock(
                    side_effect=[
                        {"status": "success", "signature": "sig-user"},
                        {"status": "success", "signature": "sig-withdraw"},
                    ]
                ),
            ),
        ):
            MockKeypair.from_base58_string.side_effect = lambda value: {
                "user-private-key": user_signer,
                str(referrer_signer): referrer_signer,
            }[value]
            mock_api = MagicMock()
            mock_api.build_borrow_deposit = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction="user-tx",
                    request_id="req-auto",
                    raw_response={"transaction": "user-tx"},
                )
            )
            MockKamino.return_value = mock_api

            result = await tool.execute(
                action="borrow_deposit",
                market="market-1",
                reserve="reserve-1",
                amount="2.0",
            )

        assert result["status"] == "success"
        assert result["signature"] == "sig-user"
        assert result["referral_automation"]["setup"]["status"] == "skipped"
        assert result["referral_automation"]["withdrawals"][0]["status"] == "success"
        assert mock_metadata.await_count == 1
        assert mock_withdraw.await_args.kwargs["reserve_liquidity_mint"] == "mint-1"


class TestKaminoPlugin:
    def test_plugin_name(self):
        plugin = KaminoPlugin()
        assert plugin.name == "kamino"

    def test_plugin_get_tools_empty_before_init(self):
        plugin = KaminoPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize(self):
        plugin = KaminoPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        tools = plugin.get_tools()
        assert len(tools) == 1
        assert isinstance(tools[0], KaminoTool)


class TestGetPlugin:
    def test_get_plugin_returns_instance(self):
        plugin = get_plugin()
        assert isinstance(plugin, KaminoPlugin)