"""
Tests for Technical Analysis Tool.

Tests the TechnicalAnalysisTool which provides comprehensive technical indicators
for any token using Birdeye OHLCV data.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

from sakit.technical_analysis import (
    TechnicalAnalysisTool,
    TechnicalAnalysisPlugin,
    get_plugin,
    calculate_indicators,
    MIN_CANDLES_REQUIRED,
    TIMEFRAME_MAP,
    _safe_get,
    _safe_get_series,
    _calc_percent_diff,
)


# =============================================================================
# Unit Tests for Helper Functions
# =============================================================================


class TestSafeGet:
    """Test _safe_get helper function."""

    def test_safe_get_valid_value(self):
        """Should return value when column exists and value is valid."""
        df = pd.DataFrame({"col1": [1.0, 2.0, 3.0]})
        assert _safe_get(df, "col1", -1) == 3.0
        assert _safe_get(df, "col1", 0) == 1.0

    def test_safe_get_missing_column(self):
        """Should return None when column doesn't exist."""
        df = pd.DataFrame({"col1": [1.0, 2.0, 3.0]})
        assert _safe_get(df, "col2", -1) is None

    def test_safe_get_nan_value(self):
        """Should return None for NaN values."""
        df = pd.DataFrame({"col1": [1.0, np.nan, 3.0]})
        assert _safe_get(df, "col1", 1) is None

    def test_safe_get_empty_dataframe(self):
        """Should return None for empty DataFrame."""
        df = pd.DataFrame()
        assert _safe_get(df, "col1", 0) is None

    def test_safe_get_none_dataframe(self):
        """Should return None for None DataFrame."""
        assert _safe_get(None, "col1", 0) is None

    def test_safe_get_index_out_of_bounds(self):
        """Should return None for out of bounds index."""
        df = pd.DataFrame({"col1": [1.0, 2.0]})
        assert _safe_get(df, "col1", 10) is None


class TestSafeGetSeries:
    """Test _safe_get_series helper function."""

    def test_safe_get_series_valid_value(self):
        """Should return value when series has valid data."""
        series = pd.Series([1.0, 2.0, 3.0])
        assert _safe_get_series(series, -1) == 3.0
        assert _safe_get_series(series, 0) == 1.0

    def test_safe_get_series_nan_value(self):
        """Should return None for NaN values."""
        series = pd.Series([1.0, np.nan, 3.0])
        assert _safe_get_series(series, 1) is None

    def test_safe_get_series_empty(self):
        """Should return None for empty Series."""
        series = pd.Series([], dtype=float)
        assert _safe_get_series(series, 0) is None

    def test_safe_get_series_none(self):
        """Should return None for None Series."""
        assert _safe_get_series(None, 0) is None


class TestCalcPercentDiff:
    """Test _calc_percent_diff helper function."""

    def test_calc_percent_diff_positive(self):
        """Should calculate positive percentage difference."""
        # 110 is 10% above 100
        result = _calc_percent_diff(110, 100)
        assert result == 10.0

    def test_calc_percent_diff_negative(self):
        """Should calculate negative percentage difference."""
        # 90 is 10% below 100
        result = _calc_percent_diff(90, 100)
        assert result == -10.0

    def test_calc_percent_diff_zero_reference(self):
        """Should return None when reference is zero."""
        assert _calc_percent_diff(100, 0) is None

    def test_calc_percent_diff_none_reference(self):
        """Should return None when reference is None."""
        assert _calc_percent_diff(100, None) is None


class TestTimeframeMap:
    """Test timeframe mapping."""

    def test_all_timeframes_mapped(self):
        """All expected timeframes should be mapped."""
        expected = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "1d"]
        for tf in expected:
            assert tf in TIMEFRAME_MAP, f"Timeframe {tf} should be in TIMEFRAME_MAP"

    def test_timeframe_values_are_birdeye_format(self):
        """Timeframe values should match Birdeye API format."""
        assert TIMEFRAME_MAP["1h"] == "1H"
        assert TIMEFRAME_MAP["4h"] == "4H"
        assert TIMEFRAME_MAP["1d"] == "1D"


# =============================================================================
# Tests for calculate_indicators Function
# =============================================================================


