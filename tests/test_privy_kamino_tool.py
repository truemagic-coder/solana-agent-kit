"""Tests for the Privy Kamino tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from solders.keypair import Keypair

from sakit.privy_kamino import PrivyKaminoPlugin, PrivyKaminoTool, get_plugin


@pytest.fixture
def privy_kamino_tool():
    referrer_signer = Keypair()
    tool = PrivyKaminoTool()
    tool.configure(
        {
            "tools": {
                "privy_kamino": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": "wallet-auth:test-signing-key",
                    "rpc_url": "https://mainnet.helius-rpc.com/?api-key=test-key",
                    "referrer_private_key": str(referrer_signer),
                }
            }
        }
    )
    return tool


class TestPrivyKaminoToolSchema:
    def test_tool_name(self, privy_kamino_tool):
        assert privy_kamino_tool.name == "privy_kamino"

    def test_schema_has_referral_actions(self, privy_kamino_tool):
        schema = privy_kamino_tool.get_schema()
        assert "borrow_deposit" in schema["properties"]["action"]["enum"]
        assert "setup_referrer" not in schema["properties"]["action"]["enum"]
        assert "withdraw_referrer_fees" not in schema["properties"]["action"]["enum"]


class TestPrivyKaminoToolExecute:
    @pytest.mark.asyncio
    async def test_execute_requires_wallet_params(self, privy_kamino_tool):
        result = await privy_kamino_tool.execute(
            wallet_id="",
            wallet_public_key="",
            action="list_markets",
        )

        assert result["status"] == "error"
        assert "wallet_id" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_markets_success(self, privy_kamino_tool):
        with patch("sakit.privy_kamino.KaminoAPI") as MockKamino:
            mock_api = MagicMock()
            mock_api.list_markets = AsyncMock(return_value={"success": True, "data": [{"market": "A"}]})
            MockKamino.return_value = mock_api

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
                action="list_markets",
            )

        assert result["status"] == "success"
        assert result["data"][0]["market"] == "A"

    @pytest.mark.asyncio
    async def test_borrow_deposit_success(self, privy_kamino_tool):
        with (
            patch("sakit.privy_kamino.KaminoAPI") as MockKamino,
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch.object(
                privy_kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-123"}),
            ),
        ):
            mock_api = MagicMock()
            mock_api.build_borrow_deposit = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction="tx-base64",
                    request_id="req-1",
                    raw_response={"transaction": "tx-base64"},
                )
            )
            MockKamino.return_value = mock_api
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
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
        call = mock_api.build_borrow_deposit.await_args
        assert call.kwargs["referrer"] == "referrer-wallet"
        assert call.kwargs["referral_code"] == "ref-abc"

    @pytest.mark.asyncio
    async def test_borrow_deposit_uses_config_referral_defaults(self, privy_kamino_tool):
        with (
            patch("sakit.privy_kamino.KaminoAPI") as MockKamino,
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch.object(
                privy_kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-defaults"}),
            ),
        ):
            mock_api = MagicMock()
            mock_api.build_borrow_deposit = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    transaction="tx-base64",
                    request_id="req-defaults",
                    raw_response={"transaction": "tx-base64"},
                )
            )
            MockKamino.return_value = mock_api
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
                action="borrow_deposit",
                market="market-1",
                reserve="reserve-1",
                amount="2.0",
            )

        assert result["status"] == "success"
        assert result["referrer"] == privy_kamino_tool._managed_referrer
        assert result["referral_code"] is None
        call = mock_api.build_borrow_deposit.await_args
        assert call.kwargs["referrer"] == privy_kamino_tool._managed_referrer
        assert call.kwargs["referral_code"] is None

    @pytest.mark.asyncio
    async def test_setup_referrer_success(self, privy_kamino_tool):
        with (
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch(
                "sakit.privy_kamino.build_kamino_referrer_setup_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "referrer_state": "state-1",
                    }
                ),
            ) as mock_setup,
            patch.object(
                privy_kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-setup"}),
            ),
        ):
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
                action="setup_referrer",
                short_url="kamino_ref",
                user_lookup_table="11111111111111111111111111111116",
            )

        assert result["status"] == "success"
        assert result["signature"] == "sig-setup"
        assert result["referrer_state"] == "state-1"
        assert mock_setup.await_args.kwargs["short_url"] == "kamino_ref"

    @pytest.mark.asyncio
    async def test_create_user_lookup_table_success(self, privy_kamino_tool):
        with (
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch(
                "sakit.privy_kamino.build_kamino_create_lookup_table_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "user_lookup_table": "lut-1",
                    }
                ),
            ) as mock_create,
            patch.object(
                privy_kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-lut"}),
            ),
        ):
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
                action="create_user_lookup_table",
            )

        assert result["status"] == "success"
        assert result["signature"] == "sig-lut"
        assert result["user_lookup_table"] == "lut-1"
        assert mock_create.await_count == 1

    @pytest.mark.asyncio
    async def test_init_user_metadata_uses_config_default_referrer(self, privy_kamino_tool):
        with (
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch(
                "sakit.privy_kamino.build_kamino_init_user_metadata_transaction",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "transaction": "tx-base64",
                        "user_lookup_table": "lut-1",
                    }
                ),
            ) as mock_init,
            patch.object(
                privy_kamino_tool,
                "_sign_and_send",
                new=AsyncMock(return_value={"status": "success", "signature": "sig-meta"}),
            ),
        ):
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await privy_kamino_tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
                action="init_user_metadata",
            )

        assert result["status"] == "success"
        assert result["referrer"] == privy_kamino_tool._managed_referrer
        assert mock_init.await_args.kwargs["referrer"] == privy_kamino_tool._managed_referrer

    @pytest.mark.asyncio
    async def test_borrow_deposit_runs_internal_referral_automation_when_configured(self):
        referrer_signer = Keypair()
        tool = PrivyKaminoTool()
        tool.configure(
            {
                "tools": {
                    "privy_kamino": {
                        "app_id": "test-app-id",
                        "app_secret": "test-app-secret",
                        "signing_key": "wallet-auth:test-signing-key",
                        "rpc_url": "https://mainnet.helius-rpc.com/?api-key=test-key",
                        "referrer_private_key": str(referrer_signer),
                    }
                }
            }
        )

        with (
            patch("sakit.privy_kamino.Keypair") as MockKeypair,
            patch("sakit.privy_kamino.KaminoAPI") as MockKamino,
            patch("sakit.privy_kamino.AsyncPrivyAPI") as MockPrivy,
            patch(
                "sakit.privy_kamino.fetch_kamino_reserve_metadata",
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
                "sakit.privy_kamino.build_kamino_withdraw_referrer_fees_transaction",
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
                new=AsyncMock(return_value={"status": "success", "signature": "sig-user"}),
            ),
            patch.object(
                tool,
                "_sign_and_send_with_keypair",
                new=AsyncMock(
                    side_effect=[
                        {"status": "success", "signature": "sig-withdraw"},
                    ]
                ),
            ),
        ):
            MockKeypair.from_base58_string.return_value = referrer_signer
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
            mock_privy_client = MagicMock()
            mock_privy_client.close = AsyncMock()
            MockPrivy.return_value = mock_privy_client

            result = await tool.execute(
                wallet_id="wallet-123",
                wallet_public_key="WalletPubkey123",
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


class TestPrivyKaminoPlugin:
    def test_plugin_initialize(self):
        plugin = PrivyKaminoPlugin()
        registry = MagicMock()

        plugin.initialize(registry)

        tools = plugin.get_tools()
        assert len(tools) == 1
        assert isinstance(tools[0], PrivyKaminoTool)

    def test_get_plugin(self):
        assert isinstance(get_plugin(), PrivyKaminoPlugin)
