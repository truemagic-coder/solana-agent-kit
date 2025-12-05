# DFlow Prediction Market API - Implementation Scope Document

**Date:** December 4, 2025  
**Status:** REVISED - Safety-First Approach  
**Priority:** First-to-market with risk guardrails  

---

## Executive Summary

DFlow has released a Prediction Market API for Solana. We will implement a **lean, safety-focused** integration that prioritizes:

1. **Risk reduction** - Filter out scammy/low-quality markets
2. **Simplicity** - Agent-friendly single request/response pattern  
3. **Discovery** - Help users find legitimate, active markets

### What We WON'T Build
- ❌ Candlestick endpoints (agents can't render charts)
- ❌ Forecast history endpoints (no visualization)
- ❌ Live data Kalshi relay (complexity, low value)
- ❌ Declarative/intent swaps (unnecessary complexity)
- ❌ Raw swap-instructions (we use /order)
- ❌ Sports-specific filters (use general filters)

### What We WILL Build
- ✅ Market discovery with quality filters
- ✅ Safety scoring/warnings
- ✅ Simple buy/sell with blocking execution
- ✅ Position tracking
- ✅ Platform fee collection

---

## The Prediction Market Scam Problem ⚠️

Unlike tokens where we have RugCheck, **there is no equivalent for prediction markets**.

### Known Risks

| Risk | Description | Our Mitigation |
|------|-------------|----------------|
| **Insider creation** | Create market, scoop cheap, news breaks, profit | Age filter, volume threshold |
| **Resolution manipulation** | Ambiguous criteria, oracle collusion | Prefer verified series, warn on unclear rules |
| **Wash trading** | Fake volume to lure bettors | Liquidity + unique traders check |
| **Rug resolution** | Market never resolves or resolves incorrectly | Prefer established series (elections, sports) |
| **Low liquidity traps** | Can enter but can't exit | Min liquidity threshold |

### What We CAN Detect (Limited)
- ✅ Market age (avoid brand new)
- ✅ Volume thresholds (skip dead markets)
- ✅ Liquidity minimums (can actually exit)
- ✅ Active trading (recent trades)
- ✅ Known series (elections, major sports)

### What We CANNOT Detect
- ❌ Insider knowledge
- ❌ Future resolution fairness
- ❌ Creator edge/information asymmetry
- ❌ Oracle manipulation

### Safety Response Format

Every market query will include a `safety` object:

```python
{
    "safety": {
        "score": "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN",
        "warnings": [
            "New market (< 7 days old)",
            "Low volume (< $1,000)",
            "Low liquidity",
            "Unclear resolution criteria",
            "Unknown series"
        ],
        "recommendation": "PROCEED" | "CAUTION" | "AVOID"
    }
}
```

---

## Quality Filters (Applied by Default)

```python
DEFAULT_QUALITY_FILTERS = {
    "min_volume_usd": 1000,        # Skip dead markets
    "min_liquidity_usd": 500,      # Must be able to exit
    "min_age_hours": 24,           # Avoid brand new scams
    "status": ["active"],          # Only tradeable markets
    "exclude_series": [],          # Blacklist known bad series
    "prefer_verified": True,       # Boost established series
}
```

Users can override with `include_risky=True` to see all markets (with warnings).

---

## Async Execution - Blocking Wait Pattern

The agent cannot poll. We handle async internally:

```python
async def _execute_order(self, order_response: dict) -> dict:
    """Execute order with internal polling for async mode."""
    
    if order_response["executionMode"] == "sync":
        # Simple: sign, send, done
        return await self._sign_and_send(order_response["transaction"])
    
    # Async: poll until complete or timeout
    max_wait = 90  # seconds
    poll_interval = 2
    start = time.time()
    
    while time.time() - start < max_wait:
        # Sign and send current transaction
        sig = await self._sign_and_send(order_response["transaction"])
        
        # Wait briefly for processing
        await asyncio.sleep(poll_interval)
        
        # Check status
        status = await self._check_order_status(order_response["requestId"])
        
        if status["status"] == "closed":
            return {"success": True, "signature": sig, "fills": status["fills"]}
        elif status["status"] in ("failed", "expired"):
            return {"success": False, "error": f"Order {status['status']}"}
        elif status.get("nextTransaction"):
            order_response["transaction"] = status["nextTransaction"]
    
    return {"success": False, "error": "Timeout (90s) waiting for order completion"}
```

The tool returns only after the order is fully complete or failed.

---

## Lean API Scope

### Endpoints We Use (12 total)

| Category | Endpoint | Purpose |
|----------|----------|---------|
| **Discovery** | `/events` | List events with filters |
| | `/event/{id}` | Get event details |
| | `/markets` | List markets with filters |
| | `/market/{id}` | Get market details |
| | `/market/by-mint/{addr}` | Lookup by mint |
| | `/search` | Text search |
| | `/series` | List series (for verification) |
| | `/tags_by_categories` | Get categories |
| **Trading** | `/order` | Get quote + transaction |
| | `/order-status` | Check async completion |
| **Reference** | `/trades` | Recent trades (activity check) |
| | `/outcome_mints` | Map mints to markets |

### Endpoints We Skip (21 total)

- All candlestick endpoints (4) - no charts
- All forecast history endpoints (2) - no viz
- All live data endpoints (3) - Kalshi relay, complexity
- `/markets/batch` - unnecessary optimization
- `/filter_outcome_mints` - edge case
- `/series/{ticker}` - series list is enough
- `/filters_by_sports` - use general filters
- `/quote`, `/swap`, `/swap-instructions` - use /order
- `/intent`, `/submit-intent` - declarative too complex
- `/tokens`, `/tokens-with-decimals` - static, not needed
- `/venues` - internal routing

---

## Tool Design

### Single Tool: `dflow_prediction`

**Actions (8 total):**

| Action | Description | Safety |
|--------|-------------|--------|
| `search` | Search markets by text | Returns with safety scores |
| `list_events` | List events (filtered) | Default quality filters |
| `get_event` | Get specific event | Includes safety assessment |
| `list_markets` | List markets (filtered) | Default quality filters |
| `get_market` | Get market details | Includes safety assessment |
| `buy` | Buy YES/NO tokens | Blocks until complete |
| `sell` | Sell outcome tokens | Blocks until complete |
| `positions` | Get user's positions | Show current holdings |

### Removed Actions (vs original scope)
- ❌ `get_trades` - Use trade count in safety score instead
- ❌ `list_series` - Bake into safety scoring
- ❌ `get_categories` - Static, document in README
- ❌ `redeem` - Same as `sell` for determined markets
- ❌ `order_status` - Handled internally

---

## Configuration

```python
config = {
    "tools": {
        "dflow_prediction": {
            # Required
            "private_key": "...",           # Base58 private key
            "rpc_url": "https://...",       # Helius RPC URL
            
            # Optional - Platform fees
            "platform_fee_bps": 50,         # 0.5% fee
            "fee_account": "...",           # USDC token account
            
            # Optional - Safety overrides
            "min_volume_usd": 1000,         # Override default
            "min_liquidity_usd": 500,       # Override default
            "include_risky": False,         # Show all markets
        }
    }
}
```

---

## Safety Scoring Algorithm

```python
def calculate_safety_score(market: dict, trades: list) -> SafetyResult:
    warnings = []
    score_points = 100
    
    # Age check
    age_hours = (now - market["created_at"]) / 3600
    if age_hours < 24:
        warnings.append("New market (< 24 hours old)")
        score_points -= 30
    elif age_hours < 168:  # 7 days
        warnings.append("Young market (< 7 days old)")
        score_points -= 15
    
    # Volume check
    if market["volume"] < 1000:
        warnings.append(f"Low volume (${market['volume']:,.0f})")
        score_points -= 25
    elif market["volume"] < 10000:
        warnings.append(f"Moderate volume (${market['volume']:,.0f})")
        score_points -= 10
    
    # Liquidity check
    if market["liquidity"] < 500:
        warnings.append("Low liquidity - may be hard to exit")
        score_points -= 30
    elif market["liquidity"] < 2000:
        warnings.append("Moderate liquidity")
        score_points -= 10
    
    # Activity check
    recent_trades = [t for t in trades if t["time"] > now - 86400]
    if len(recent_trades) == 0:
        warnings.append("No trades in 24 hours")
        score_points -= 20
    
    # Series verification
    known_series = ["US-POLITICS", "NFL", "NBA", "CRYPTO", ...]
    if market["series_ticker"] not in known_series:
        warnings.append("Unknown/unverified series")
        score_points -= 15
    
    # Resolution clarity
    if not market.get("rules_primary") or len(market["rules_primary"]) < 50:
        warnings.append("Unclear resolution criteria")
        score_points -= 20
    
    # Calculate final
    if score_points >= 70:
        return SafetyResult("HIGH", warnings, "PROCEED")
    elif score_points >= 40:
        return SafetyResult("MEDIUM", warnings, "CAUTION")
    else:
        return SafetyResult("LOW", warnings, "AVOID")
```

---

## Example Responses

### Search Result (with safety)

```json
{
    "events": [
        {
            "ticker": "PRES-2028-DEM",
            "title": "2028 Democratic Nominee",
            "volume": 125000,
            "liquidity": 45000,
            "safety": {
                "score": "HIGH",
                "warnings": [],
                "recommendation": "PROCEED"
            },
            "markets": [
                {
                    "ticker": "PRES-2028-DEM-HARRIS",
                    "title": "Will Kamala Harris be the nominee?",
                    "yes_price": "0.35",
                    "no_price": "0.65"
                }
            ]
        },
        {
            "ticker": "RANDOM-STUFF-123",
            "title": "Will my cat sleep today?",
            "volume": 50,
            "liquidity": 20,
            "safety": {
                "score": "LOW",
                "warnings": [
                    "Low volume ($50)",
                    "Low liquidity",
                    "Unknown/unverified series",
                    "Young market (< 7 days)"
                ],
                "recommendation": "AVOID"
            }
        }
    ]
}
```

### Buy Result

```json
{
    "success": true,
    "action": "buy",
    "market": "PRES-2028-DEM-HARRIS",
    "side": "YES",
    "amount_in": "10 USDC",
    "tokens_received": "28.57 YES",
    "avg_price": "0.35",
    "signature": "5xyz...",
    "execution_mode": "sync"
}
```

---

## Implementation Plan

### Phase 1: Client + Safety (8-10 hours)
- [ ] `sakit/utils/dflow.py` - API client with 12 endpoints
- [ ] Safety scoring algorithm
- [ ] Trade activity fetching
- [ ] Tests with mocks

### Phase 2: Tool (6-8 hours)
- [ ] `sakit/dflow_prediction.py` - 8 actions
- [ ] Blocking async execution
- [ ] Platform fee support
- [ ] 100% test coverage

### Phase 3: Testing (4-6 hours)
- [ ] Unit tests
- [ ] Integration tests against live API
- [ ] Edge cases (async timeouts, low liquidity)

### Phase 4: Documentation (2 hours)
- [ ] README section
- [ ] Safety warnings documentation
- [ ] Example usage

**Total: 20-26 hours** (reduced from 28-39)

---

## Success Criteria

1. ✅ 12 API endpoints implemented (lean)
2. ✅ Safety scoring on all market queries
3. ✅ Quality filters applied by default
4. ✅ Blocking async execution (no polling for agent)
5. ✅ 100% test coverage
6. ✅ Clear warnings in responses
7. ✅ Platform fee collection working

---

## API Endpoint Summary

| Category | Count | Endpoints |
|----------|-------|-----------|
| Discovery | 8 | `/events`, `/event/{id}`, `/markets`, `/market/{id}`, `/market/by-mint/{addr}`, `/search`, `/series`, `/tags_by_categories` |
| Trading | 2 | `/order`, `/order-status` |
| Reference | 2 | `/trades`, `/outcome_mints` |
| **TOTAL** | **12** | (reduced from 33) |

---

## Risk Documentation for Users

The tool will include this warning in its description:

> **⚠️ PREDICTION MARKET RISKS**
>
> Unlike token swaps, prediction markets carry unique risks that cannot be fully detected:
> - **Insider trading**: Market creators may have privileged information
> - **Resolution risk**: Markets may resolve unfairly or not at all  
> - **Liquidity traps**: You may not be able to exit your position
>
> This tool applies safety filters and provides warnings, but **cannot guarantee market legitimacy**.
> Only bet what you can afford to lose. Prefer established series (major elections, sports).

---

## Next Steps

1. Review and approve this revised scope
2. Begin Phase 1: Client + Safety scoring
3. Iterate with continuous testing

**Ready to proceed with lean, safety-first implementation?**