class TestCalculateIndicators:
    """Test calculate_indicators function with real pandas-ta calculations."""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data with enough points for all indicators."""
        np.random.seed(42)
        n = 250  # More than MIN_CANDLES_REQUIRED

        # Generate realistic price movement
        base_price = 100.0
        prices = [base_price]
        for _ in range(n - 1):
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            prices.append(prices[-1] * (1 + change))

        prices = np.array(prices)

        df = pd.DataFrame(
            {
                "open": prices * (1 + np.random.uniform(-0.01, 0.01, n)),
                "high": prices * (1 + np.random.uniform(0, 0.02, n)),
                "low": prices * (1 - np.random.uniform(0, 0.02, n)),
                "close": prices,
                "volume": np.random.uniform(1000000, 10000000, n),
            }
        )

        return df

    def test_calculate_indicators_returns_all_categories(self, sample_ohlcv_data):
        """Should return all indicator categories."""
        result = calculate_indicators(sample_ohlcv_data)

        assert "trend" in result
        assert "momentum" in result
        assert "volatility" in result
        assert "volume" in result
        assert "price_vs_indicators" in result

    def test_trend_indicators_present(self, sample_ohlcv_data):
        """Should include all trend indicators."""
        result = calculate_indicators(sample_ohlcv_data)
        trend = result["trend"]

        assert "ema_9" in trend
        assert "ema_21" in trend
        assert "ema_50" in trend
        assert "ema_200" in trend
        assert "sma_20" in trend
        assert "sma_50" in trend
        assert "sma_200" in trend
        assert "macd" in trend
        assert "adx" in trend

    def test_momentum_indicators_present(self, sample_ohlcv_data):
        """Should include all momentum indicators."""
        result = calculate_indicators(sample_ohlcv_data)
        momentum = result["momentum"]

        assert "rsi_14" in momentum
        assert "stochastic" in momentum
        assert "cci_20" in momentum
        assert "williams_r_14" in momentum
        assert "roc_12" in momentum
        assert "mfi_14" in momentum

    def test_volatility_indicators_present(self, sample_ohlcv_data):
        """Should include all volatility indicators."""
        result = calculate_indicators(sample_ohlcv_data)
        volatility = result["volatility"]

        assert "bollinger" in volatility
        assert "atr_14" in volatility
        assert "atr_percent" in volatility
        assert "keltner" in volatility

    def test_volume_indicators_present(self, sample_ohlcv_data):
        """Should include all volume indicators."""
        result = calculate_indicators(sample_ohlcv_data)
        volume = result["volume"]

        assert "obv" in volume
        assert "obv_ema_21" in volume
        assert "volume_sma_20" in volume
        assert "current_volume" in volume
        assert "vwap" in volume

    def test_macd_structure(self, sample_ohlcv_data):
        """MACD should have line, signal, and histogram."""
        result = calculate_indicators(sample_ohlcv_data)
        macd = result["trend"]["macd"]

        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd

    def test_bollinger_structure(self, sample_ohlcv_data):
        """Bollinger Bands should have all components."""
        result = calculate_indicators(sample_ohlcv_data)
        bb = result["volatility"]["bollinger"]

        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb
        assert "bandwidth" in bb
        assert "percent_b" in bb

    def test_stochastic_structure(self, sample_ohlcv_data):
        """Stochastic should have K and D lines."""
        result = calculate_indicators(sample_ohlcv_data)
        stoch = result["momentum"]["stochastic"]

        assert "k" in stoch
        assert "d" in stoch

    def test_price_vs_indicators_calculated(self, sample_ohlcv_data):
        """Should calculate price vs indicator percentages."""
        result = calculate_indicators(sample_ohlcv_data)
        pvs = result["price_vs_indicators"]

        # Should have some calculated percentages
        assert len(pvs) > 0

    def test_rsi_in_valid_range(self, sample_ohlcv_data):
        """RSI should be between 0 and 100."""
        result = calculate_indicators(sample_ohlcv_data)
        rsi = result["momentum"]["rsi_14"]

        if rsi is not None:
            assert 0 <= rsi <= 100

    def test_williams_r_in_valid_range(self, sample_ohlcv_data):
        """Williams %R should be between -100 and 0."""
        result = calculate_indicators(sample_ohlcv_data)
        willr = result["momentum"]["williams_r_14"]

        if willr is not None:
            assert -100 <= willr <= 0


# =============================================================================
# Tests for TechnicalAnalysisTool Class
# =============================================================================


class TestTechnicalAnalysisTool:
    """Test TechnicalAnalysisTool class."""

    def test_tool_initialization(self):
        """Tool should initialize with correct defaults."""
        tool = TechnicalAnalysisTool()

        assert tool.name == "technical_analysis"
        assert "technical analysis" in tool.description.lower()
        assert tool.default_chain == "solana"

    def test_get_schema_structure(self):
        """Schema should have required structure for OpenAI."""
        tool = TechnicalAnalysisTool()
        schema = tool.get_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert schema.get("additionalProperties") is False

    def test_schema_has_address_property(self):
        """Schema should require address parameter."""
        tool = TechnicalAnalysisTool()
        schema = tool.get_schema()

        assert "address" in schema["properties"]
        assert "address" in schema["required"]

    def test_schema_has_timeframe_property(self):
        """Schema should have timeframe parameter."""
        tool = TechnicalAnalysisTool()
        schema = tool.get_schema()

        assert "timeframe" in schema["properties"]
        assert schema["properties"]["timeframe"]["default"] == "4h"

    def test_configure_sets_api_key(self):
        """Configure should set API key."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        assert tool.api_key == "test-key"

    def test_configure_sets_chain(self):
        """Configure should set chain."""
        tool = TechnicalAnalysisTool()
        tool.configure({"chain": "ethereum"})

        assert tool.default_chain == "ethereum"


