"""Comprehensive tests for BirdeyeTool - all 50 actions."""

import pytest
import respx
from httpx import Response

from sakit.birdeye import BirdeyeTool


@pytest.fixture
def tool():
    """Create a BirdeyeTool instance with mock API key."""
    t = BirdeyeTool()
    t.configure({"tools": {"birdeye": {"api_key": "test-api-key"}}})
    return t


@pytest.fixture
def tool_no_key():
    """Create a BirdeyeTool instance without API key."""
    t = BirdeyeTool()
    t.configure({})
    return t


# Test token addresses
SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
BONK = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
TEST_WALLET = "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9"
TEST_PAIR = "8sLbNZoA1cfnvMJLPfp98ZLAnFSYCFApfJKMbiXNLwxj"


class TestNoApiKey:
    """Test behavior when API key is missing."""

    @pytest.mark.asyncio
    async def test_no_api_key(self, tool_no_key):
        """Should return error when API key is not set."""
        result = await tool_no_key.run("price", address=SOL)
        assert result["success"] is False
        assert "not configured" in result["error"]


class TestUnknownAction:
    """Test unknown action handling."""

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        """Should return error for unknown action."""
        result = await tool.run("unknown_action")
        assert result["success"] is False
        assert "Unknown action" in result["error"]


class TestPriceActions:
    """Tests for price-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_price(self, tool):
        """Test price action."""
        respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(200, json={"data": {"value": 150.5}})
        )
        result = await tool.run("price", address=SOL)
        assert result["success"] is True
        assert result["data"]["value"] == 150.5

    @pytest.mark.asyncio
    async def test_price_missing_address(self, tool):
        """Test price action without address."""
        result = await tool.run("price")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_multi_price(self, tool):
        """Test multi_price action."""
        respx.get("https://public-api.birdeye.so/defi/multi_price").mock(
            return_value=Response(
                200, json={"data": {SOL: {"value": 150}, USDC: {"value": 1}}}
            )
        )
        result = await tool.run("multi_price", list_address=f"{SOL},{USDC}")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_multi_price_missing_addresses(self, tool):
        """Test multi_price without addresses."""
        result = await tool.run("multi_price")
        assert result["success"] is False
        assert "list_address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_multi_price_post(self, tool):
        """Test multi_price_post action."""
        respx.post("https://public-api.birdeye.so/defi/multi_price").mock(
            return_value=Response(200, json={"data": {SOL: {"value": 150}}})
        )
        result = await tool.run("multi_price_post", list_address=[SOL, USDC])
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_history_price(self, tool):
        """Test history_price action."""
        respx.get("https://public-api.birdeye.so/defi/history_price").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("history_price", address=SOL, type="1H")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_history_price_missing_address(self, tool):
        """Test history_price without address."""
        result = await tool.run("history_price")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_historical_price_unix(self, tool):
        """Test historical_price_unix action."""
        respx.get("https://public-api.birdeye.so/defi/historical_price_unix").mock(
            return_value=Response(200, json={"data": {"value": 145.0}})
        )
        result = await tool.run(
            "historical_price_unix", address=SOL, unixtime=1700000000
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_historical_price_unix_missing_params(self, tool):
        """Test historical_price_unix without required params."""
        result = await tool.run("historical_price_unix", address=SOL)
        assert result["success"] is False
        assert "unixtime are required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_price_volume_single(self, tool):
        """Test price_volume_single action."""
        respx.get("https://public-api.birdeye.so/defi/price_volume/single").mock(
            return_value=Response(200, json={"data": {"price": 150, "volume": 1000000}})
        )
        result = await tool.run("price_volume_single", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_price_volume_multi(self, tool):
        """Test price_volume_multi action."""
        respx.post("https://public-api.birdeye.so/defi/price_volume/multi").mock(
            return_value=Response(200, json={"data": {}})
        )
        result = await tool.run("price_volume_multi", list_address=[SOL])
        assert result["success"] is True


class TestOHLCVActions:
    """Tests for OHLCV-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_ohlcv(self, tool):
        """Test ohlcv action."""
        respx.get("https://public-api.birdeye.so/defi/ohlcv").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("ohlcv", address=SOL, type="1H")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ohlcv_missing_address(self, tool):
        """Test ohlcv without address."""
        result = await tool.run("ohlcv")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_ohlcv_pair(self, tool):
        """Test ohlcv_pair action."""
        respx.get("https://public-api.birdeye.so/defi/ohlcv/pair").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("ohlcv_pair", address=TEST_PAIR)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_ohlcv_base_quote(self, tool):
        """Test ohlcv_base_quote action."""
        respx.get("https://public-api.birdeye.so/defi/ohlcv/base_quote").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run(
            "ohlcv_base_quote", base_address=SOL, quote_address=USDC
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ohlcv_base_quote_missing_params(self, tool):
        """Test ohlcv_base_quote without required params."""
        result = await tool.run("ohlcv_base_quote", base_address=SOL)
        assert result["success"] is False
        assert "quote_address are required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_ohlcv_v3(self, tool):
        """Test ohlcv_v3 action."""
        respx.get("https://public-api.birdeye.so/defi/v3/ohlcv").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("ohlcv_v3", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_ohlcv_pair_v3(self, tool):
        """Test ohlcv_pair_v3 action."""
        respx.get("https://public-api.birdeye.so/defi/v3/ohlcv/pair").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("ohlcv_pair_v3", address=TEST_PAIR)
        assert result["success"] is True


class TestTradesActions:
    """Tests for trades-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_token(self, tool):
        """Test trades_token action."""
        respx.get("https://public-api.birdeye.so/defi/txs/token").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("trades_token", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_trades_token_missing_address(self, tool):
        """Test trades_token without address."""
        result = await tool.run("trades_token")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_pair(self, tool):
        """Test trades_pair action."""
        respx.get("https://public-api.birdeye.so/defi/txs/pair").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("trades_pair", address=TEST_PAIR)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_token_seek(self, tool):
        """Test trades_token_seek action."""
        respx.get("https://public-api.birdeye.so/defi/txs/token/seek_by_time").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run(
            "trades_token_seek", address=SOL, before_time=1700000000
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_pair_seek(self, tool):
        """Test trades_pair_seek action."""
        respx.get("https://public-api.birdeye.so/defi/txs/pair/seek_by_time").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run(
            "trades_pair_seek", address=TEST_PAIR, after_time=1600000000
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_v3(self, tool):
        """Test trades_v3 action."""
        respx.get("https://public-api.birdeye.so/defi/v3/txs").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("trades_v3", address=SOL, owner=TEST_WALLET)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_trades_token_v3(self, tool):
        """Test trades_token_v3 action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/txs").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("trades_token_v3", address=SOL)
        assert result["success"] is True


class TestTokenActions:
    """Tests for token-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_list(self, tool):
        """Test token_list action."""
        respx.get("https://public-api.birdeye.so/defi/tokenlist").mock(
            return_value=Response(200, json={"data": {"tokens": []}})
        )
        result = await tool.run("token_list", limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_list_v3(self, tool):
        """Test token_list_v3 action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/list").mock(
            return_value=Response(200, json={"data": {"tokens": []}})
        )
        result = await tool.run("token_list_v3", limit=10, min_liquidity=1000)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_list_scroll(self, tool):
        """Test token_list_scroll action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/list/scroll").mock(
            return_value=Response(
                200, json={"data": {"tokens": [], "scroll_id": "abc"}}
            )
        )
        result = await tool.run("token_list_scroll", limit=50)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_overview(self, tool):
        """Test token_overview action."""
        respx.get("https://public-api.birdeye.so/defi/token_overview").mock(
            return_value=Response(
                200, json={"data": {"symbol": "SOL", "name": "Solana"}}
            )
        )
        result = await tool.run("token_overview", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_token_overview_missing_address(self, tool):
        """Test token_overview without address."""
        result = await tool.run("token_overview")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_metadata_single(self, tool):
        """Test token_metadata_single action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/meta-data/single").mock(
            return_value=Response(200, json={"data": {"symbol": "SOL"}})
        )
        result = await tool.run("token_metadata_single", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_metadata_multiple(self, tool):
        """Test token_metadata_multiple action."""
        respx.get(
            "https://public-api.birdeye.so/defi/v3/token/meta-data/multiple"
        ).mock(return_value=Response(200, json={"data": {}}))
        result = await tool.run("token_metadata_multiple", list_address=f"{SOL},{USDC}")
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_market_data(self, tool):
        """Test token_market_data action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/market-data").mock(
            return_value=Response(200, json={"data": {"price": 150}})
        )
        result = await tool.run("token_market_data", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_market_data_multiple(self, tool):
        """Test token_market_data_multiple action."""
        respx.get(
            "https://public-api.birdeye.so/defi/v3/token/market-data/multiple"
        ).mock(return_value=Response(200, json={"data": {}}))
        result = await tool.run(
            "token_market_data_multiple", list_address=f"{SOL},{USDC}"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_trade_data_single(self, tool):
        """Test token_trade_data_single action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/trade-data/single").mock(
            return_value=Response(200, json={"data": {"volume_24h": 1000000}})
        )
        result = await tool.run("token_trade_data_single", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_trade_data_multiple(self, tool):
        """Test token_trade_data_multiple action."""
        respx.get(
            "https://public-api.birdeye.so/defi/v3/token/trade-data/multiple"
        ).mock(return_value=Response(200, json={"data": {}}))
        result = await tool.run(
            "token_trade_data_multiple", list_address=f"{SOL},{USDC}"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_holder(self, tool):
        """Test token_holder action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/holder").mock(
            return_value=Response(200, json={"data": {"holders": []}})
        )
        result = await tool.run("token_holder", address=SOL, limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_trending(self, tool):
        """Test token_trending action."""
        respx.get("https://public-api.birdeye.so/defi/token_trending").mock(
            return_value=Response(200, json={"data": {"tokens": []}})
        )
        result = await tool.run("token_trending", limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_new_listing(self, tool):
        """Test token_new_listing action."""
        respx.get("https://public-api.birdeye.so/defi/v2/tokens/new_listing").mock(
            return_value=Response(200, json={"data": {"tokens": []}})
        )
        result = await tool.run("token_new_listing", limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_top_traders(self, tool):
        """Test token_top_traders action."""
        respx.get("https://public-api.birdeye.so/defi/v2/tokens/top_traders").mock(
            return_value=Response(200, json={"data": {"traders": []}})
        )
        result = await tool.run("token_top_traders", address=BONK, time_frame="24h")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_token_top_traders_missing_address(self, tool):
        """Test token_top_traders without address."""
        result = await tool.run("token_top_traders")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_markets(self, tool):
        """Test token_markets action."""
        respx.get("https://public-api.birdeye.so/defi/v2/markets").mock(
            return_value=Response(200, json={"data": {"markets": []}})
        )
        result = await tool.run("token_markets", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_security(self, tool):
        """Test token_security action."""
        respx.get("https://public-api.birdeye.so/defi/token_security").mock(
            return_value=Response(200, json={"data": {"isScam": False}})
        )
        result = await tool.run("token_security", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_creation_info(self, tool):
        """Test token_creation_info action."""
        respx.get("https://public-api.birdeye.so/defi/token_creation_info").mock(
            return_value=Response(200, json={"data": {"creator": TEST_WALLET}})
        )
        result = await tool.run("token_creation_info", address=BONK)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_mint_burn(self, tool):
        """Test token_mint_burn action."""
        respx.get("https://public-api.birdeye.so/defi/v3/token/mint-burn-txs").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("token_mint_burn", address=BONK, tx_type="mint")
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_all_time_trades_single(self, tool):
        """Test token_all_time_trades_single action."""
        respx.get("https://public-api.birdeye.so/defi/v3/all-time-trades/single").mock(
            return_value=Response(200, json={"data": {"total_trades": 1000000}})
        )
        result = await tool.run("token_all_time_trades_single", address=SOL)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_all_time_trades_multiple(self, tool):
        """Test token_all_time_trades_multiple action."""
        respx.get(
            "https://public-api.birdeye.so/defi/v3/all-time-trades/multiple"
        ).mock(return_value=Response(200, json={"data": {}}))
        result = await tool.run(
            "token_all_time_trades_multiple", list_address=f"{SOL},{USDC}"
        )
        assert result["success"] is True


class TestPairActions:
    """Tests for pair-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_pair_overview_single(self, tool):
        """Test pair_overview_single action."""
        respx.get("https://public-api.birdeye.so/defi/v3/pair/overview/single").mock(
            return_value=Response(200, json={"data": {"liquidity": 1000000}})
        )
        result = await tool.run("pair_overview_single", address=TEST_PAIR)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pair_overview_single_missing_address(self, tool):
        """Test pair_overview_single without address."""
        result = await tool.run("pair_overview_single")
        assert result["success"] is False
        assert "address is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_pair_overview_multiple(self, tool):
        """Test pair_overview_multiple action."""
        respx.get("https://public-api.birdeye.so/defi/v3/pair/overview/multiple").mock(
            return_value=Response(200, json={"data": {}})
        )
        result = await tool.run("pair_overview_multiple", list_address=TEST_PAIR)
        assert result["success"] is True


class TestTraderActions:
    """Tests for trader-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_trader_gainers_losers(self, tool):
        """Test trader_gainers_losers action."""
        respx.get("https://public-api.birdeye.so/trader/gainers-losers").mock(
            return_value=Response(200, json={"data": {"gainers": [], "losers": []}})
        )
        result = await tool.run("trader_gainers_losers", type="1h", limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_trader_txs_seek(self, tool):
        """Test trader_txs_seek action."""
        respx.get("https://public-api.birdeye.so/trader/txs/seek_by_time").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run(
            "trader_txs_seek", address=TEST_WALLET, before_time=1700000000
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_trader_txs_seek_missing_address(self, tool):
        """Test trader_txs_seek without address."""
        result = await tool.run("trader_txs_seek")
        assert result["success"] is False
        assert "address is required" in result["error"]


class TestWalletActions:
    """Tests for wallet-related actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_wallet_token_list(self, tool):
        """Test wallet_token_list action."""
        respx.get("https://public-api.birdeye.so/v1/wallet/token_list").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("wallet_token_list", wallet=TEST_WALLET)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_wallet_token_list_missing_wallet(self, tool):
        """Test wallet_token_list without wallet."""
        result = await tool.run("wallet_token_list")
        assert result["success"] is False
        assert "wallet is required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_wallet_token_balance(self, tool):
        """Test wallet_token_balance action."""
        respx.get("https://public-api.birdeye.so/v1/wallet/token_balance").mock(
            return_value=Response(200, json={"data": {"balance": 100}})
        )
        result = await tool.run(
            "wallet_token_balance", wallet=TEST_WALLET, token_address=SOL
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_wallet_token_balance_missing_params(self, tool):
        """Test wallet_token_balance without required params."""
        result = await tool.run("wallet_token_balance", wallet=TEST_WALLET)
        assert result["success"] is False
        assert "token_address are required" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_wallet_tx_list(self, tool):
        """Test wallet_tx_list action."""
        respx.get("https://public-api.birdeye.so/v1/wallet/tx_list").mock(
            return_value=Response(200, json={"data": {"items": []}})
        )
        result = await tool.run("wallet_tx_list", wallet=TEST_WALLET, limit=20)
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_wallet_balance_change(self, tool):
        """Test wallet_balance_change action."""
        respx.get("https://public-api.birdeye.so/wallet/v2/balance-change").mock(
            return_value=Response(200, json={"data": {"changes": []}})
        )
        result = await tool.run(
            "wallet_balance_change", wallet=TEST_WALLET, token_address=SOL
        )
        assert result["success"] is True


class TestSearchAction:
    """Tests for search action."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_search(self, tool):
        """Test search action."""
        respx.get("https://public-api.birdeye.so/defi/v3/search").mock(
            return_value=Response(200, json={"data": {"tokens": [], "pairs": []}})
        )
        result = await tool.run("search", keyword="bonk", limit=10)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search_missing_keyword(self, tool):
        """Test search without keyword."""
        result = await tool.run("search")
        assert result["success"] is False
        assert "keyword is required" in result["error"]


class TestUtilsActions:
    """Tests for utility actions."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_latest_block(self, tool):
        """Test latest_block action."""
        respx.get("https://public-api.birdeye.so/defi/v3/txs/latest_block").mock(
            return_value=Response(200, json={"data": {"slot": 250000000}})
        )
        result = await tool.run("latest_block")
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_networks(self, tool):
        """Test networks action."""
        respx.get("https://public-api.birdeye.so/defi/networks").mock(
            return_value=Response(200, json={"data": ["solana", "ethereum"]})
        )
        result = await tool.run("networks")
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_supported_chains(self, tool):
        """Test supported_chains action."""
        respx.get("https://public-api.birdeye.so/v1/wallet/list_supported_chain").mock(
            return_value=Response(200, json={"data": ["solana"]})
        )
        result = await tool.run("supported_chains")
        assert result["success"] is True


class TestAPIErrors:
    """Tests for API error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error_response(self, tool):
        """Test handling of API error response."""
        respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        result = await tool.run("price", address=SOL)
        assert result["success"] is False
        assert "API error: 500" in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_unauthorized(self, tool):
        """Test handling of 401 unauthorized."""
        respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(401, text="Unauthorized")
        )
        result = await tool.run("price", address=SOL)
        assert result["success"] is False
        assert "401" in result["error"]


class TestChainSupport:
    """Tests for multi-chain support."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_different_chain(self, tool):
        """Test specifying different chain."""
        route = respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(200, json={"data": {"value": 3000}})
        )
        result = await tool.run("price", address="0xabc", chain="ethereum")
        assert result["success"] is True
        # Verify the chain header was set
        assert route.calls[0].request.headers["x-chain"] == "ethereum"

    @pytest.mark.asyncio
    @respx.mock
    async def test_chain_from_config(self):
        """Test chain configured via config locks all requests to that chain."""
        t = BirdeyeTool()
        t.configure(
            {"tools": {"birdeye": {"api_key": "test-key", "chain": "ethereum"}}}
        )

        route = respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(200, json={"data": {"value": 3000}})
        )
        # Don't pass chain - should use config chain
        result = await t.run("price", address="0xabc")
        assert result["success"] is True
        assert route.calls[0].request.headers["x-chain"] == "ethereum"

    @pytest.mark.asyncio
    @respx.mock
    async def test_default_chain_is_solana(self, tool):
        """Test default chain is solana when not specified."""
        route = respx.get("https://public-api.birdeye.so/defi/price").mock(
            return_value=Response(200, json={"data": {"value": 150}})
        )
        result = await tool.run("price", address=SOL)
        assert result["success"] is True
        assert route.calls[0].request.headers["x-chain"] == "solana"
