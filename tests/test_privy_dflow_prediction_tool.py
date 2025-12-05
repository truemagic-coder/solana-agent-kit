"""
Tests for Privy DFlow Prediction Market Tool.

Tests the PrivyDFlowPredictionTool which provides safety-focused prediction
market discovery and trading with Privy delegated wallets.
"""

import pytest
from unittest.mock import patch, AsyncMock
import time

from sakit.privy_dflow_prediction import (
    PrivyDFlowPredictionTool,
    PrivyDFlowPredictionPlugin,
)
from sakit.utils.dflow import (
    DFlowPredictionClient,
    DFlowPredictionOrderResult,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def privy_prediction_tool():
    """Create a configured PrivyDFlowPredictionTool."""
    tool = PrivyDFlowPredictionTool()
    tool.configure(
        {
            "tools": {
                "privy_dflow_prediction": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": "wallet-auth:test-signing-key",
                    "rpc_url": "https://mainnet.helius-rpc.com/?api-key=test-key",
                    "platform_fee_bps": 50,
                    "fee_account": "FeeAccountPubkey123",
                    "min_volume_usd": 1000,
                    "min_liquidity_usd": 500,
                }
            }
        }
    )
    return tool


@pytest.fixture
def privy_prediction_tool_no_config():
    """Create an unconfigured PrivyDFlowPredictionTool."""
    tool = PrivyDFlowPredictionTool()
    tool.configure({"tools": {"privy_dflow_prediction": {}}})
    return tool


@pytest.fixture
def sample_market():
    """Sample market data for testing."""
    return {
        "ticker": "PRES-2028-DEM-HARRIS",
        "eventTicker": "PRES-2028-DEM",
        "title": "Will Kamala Harris be the 2028 Democratic Nominee?",
        "subtitle": "Democratic Primary",
        "status": "active",
        "result": None,
        "marketType": "binary",
        "volume": 125000,
        "openInterest": 45000,
        "liquidity": 20000,
        "openTime": int(time.time()) - 86400 * 30,
        "closeTime": int(time.time()) + 86400 * 365,
        "yesAsk": "0.37",
        "yesBid": "0.35",
        "noAsk": "0.65",
        "noBid": "0.63",
        "rulesPrimary": "This market will resolve YES if Kamala Harris wins.",
        "seriesTicker": "US-POLITICS-2028",
        "safety": {"score": "HIGH", "recommendation": "PROCEED", "warnings": []},
        "accounts": {
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {
                "yesMint": "YesMintAddress123",
                "noMint": "NoMintAddress456",
            }
        },
    }


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return {
        "ticker": "PRES-2028-DEM",
        "title": "2028 Democratic Nominee",
        "subtitle": "Who will win?",
        "seriesTicker": "US-POLITICS-2028",
        "volume": 250000,
        "liquidity": 45000,
        "status": "active",
    }


# =============================================================================
# TOOL INITIALIZATION TESTS
# =============================================================================


class TestToolInitialization:
    """Test tool initialization and configuration."""

    def test_tool_name(self):
        """Tool should have correct name."""
        tool = PrivyDFlowPredictionTool()
        assert tool.name == "privy_dflow_prediction"

    def test_tool_description(self):
        """Tool should have description with Privy."""
        tool = PrivyDFlowPredictionTool()
        assert "Privy" in tool.description
        assert "prediction markets" in tool.description.lower()

    def test_configure_sets_values(self, privy_prediction_tool):
        """Configure should set all config values."""
        assert privy_prediction_tool._privy_app_id == "test-app-id"
        assert privy_prediction_tool._privy_app_secret == "test-app-secret"
        assert privy_prediction_tool._signing_key == "wallet-auth:test-signing-key"
        assert (
            privy_prediction_tool._rpc_url
            == "https://mainnet.helius-rpc.com/?api-key=test-key"
        )
        assert privy_prediction_tool._platform_fee_bps == 50
        assert privy_prediction_tool._fee_account == "FeeAccountPubkey123"
        assert privy_prediction_tool._min_volume_usd == 1000
        assert privy_prediction_tool._min_liquidity_usd == 500

    def test_configure_defaults(self, privy_prediction_tool_no_config):
        """Unconfigured tool should have default values."""
        assert privy_prediction_tool_no_config._min_volume_usd == 1000
        assert privy_prediction_tool_no_config._min_liquidity_usd == 500
        assert privy_prediction_tool_no_config._include_risky is False

    def test_get_schema(self, privy_prediction_tool):
        """Schema should have required action field and privy_user_id."""
        schema = privy_prediction_tool.get_schema()
        assert schema["type"] == "object"
        assert "action" in schema["properties"]
        assert "privy_user_id" in schema["properties"]
        # OpenAI strict mode requires all properties in required array
        assert "action" in schema["required"]
        assert "privy_user_id" in schema["required"]
        assert schema["additionalProperties"] is False