class TestTechnicalAnalysisToolExecute:
    """Test TechnicalAnalysisTool.execute method."""

    @pytest.fixture
    def mock_ohlcv_response(self):
        """Create mock OHLCV API response with sufficient data."""
        np.random.seed(42)
        n = 250
        base_price = 100.0
        prices = [base_price]
        for _ in range(n - 1):
            prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))

        items = []
        base_time = 1700000000
        for i, price in enumerate(prices):
            items.append(
                {
                    "o": price * 0.99,
                    "h": price * 1.01,
                    "l": price * 0.98,
                    "c": price,
                    "v": 1000000 + np.random.random() * 1000000,
                    "v_usd": 100000000,
                    "unix_time": base_time + i * 14400,  # 4h intervals
                }
            )

        return {"success": True, "data": {"items": items}}

    @pytest.fixture
    def mock_overview_response(self):
        """Create mock token overview response."""
        return {
            "success": True,
            "data": {
                "address": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "name": "Wrapped SOL",
                "decimals": 9,
                "price": 185.83,
                "history24hPrice": 180.50,
                "priceChange24hPercent": 2.95,
                "marketCap": 100000000000,
                "liquidity": 25000000000,
            },
        }

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ohlcv_response, mock_overview_response):
        """Should return successful analysis with valid data."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        with patch.object(
            tool, "_get_ohlcv_data", new_callable=AsyncMock
        ) as mock_ohlcv:
            with patch.object(
                tool, "_get_token_overview", new_callable=AsyncMock
            ) as mock_overview:
                mock_ohlcv.return_value = mock_ohlcv_response
                mock_overview.return_value = mock_overview_response

                result = await tool.execute(
                    address="So11111111111111111111111111111111111111112",
                    timeframe="4h",
                )

        assert result["status"] == "success"
        assert "token" in result
        assert "analysis" in result
        assert "current" in result
        assert "trend" in result
        assert "momentum" in result
        assert "volatility" in result
        assert "volume" in result

    @pytest.mark.asyncio
    async def test_execute_invalid_timeframe(self):
        """Should return error for invalid timeframe."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        result = await tool.execute(
            address="So11111111111111111111111111111111111111112",
            timeframe="invalid",
        )

        assert result["status"] == "error"
        assert result["error"] == "invalid_timeframe"

    @pytest.mark.asyncio
    async def test_execute_insufficient_data(self, mock_overview_response):
        """Should return error when insufficient candles."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        # Mock with only 50 candles
        insufficient_response = {
            "success": True,
            "data": {
                "items": [
                    {"o": 100, "h": 101, "l": 99, "c": 100.5, "v": 1000000, "unix_time": 1700000000 + i * 14400}
                    for i in range(50)
                ]
            },
        }

        with patch.object(
            tool, "_get_ohlcv_data", new_callable=AsyncMock
        ) as mock_ohlcv:
            with patch.object(
                tool, "_get_token_overview", new_callable=AsyncMock
            ) as mock_overview:
                mock_ohlcv.return_value = insufficient_response
                mock_overview.return_value = mock_overview_response

                result = await tool.execute(
                    address="So11111111111111111111111111111111111111112",
                    timeframe="4h",
                )

        assert result["status"] == "error"
        assert result["error"] == "insufficient_data"
        assert result["candles_available"] == 50
        assert result["candles_required"] == MIN_CANDLES_REQUIRED

    @pytest.mark.asyncio
    async def test_execute_no_data(self, mock_overview_response):
        """Should return error when no OHLCV data."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        empty_response = {"success": True, "data": {"items": []}}

        with patch.object(
            tool, "_get_ohlcv_data", new_callable=AsyncMock
        ) as mock_ohlcv:
            with patch.object(
                tool, "_get_token_overview", new_callable=AsyncMock
            ) as mock_overview:
                mock_ohlcv.return_value = empty_response
                mock_overview.return_value = mock_overview_response

                result = await tool.execute(
                    address="So11111111111111111111111111111111111111112",
                    timeframe="4h",
                )

        assert result["status"] == "error"
        assert result["error"] == "no_data"

    @pytest.mark.asyncio
    async def test_execute_api_failure(self):
        """Should return error on API failure."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        with patch.object(
            tool, "_get_ohlcv_data", new_callable=AsyncMock
        ) as mock_ohlcv:
            with patch.object(
                tool, "_get_token_overview", new_callable=AsyncMock
            ) as mock_overview:
                mock_ohlcv.return_value = {"success": False, "message": "API error"}
                mock_overview.return_value = {"success": False}

                result = await tool.execute(
                    address="So11111111111111111111111111111111111111112",
                    timeframe="4h",
                )

        assert result["status"] == "error"
        assert result["error"] == "api_error"

    @pytest.mark.asyncio
    async def test_execute_timeframe_case_insensitive(
        self, mock_ohlcv_response, mock_overview_response
    ):
        """Timeframe should be case insensitive."""
        tool = TechnicalAnalysisTool()
        tool.configure({"api_key": "test-key"})

        with patch.object(
            tool, "_get_ohlcv_data", new_callable=AsyncMock
        ) as mock_ohlcv:
            with patch.object(
                tool, "_get_token_overview", new_callable=AsyncMock
            ) as mock_overview:
                mock_ohlcv.return_value = mock_ohlcv_response
                mock_overview.return_value = mock_overview_response

                result = await tool.execute(
                    address="So11111111111111111111111111111111111111112",
                    timeframe="4H",  # Uppercase
                )

        assert result["status"] == "success"


# =============================================================================
# Tests for Plugin
# =============================================================================


class TestTechnicalAnalysisPlugin:
    """Test TechnicalAnalysisPlugin class."""

    def test_plugin_name(self):
        """Plugin should have correct name."""
        plugin = TechnicalAnalysisPlugin()
        assert plugin.name == "technical_analysis"

    def test_plugin_description(self):
        """Plugin should have description."""
        plugin = TechnicalAnalysisPlugin()
        assert "technical analysis" in plugin.description.lower()

    def test_plugin_initialize(self):
        """Plugin should initialize tool."""
        plugin = TechnicalAnalysisPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        assert plugin._tool is not None
        assert isinstance(plugin._tool, TechnicalAnalysisTool)


class TestGetPlugin:
    """Test get_plugin function."""

    def test_get_plugin_returns_plugin(self):
        """get_plugin should return TechnicalAnalysisPlugin instance."""
        plugin = get_plugin()

        assert isinstance(plugin, TechnicalAnalysisPlugin)
        assert plugin.name == "technical_analysis"