# =============================================================================
# DISCOVERY ACTION TESTS
# =============================================================================


class TestDiscoveryActions:
    """Test discovery actions that don't require Privy signing."""

    @pytest.mark.asyncio
    async def test_search_success(self, privy_prediction_tool):
        """Search should return results with safety scores."""
        with patch.object(
            DFlowPredictionClient, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = {
                "markets": [{"ticker": "TEST-MARKET", "volume": 50000}],
                "events": [],
                "total": 1,
            }
            result = await privy_prediction_tool.execute(
                action="search", query="election"
            )
            assert result["status"] == "success"
            assert "markets" in result
            mock_search.assert_called_once_with(query="election", limit=20)

    @pytest.mark.asyncio
    async def test_search_missing_query(self, privy_prediction_tool):
        """Search without query should return error."""
        result = await privy_prediction_tool.execute(action="search")
        assert result["status"] == "error"
        assert "query is required" in result["message"]

    @pytest.mark.asyncio
    async def test_list_events_success(self, privy_prediction_tool, sample_event):
        """List events should return events."""
        with patch.object(
            DFlowPredictionClient, "list_events", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = {"events": [sample_event], "total": 1}
            result = await privy_prediction_tool.execute(action="list_events")
            assert result["status"] == "success"
            assert "events" in result

    @pytest.mark.asyncio
    async def test_get_event_success(self, privy_prediction_tool, sample_event):
        """Get event should return event details."""
        with patch.object(
            DFlowPredictionClient, "get_event", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_event
            result = await privy_prediction_tool.execute(
                action="get_event", event_id="PRES-2028-DEM"
            )
            assert result["status"] == "success"
            assert "event" in result

    @pytest.mark.asyncio
    async def test_get_event_missing_id(self, privy_prediction_tool):
        """Get event without event_id should return error."""
        result = await privy_prediction_tool.execute(action="get_event")
        assert result["status"] == "error"
        assert "event_id is required" in result["message"]

    @pytest.mark.asyncio
    async def test_list_markets_success(self, privy_prediction_tool, sample_market):
        """List markets should return markets."""
        with patch.object(
            DFlowPredictionClient, "list_markets", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = {"markets": [sample_market], "total": 1}
            result = await privy_prediction_tool.execute(action="list_markets")
            assert result["status"] == "success"
            assert "markets" in result

    @pytest.mark.asyncio
    async def test_get_market_success(self, privy_prediction_tool, sample_market):
        """Get market should return market with mints."""
        with patch.object(
            DFlowPredictionClient, "get_market", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_market
            result = await privy_prediction_tool.execute(
                action="get_market", market_id="PRES-2028-DEM-HARRIS"
            )
            assert result["status"] == "success"
            assert "market" in result
            # Check that mints were extracted
            assert result["market"].get("yes_mint") == "YesMintAddress123"
            assert result["market"].get("no_mint") == "NoMintAddress456"

    @pytest.mark.asyncio
    async def test_get_market_missing_id(self, privy_prediction_tool):
        """Get market without id should return error."""
        result = await privy_prediction_tool.execute(action="get_market")
        assert result["status"] == "error"
        assert "market_id or mint_address is required" in result["message"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, privy_prediction_tool):
        """Unknown action should return error."""
        result = await privy_prediction_tool.execute(action="unknown_action")
        assert result["status"] == "error"
        assert "Unknown action" in result["message"]


# =============================================================================
# TRADING ACTION VALIDATION TESTS
# =============================================================================


class TestTradingValidation:
    """Test trading action validation (before actual trading)."""

    @pytest.mark.asyncio
    async def test_buy_missing_app_id(self, privy_prediction_tool_no_config):
        """Buy without app_id should return error."""
        result = await privy_prediction_tool_no_config.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "app_id" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_app_secret(self, privy_prediction_tool):
        """Buy without app_secret should return error."""
        privy_prediction_tool._privy_app_secret = None
        result = await privy_prediction_tool.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "app_secret" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_signing_key(self, privy_prediction_tool):
        """Buy without signing_key should return error."""
        privy_prediction_tool._signing_key = None
        result = await privy_prediction_tool.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "signing_key" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_rpc_url(self, privy_prediction_tool):
        """Buy without rpc_url should return error."""
        privy_prediction_tool._rpc_url = None
        result = await privy_prediction_tool.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "rpc_url" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_user_id(self, privy_prediction_tool):
        """Buy without privy_user_id should return error."""
        result = await privy_prediction_tool.execute(
            action="buy", market_id="TEST", side="YES", amount=10
        )
        assert result["status"] == "error"
        assert "privy_user_id is required" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_market_id(self, privy_prediction_tool):
        """Buy without market_id should return error."""
        result = await privy_prediction_tool.execute(
            action="buy", privy_user_id="did:privy:test", side="YES", amount=10
        )
        assert result["status"] == "error"
        assert "market_id or mint_address required" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_side(self, privy_prediction_tool):
        """Buy without side should return error."""
        result = await privy_prediction_tool.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            amount=10,
        )
        assert result["status"] == "error"
        assert "side" in result["message"]

    @pytest.mark.asyncio
    async def test_buy_missing_amount(self, privy_prediction_tool):
        """Buy without amount should return error."""
        result = await privy_prediction_tool.execute(
            action="buy",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
        )
        assert result["status"] == "error"
        assert "amount required" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_user_id(self, privy_prediction_tool):
        """Sell without privy_user_id should return error."""
        result = await privy_prediction_tool.execute(
            action="sell", market_id="TEST", side="YES", amount=10
        )
        assert result["status"] == "error"
        assert "privy_user_id is required" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_market_id(self, privy_prediction_tool):
        """Sell without market_id should return error."""
        result = await privy_prediction_tool.execute(
            action="sell", privy_user_id="did:privy:test", side="YES", amount=10
        )
        assert result["status"] == "error"
        assert "market_id or mint_address required" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_side(self, privy_prediction_tool):
        """Sell without side should return error."""
        result = await privy_prediction_tool.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            amount=10,
        )
        assert result["status"] == "error"
        assert "side" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_amount(self, privy_prediction_tool):
        """Sell without amount should return error."""
        result = await privy_prediction_tool.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
        )
        assert result["status"] == "error"
        assert "amount required" in result["message"]


# =============================================================================
# POSITIONS ACTION TESTS
# =============================================================================


class TestPositionsAction:
    """Test positions action."""

    @pytest.mark.asyncio
    async def test_positions_missing_user_id(self, privy_prediction_tool):
        """Positions without privy_user_id should return error."""
        result = await privy_prediction_tool.execute(action="positions")
        assert result["status"] == "error"
        assert "privy_user_id is required" in result["message"]

    @pytest.mark.asyncio
    async def test_positions_missing_privy_config(
        self, privy_prediction_tool_no_config
    ):
        """Positions without Privy config should return error."""
        result = await privy_prediction_tool_no_config.execute(
            action="positions", privy_user_id="did:privy:test"
        )
        assert result["status"] == "error"
        assert "app_id" in result["message"] or "app_secret" in result["message"]


# =============================================================================
# PRIVY CLIENT TESTS
# =============================================================================


class TestPrivyClient:
    """Test Privy client creation."""

    def test_get_privy_client_missing_app_id(self, privy_prediction_tool):
        """Missing app_id should raise ValueError."""
        privy_prediction_tool._privy_app_id = None
        with pytest.raises(ValueError, match="app_id"):
            privy_prediction_tool._get_privy_client()

    def test_get_privy_client_missing_app_secret(self, privy_prediction_tool):
        """Missing app_secret should raise ValueError."""
        privy_prediction_tool._privy_app_secret = None
        with pytest.raises(ValueError, match="app_secret"):
            privy_prediction_tool._get_privy_client()

    def test_get_privy_client_success(self, privy_prediction_tool):
        """Should return AsyncPrivyAPI client."""
        client = privy_prediction_tool._get_privy_client()
        assert client is not None
        assert client.app_id == "test-app-id"


# =============================================================================
# DFLOW CLIENT TESTS
# =============================================================================


class TestDFlowClient:
    """Test DFlow client creation."""

    def test_get_client_default(self, privy_prediction_tool):
        """Get client with default settings."""
        client = privy_prediction_tool._get_client()
        assert isinstance(client, DFlowPredictionClient)
        assert client.min_volume_usd == 1000
        assert client.min_liquidity_usd == 500

    def test_get_client_override_risky(self, privy_prediction_tool):
        """Get client with include_risky override."""
        client = privy_prediction_tool._get_client(include_risky=True)
        assert client.include_risky is True


# =============================================================================
# MARKET MINTS EXTRACTION TESTS
# =============================================================================


class TestMarketMintsExtraction:
    """Test _get_market_with_mints method."""

    @pytest.mark.asyncio
    async def test_extracts_yes_no_mints(self, privy_prediction_tool, sample_market):
        """Should extract YES and NO mints from market accounts."""
        with patch.object(
            DFlowPredictionClient, "get_market", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_market
            client = privy_prediction_tool._get_client()
            result = await privy_prediction_tool._get_market_with_mints(
                client, "PRES-2028-DEM-HARRIS", None
            )
            assert result["yes_mint"] == "YesMintAddress123"
            assert result["no_mint"] == "NoMintAddress456"
            assert (
                result["settlement_mint"]
                == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            )


# =============================================================================
# BUY ACTION - NO WALLET FOUND TESTS
# =============================================================================


class TestBuyNoWallet:
    """Test buy action when no wallet is found."""

    @pytest.mark.asyncio
    async def test_buy_no_wallet_found(self, privy_prediction_tool):
        """Buy should fail if user has no delegated wallet."""
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = None
            result = await privy_prediction_tool.execute(
                action="buy",
                privy_user_id="did:privy:test",
                market_id="TEST",
                side="YES",
                amount=10,
            )
            assert result["status"] == "error"
            assert "No delegated Solana wallet" in result["message"]


# =============================================================================
# BUY ACTION - SAFETY CHECK TESTS
# =============================================================================


class TestBuySafetyCheck:
    """Test buy action safety checks."""

    @pytest.mark.asyncio
    async def test_buy_blocks_avoid_market(self, privy_prediction_tool, sample_market):
        """Buy should block AVOID markets by default."""
        sample_market["safety"] = {
            "score": "LOW",
            "recommendation": "AVOID",
            "warnings": ["Low volume"],
        }
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = sample_market
                result = await privy_prediction_tool.execute(
                    action="buy",
                    privy_user_id="did:privy:test",
                    market_id="TEST",
                    side="YES",
                    amount=10,
                )
                assert result["status"] == "error"
                assert "LOW" in result["message"]
                assert "safety" in result


# =============================================================================
# BUY ACTION - MISSING MINT TESTS
# =============================================================================


class TestBuyMissingMint:
    """Test buy action when outcome mint is missing."""

    @pytest.mark.asyncio
    async def test_buy_missing_yes_mint(self, privy_prediction_tool, sample_market):
        """Buy should fail if YES mint not found."""
        sample_market["accounts"] = {}  # No mints
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = sample_market
                result = await privy_prediction_tool.execute(
                    action="buy",
                    privy_user_id="did:privy:test",
                    market_id="TEST",
                    side="YES",
                    amount=10,
                )
                assert result["status"] == "error"
                assert "Could not find YES outcome mint" in result["message"]


# =============================================================================
# SELL ACTION - NO WALLET FOUND TESTS
# =============================================================================


class TestSellNoWallet:
    """Test sell action when no wallet is found."""

    @pytest.mark.asyncio
    async def test_sell_no_wallet_found(self, privy_prediction_tool):
        """Sell should fail if user has no delegated wallet."""
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = None
            result = await privy_prediction_tool.execute(
                action="sell",
                privy_user_id="did:privy:test",
                market_id="TEST",
                side="YES",
                amount=10,
            )
            assert result["status"] == "error"
            assert "No delegated Solana wallet" in result["message"]


# =============================================================================
# SELL ACTION - CONFIG VALIDATION TESTS
# =============================================================================


class TestSellConfigValidation:
    """Test sell action config validation."""

    @pytest.mark.asyncio
    async def test_sell_missing_app_id(self, privy_prediction_tool_no_config):
        """Sell without app_id should return error."""
        result = await privy_prediction_tool_no_config.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "app_id" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_app_secret(self, privy_prediction_tool):
        """Sell without app_secret should return error."""
        privy_prediction_tool._privy_app_secret = None
        result = await privy_prediction_tool.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "app_secret" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_signing_key(self, privy_prediction_tool):
        """Sell without signing_key should return error."""
        privy_prediction_tool._signing_key = None
        result = await privy_prediction_tool.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "signing_key" in result["message"]

    @pytest.mark.asyncio
    async def test_sell_missing_rpc_url(self, privy_prediction_tool):
        """Sell without rpc_url should return error."""
        privy_prediction_tool._rpc_url = None
        result = await privy_prediction_tool.execute(
            action="sell",
            privy_user_id="did:privy:test",
            market_id="TEST",
            side="YES",
            amount=10,
        )
        assert result["status"] == "error"
        assert "rpc_url" in result["message"]


# =============================================================================
# SELL ACTION - MISSING MINT TESTS
# =============================================================================


class TestSellMissingMint:
    """Test sell action when outcome mint is missing."""

    @pytest.mark.asyncio
    async def test_sell_missing_no_mint(self, privy_prediction_tool, sample_market):
        """Sell should fail if NO mint not found."""
        sample_market["accounts"] = {}  # No mints
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = sample_market
                result = await privy_prediction_tool.execute(
                    action="sell",
                    privy_user_id="did:privy:test",
                    market_id="TEST",
                    side="NO",
                    amount=10,
                )
                assert result["status"] == "error"
                assert "Could not find NO outcome mint" in result["message"]


# =============================================================================
# EXCEPTION HANDLING TESTS
# =============================================================================


class TestExceptionHandling:
    """Test exception handling in execute method."""

    @pytest.mark.asyncio
    async def test_exception_in_search(self, privy_prediction_tool):
        """Exception in search should return error."""
        with patch.object(
            DFlowPredictionClient, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = Exception("API error")
            result = await privy_prediction_tool.execute(action="search", query="test")
            assert result["status"] == "error"
            assert "API error" in result["message"]

    @pytest.mark.asyncio
    async def test_exception_in_list_events(self, privy_prediction_tool):
        """Exception in list_events should return error."""
        with patch.object(
            DFlowPredictionClient, "list_events", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = Exception("Network error")
            result = await privy_prediction_tool.execute(action="list_events")
            assert result["status"] == "error"
            assert "Network error" in result["message"]


# =============================================================================
# PLUGIN TESTS
# =============================================================================


# =============================================================================
# SUCCESSFUL BUY EXECUTION TESTS
# =============================================================================


class TestBuySuccessfulExecution:
    """Test successful buy execution flow."""

    @pytest.fixture
    def market_with_mints(self, sample_market):
        """Sample market with YES/NO mints."""
        sample_market["yes_mint"] = "YesMintAddress123"
        sample_market["no_mint"] = "NoMintAddress456"
        return sample_market

    @pytest.mark.asyncio
    async def test_buy_yes_success(self, privy_prediction_tool, market_with_mints):
        """Buy YES should succeed with mocked order execution."""
        success_result = DFlowPredictionOrderResult(
            success=True,
            signature="TestSignature123abc",
            execution_mode="sync",
            in_amount="10.0",
            out_amount="25.5",
            min_out_amount="25.0",
            price_impact_pct="0.1",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = success_result
                        result = await privy_prediction_tool.execute(
                            action="buy",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="YES",
                            amount=10,
                        )
                        assert result["status"] == "success"
                        assert result["action"] == "buy"
                        assert result["side"] == "YES"
                        assert result["amount_in"] == "10 USDC"
                        assert result["tokens_received"] == "25.5"
                        assert result["signature"] == "TestSignature123abc"
                        assert result["execution_mode"] == "sync"
                        assert result["wallet"] == "TestPublicKey123"
                        assert "safety" in result

    @pytest.mark.asyncio
    async def test_buy_no_success(self, privy_prediction_tool, market_with_mints):
        """Buy NO should succeed with mocked order execution."""
        success_result = DFlowPredictionOrderResult(
            success=True,
            signature="TestSignatureNo456",
            execution_mode="async",
            in_amount="10.0",
            out_amount="15.3",
            min_out_amount="15.0",
            price_impact_pct="0.2",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = success_result
                        result = await privy_prediction_tool.execute(
                            action="buy",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="NO",
                            amount=10,
                        )
                        assert result["status"] == "success"
                        assert result["side"] == "NO"
                        assert result["tokens_received"] == "15.3"

    @pytest.mark.asyncio
    async def test_buy_execution_failure(
        self, privy_prediction_tool, market_with_mints
    ):
        """Buy should return error when order execution fails."""
        failure_result = DFlowPredictionOrderResult(
            success=False,
            signature="FailedSig789",
            execution_mode="sync",
            in_amount=None,
            out_amount=None,
            min_out_amount=None,
            price_impact_pct=None,
            error="Insufficient liquidity",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = failure_result
                        result = await privy_prediction_tool.execute(
                            action="buy",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="YES",
                            amount=10,
                        )
                        assert result["status"] == "error"
                        assert "Insufficient liquidity" in result["message"]
                        assert result["signature"] == "FailedSig789"


# =============================================================================
# SUCCESSFUL SELL EXECUTION TESTS
# =============================================================================


class TestSellSuccessfulExecution:
    """Test successful sell execution flow."""

    @pytest.fixture
    def market_with_mints(self, sample_market):
        """Sample market with YES/NO mints."""
        sample_market["yes_mint"] = "YesMintAddress123"
        sample_market["no_mint"] = "NoMintAddress456"
        return sample_market

    @pytest.mark.asyncio
    async def test_sell_yes_success(self, privy_prediction_tool, market_with_mints):
        """Sell YES should succeed with mocked order execution."""
        success_result = DFlowPredictionOrderResult(
            success=True,
            signature="SellSignature123",
            execution_mode="sync",
            in_amount="10.0",
            out_amount="3.75",
            min_out_amount="3.50",
            price_impact_pct="0.5",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = success_result
                        result = await privy_prediction_tool.execute(
                            action="sell",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="YES",
                            amount=10,
                        )
                        assert result["status"] == "success"
                        assert result["action"] == "sell"
                        assert result["side"] == "YES"
                        assert result["tokens_sold"] == "10 YES"
                        assert result["usdc_received"] == "3.75"
                        assert result["signature"] == "SellSignature123"
                        assert result["execution_mode"] == "sync"
                        assert result["wallet"] == "TestPublicKey123"

    @pytest.mark.asyncio
    async def test_sell_no_success(self, privy_prediction_tool, market_with_mints):
        """Sell NO should succeed with mocked order execution."""
        success_result = DFlowPredictionOrderResult(
            success=True,
            signature="SellNoSignature456",
            execution_mode="async",
            in_amount="10.0",
            out_amount="6.50",
            min_out_amount="6.00",
            price_impact_pct="0.3",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = success_result
                        result = await privy_prediction_tool.execute(
                            action="sell",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="NO",
                            amount=10,
                        )
                        assert result["status"] == "success"
                        assert result["side"] == "NO"
                        assert result["tokens_sold"] == "10 NO"
                        assert result["usdc_received"] == "6.50"

    @pytest.mark.asyncio
    async def test_sell_execution_failure(
        self, privy_prediction_tool, market_with_mints
    ):
        """Sell should return error when order execution fails."""
        failure_result = DFlowPredictionOrderResult(
            success=False,
            signature="FailedSellSig789",
            execution_mode="sync",
            in_amount=None,
            out_amount=None,
            min_out_amount=None,
            price_impact_pct=None,
            error="Insufficient balance",
        )

        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_market", new_callable=AsyncMock
            ) as mock_get_market:
                mock_get_market.return_value = market_with_mints
                with patch.object(
                    DFlowPredictionClient,
                    "get_prediction_order",
                    new_callable=AsyncMock,
                ) as mock_order:
                    mock_order.return_value = {"order": "data"}
                    with patch.object(
                        DFlowPredictionClient,
                        "execute_prediction_order_blocking",
                        new_callable=AsyncMock,
                    ) as mock_execute:
                        mock_execute.return_value = failure_result
                        result = await privy_prediction_tool.execute(
                            action="sell",
                            privy_user_id="did:privy:test",
                            market_id="TEST",
                            side="YES",
                            amount=10,
                        )
                        assert result["status"] == "error"
                        assert "Insufficient balance" in result["message"]
                        assert result["signature"] == "FailedSellSig789"


# =============================================================================
# POSITIONS ACTION SUCCESS TESTS
# =============================================================================


class TestPositionsSuccessfulExecution:
    """Test successful positions action."""

    @pytest.mark.asyncio
    async def test_positions_with_wallet_found(self, privy_prediction_tool):
        """Positions should succeed when wallet is found."""
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = {
                "wallet_id": "test-wallet-id",
                "public_key": "TestPublicKey123",
            }
            with patch.object(
                DFlowPredictionClient, "get_outcome_mints", new_callable=AsyncMock
            ) as mock_mints:
                mock_mints.return_value = [
                    {"mint": "Mint1", "ticker": "TEST-YES"},
                    {"mint": "Mint2", "ticker": "TEST-NO"},
                    {"mint": "Mint3", "ticker": "ANOTHER-YES"},
                ]
                result = await privy_prediction_tool.execute(
                    action="positions",
                    privy_user_id="did:privy:test",
                )
                assert result["status"] == "success"
                assert result["user_wallet"] == "TestPublicKey123"
                assert result["outcome_mint_count"] == 3
                assert "hint" in result

    @pytest.mark.asyncio
    async def test_positions_missing_user_id(self, privy_prediction_tool):
        """Positions without privy_user_id should return error."""
        result = await privy_prediction_tool.execute(action="positions")
        assert result["status"] == "error"
        assert "privy_user_id is required" in result["message"]

    @pytest.mark.asyncio
    async def test_positions_missing_config(self, privy_prediction_tool_no_config):
        """Positions without Privy config should return error."""
        result = await privy_prediction_tool_no_config.execute(
            action="positions",
            privy_user_id="did:privy:test",
        )
        assert result["status"] == "error"
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_positions_no_wallet(self, privy_prediction_tool):
        """Positions should fail when no wallet found."""
        with patch(
            "sakit.privy_dflow_prediction._get_privy_embedded_wallet",
            new_callable=AsyncMock,
        ) as mock_wallet:
            mock_wallet.return_value = None
            result = await privy_prediction_tool.execute(
                action="positions",
                privy_user_id="did:privy:test",
            )
            assert result["status"] == "error"
            assert "No delegated Solana wallet" in result["message"]


# =============================================================================
# PLUGIN TESTS
# =============================================================================


class TestPlugin:
    """Test PrivyDFlowPredictionPlugin."""

    def test_plugin_name(self):
        """Plugin should have correct name."""
        plugin = PrivyDFlowPredictionPlugin()
        assert plugin.name == "privy_dflow_prediction"

    def test_plugin_description(self):
        """Plugin should have description."""
        plugin = PrivyDFlowPredictionPlugin()
        assert "Privy" in plugin.description
