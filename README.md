# Solana Agent Kit

[![PyPI - Version](https://img.shields.io/pypi/v/sakit)](https://pypi.org/project/sakit)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/sakit)](https://pypi.org/project/sakit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://img.shields.io/codecov/c/github/truemagic-coder/solana-agent-kit/main.svg)](https://codecov.io/gh/truemagic-coder/solana-agent-kit)
[![Build Status](https://img.shields.io/github/actions/workflow/status/truemagic-coder/solana-agent-kit/ci.yml?branch=main)](https://github.com/truemagic-coder/solana-agent-kit/actions/workflows/ci.yml)
[![Ruff Style](https://img.shields.io/badge/style-ruff-41B5BE)](https://github.com/astral-sh/ruff)

A collection of powerful plugins to extend the capabilities of Solana Agent.

## 🚀 Features
Solana Agent Kit provides a growing library of plugins that enhance your Solana Agent with new capabilities:

* Solana Transfer - Transfer Solana tokens between the agent's wallet and the destination wallet
* Solana Ultra - Swap Solana tokens using Jupiter Ultra API with automatic slippage, priority fees, and transaction landing
* Solana DFlow Swap - Fast token swaps using DFlow API
* Jupiter Trigger - Create, cancel, and manage limit orders using Jupiter Trigger API
* Jupiter Recurring - Create, cancel, and manage DCA orders using Jupiter Recurring API
* Jupiter Holdings - Get token holdings with USD values for any wallet
* Jupiter Shield - Get security warnings and risk information for tokens
* Jupiter Token Search - Search for tokens by symbol, name, or address
* DFlow Prediction - Trade prediction markets with safety scoring and quality filters
* Privy DFlow Prediction - Trade prediction markets with Privy delegated wallets
* Privy Transfer - Transfer tokens using Privy delegated wallets with sponsored transactions
* Privy Ultra - Swap tokens using Jupiter Ultra with Privy delegated wallets
* Privy Trigger - Create and manage limit orders with Privy delegated wallets
* Privy Recurring - Create and manage DCA orders with Privy delegated wallets
* Privy DFlow Swap - Fast token swaps using DFlow API with Privy delegated wallets
* Privy Wallet Address - Get the wallet address of a Privy delegated wallet
* Privy Create User - Create a new Privy user with a linked Telegram account (for bot-first flows)
* Privy Create Wallet - Create a Solana wallet for a Privy user with optional bot delegation
* Privy Get User by Telegram - Look up an existing Privy user by their Telegram ID
* Rugcheck - Check if a token is a rug
* Vybe - Look up and label known Solana wallets (CEX, market makers, AMM pools, treasuries)
* Birdeye - Comprehensive token analytics including prices, OHLCV, trades, wallet data, trending tokens, top traders, and more
* Internet Search - Search the internet in real-time using Perplexity, Grok, or OpenAI
* MCP - Interface with MCP web servers
* Image Generation - Generate images with OpenAI, Grok, or Gemini with uploading to S3 compatible storage
* Technical Analysis - Comprehensive technical indicators (EMA, SMA, MACD, RSI, Bollinger Bands, etc.) for any token using Birdeye OHLCV data
* Token Math - Reliable token amount calculations for swaps, limit orders, and transfers (LLMs are bad at math!)

## 📦 Installation

```bash
pip install sakit
```

## 🔌 Plugins

### Solana Transfer

This plugin enables Solana Agent to transfer SOL and SPL tokens from the agent's wallet to the destination wallet.

Don't use tickers - but mint addresses in your user queries.

```python
config = {
    "tools": {
        "solana_transfer": {
            "rpc_url": "my-rpc-url", # Required - your RPC URL - Helius is recommended
            "private_key": "my-private-key", # Required - base58 string - please use env vars to store the key as it is very confidential
        },
    },
}
```

### Solana Ultra

This plugin enables Solana Agent to swap tokens using Jupiter Ultra API. Jupiter Ultra automatically handles slippage, priority fees, and transaction landing for reliable swaps.

Don't use tickers - but mint addresses in your user queries.

```python
config = {
    "tools": {
        "solana_ultra": {
            "private_key": "my-private-key", # Required - base58 string - please use env vars to store the key as it is very confidential
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag (60 req/min on free tier)
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY", # Required - Helius RPC for reliable tx sending
            "referral_account": "my-referral-account", # Optional - your Jupiter referral account public key for collecting fees
            "referral_fee": 50, # Optional - fee in basis points (50-255 bps, e.g., 50 = 0.5%). Jupiter takes 20% of this fee.
            "payer_private_key": "payer-private-key", # Optional - base58 private key for gasless transactions (integrator pays gas)
        },
    },
}
```

**Features:**
- **Jupiter Ultra API**: Access to competitive pricing with automatic slippage protection
- **Helius RPC**: Transactions sent directly via RPC instead of Jupiter's execute endpoint for reliability
- **Priority Fees**: Automatically calculated to ensure transaction landing
- **Referral Fees**: Optionally collect integrator fees (50-255 bps) via your Jupiter referral account
- **Integrator Gas Payer**: Optionally pay for gas on behalf of users for truly gasless swaps

**API Key (Required):**
Get a free Jupiter API key at [portal.jup.ag](https://portal.jup.ag). The free tier provides 60 requests per minute. The lite API (no key) was deprecated on December 31, 2025.

**RPC URL (Required):**
Transactions are sent directly via your RPC instead of Jupiter's `/execute` endpoint, which can have reliability issues. Helius RPC is recommended (`https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`). Get a free API key at [helius.dev](https://helius.dev).

**Setting up Referral Account:**
To collect fees, you need a Jupiter referral account. Create one at [referral.jup.ag](https://referral.jup.ag/). Jupiter takes 20% of the referral fee you set. You also need to create token accounts for the tokens you want to collect fees in.

**Gasless Transactions:**
By default, Jupiter Ultra provides gasless swaps when the user has < 0.01 SOL and trade is > $10. However, this **doesn't work with referral fees**. To enable gasless + referral fees, configure `payer_private_key` - this wallet will pay all gas fees and you recoup costs via referral fees.

### Solana DFlow Swap

This plugin enables Solana Agent to swap tokens using DFlow's Swap API with a Solana keypair. DFlow offers faster swaps compared to Jupiter Ultra with competitive rates.

**Note:** Platform fees are not supported with DFlow. Use Jupiter Ultra (solana_ultra) if you need to collect fees on swaps.

```python
config = {
    "tools": {
        "solana_dflow_swap": {
            "private_key": "my-private-key", # Required - base58 string
            "payer_private_key": "payer-private-key", # Optional - for gasless/sponsored transactions
            "rpc_url": "https://api.mainnet-beta.solana.com", # Optional - RPC URL (defaults to mainnet)
        },
    },
}
```

**Features:**
- **Fast Swaps**: DFlow typically executes faster than Jupiter Ultra
- **Gasless Transactions**: Optionally sponsor gas fees for users via `payer_private_key`

### Jupiter Trigger

This plugin enables Solana Agent to create, cancel, and manage limit orders using Jupiter's Trigger API. It's a smart tool that handles the full lifecycle of limit orders with a single action parameter.

Transactions are sent directly via your RPC (Helius recommended) instead of Jupiter's `/execute` endpoint for improved reliability.

```python
config = {
    "tools": {
        "jupiter_trigger": {
            "private_key": "my-private-key", # Required - base58 string
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=xxx", # Required - Helius RPC URL for transaction sending
            "referral_account": "my-referral-account", # Optional - for collecting fees
            "referral_fee": 50, # Optional - fee in basis points (50-255 bps)
            "payer_private_key": "payer-private-key", # Optional - for gasless transactions
        },
    },
}
```

**Actions:**
- `create` - Create a new limit order (requires input_mint, output_mint, making_amount, taking_amount)
- `cancel` - Cancel a specific order (requires order_pubkey)
- `cancel_all` - Cancel all open orders for the wallet
- `list` - List all orders for the wallet

**Features:**
- **Smart Action Routing**: Single tool handles create, cancel, and list operations
- **Limit Orders**: Set exact prices for token swaps
- **Order Expiry**: Optionally set expiration time for orders
- **Referral Fees**: Collect integrator fees on filled orders
- **Gasless Transactions**: Optionally pay gas on behalf of users

### Jupiter Recurring

This plugin enables Solana Agent to create, cancel, and manage DCA (Dollar Cost Averaging) orders using Jupiter's Recurring API.

```python
config = {
    "tools": {
        "jupiter_recurring": {
            "private_key": "my-private-key", # Required - base58 string
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
            "payer_private_key": "payer-private-key", # Optional - for gasless transactions
        },
    },
}
```

**Actions:**
- `create` - Create a new DCA order (requires input_mint, output_mint, in_amount, order_count, frequency)
- `cancel` - Cancel a specific DCA order (requires order_pubkey)
- `list` - List all DCA orders for the wallet

**Parameters for Create:**
- `input_mint` - Token to sell
- `output_mint` - Token to buy
- `in_amount` - Total amount to DCA (in base units)
- `order_count` - How many orders to split into
- `frequency` - Time between orders in seconds (e.g., '3600' for hourly, '86400' for daily)
- `min_out_amount` / `max_out_amount` - Optional output amount bounds per order
- `start_at` - Optional start time (unix timestamp)

**Features:**
- **Time-Based DCA**: Automatically split large orders over time
- **Amount Bounds**: Set min/max output amount limits per order
- **Flexible Frequency**: Specify interval in seconds
- **Gasless Transactions**: Optionally pay gas on behalf of users

### Jupiter Holdings

This plugin enables Solana Agent to get token holdings with USD values for any wallet address using Jupiter Ultra API.

```python
config = {
    "tools": {
        "jupiter_holdings": {
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
        },
    },
    "agents": [
        {
            "name": "portfolio_analyst",
            "instructions": "You are an expert in analyzing Solana portfolios. Use the jupiter_holdings tool to get wallet token balances.",
            "specialization": "Portfolio analysis",
            "tools": ["jupiter_holdings"],
        }
    ]
}
```

**Returns:**
- Token mint addresses, symbols, and names
- Token balances and USD values
- Total portfolio value in USD

### Jupiter Shield

This plugin enables Solana Agent to get security warnings and risk information for Solana tokens using Jupiter's Shield API.

```python
config = {
    "tools": {
        "jupiter_shield": {
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
        },
    },
    "agents": [
        {
            "name": "security_analyst",
            "instructions": "You are a security expert for Solana tokens. Use the jupiter_shield tool to check token security before trading.",
            "specialization": "Token security analysis",
            "tools": ["jupiter_shield"],
        }
    ]
}
```

**Returns:**
- Security warnings for each token
- Risk flags and descriptions
- Recommended caution levels

### Jupiter Token Search

This plugin enables Solana Agent to search for Solana tokens by symbol, name, or address using Jupiter's search API.

```python
config = {
    "tools": {
        "jupiter_token_search": {
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
        },
    },
    "agents": [
        {
            "name": "token_researcher",
            "instructions": "You are an expert in finding Solana tokens. Use the jupiter_token_search tool to search for tokens.",
            "specialization": "Token research",
            "tools": ["jupiter_token_search"],
        }
    ]
}
```

**Returns:**
- Token mint addresses
- Token symbols and names
- Token metadata (logo, decimals, etc.)


### Privy Transfer

This plugin enables Solana Agent to transfer SOL and SPL tokens using Privy delegated wallets. The fee_payer wallet pays for transaction fees, enabling gasless transfers for users.

```python
config = {
    "tools": {
        "privy_transfer": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key", # Required - your Privy wallet authorization signing key
            "rpc_url": "my-rpc-url", # Required - your RPC URL - Helius is recommended
            "fee_payer": "fee-payer-private-key", # Required - base58 private key for the fee payer wallet
        },
    },
}
```

### Privy Ultra

This plugin enables Solana Agent to swap tokens using Jupiter Ultra API with Privy delegated wallets. Jupiter Ultra automatically handles slippage, priority fees, and transaction landing.

```python
config = {
    "tools": {
        "privy_ultra": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key", # Required - your Privy wallet authorization signing key
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY", # Required - Helius RPC for reliable tx sending
            "referral_account": "my-referral-account", # Optional - your Jupiter referral account public key for collecting fees
            "referral_fee": 50, # Optional - fee in basis points (50-255 bps, e.g., 50 = 0.5%). Jupiter takes 20% of this fee.
            "payer_private_key": "payer-private-key", # Optional - base58 private key for gasless transactions (integrator pays gas)
        },
    },
}
```

**Features:**
- **Jupiter Ultra API**: Access to competitive pricing with automatic slippage protection
- **Privy Delegated Wallets**: Use Privy's embedded wallets with delegation for seamless user experience
- **Helius RPC**: Transactions sent directly via RPC instead of Jupiter's execute endpoint for reliability
- **Referral Fees**: Optionally collect integrator fees (50-255 bps) via your Jupiter referral account
- **Integrator Gas Payer**: Optionally pay for gas on behalf of users for truly gasless swaps

**RPC URL (Required):**
Transactions are sent directly via your RPC instead of Jupiter's `/execute` endpoint, which can have reliability issues. Helius RPC is recommended (`https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`). Get a free API key at [helius.dev](https://helius.dev).

### Privy Trigger

This plugin enables Solana Agent to create, cancel, and manage limit orders using Jupiter's Trigger API with Privy delegated wallets.

```python
config = {
    "tools": {
        "privy_trigger": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key", # Required - your Privy wallet authorization signing key
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY", # Recommended - Helius RPC for reliable tx sending
            "referral_account": "my-referral-account", # Optional - for collecting fees
            "referral_fee": 50, # Optional - fee in basis points (50-255 bps)
            "payer_private_key": "payer-private-key", # Optional - for gasless transactions
        },
    },
}
```

**RPC URL (Recommended):**
If configured, transactions are sent directly via RPC instead of Jupiter's execute endpoint, which can timeout. Helius RPC is recommended for reliable transaction landing.

**Actions:** Same as Jupiter Trigger (create, cancel, cancel_all, list)

### Privy Recurring

This plugin enables Solana Agent to create, cancel, and manage DCA orders using Jupiter's Recurring API with Privy delegated wallets.

```python
config = {
    "tools": {
        "privy_recurring": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key", # Required - your Privy wallet authorization signing key
            "jupiter_api_key": "my-jupiter-api-key", # Required - get free key at portal.jup.ag
            "payer_private_key": "payer-private-key", # Optional - for gasless transactions
        },
    },
}
```

**Actions:** Same as Jupiter Recurring (create, cancel, list)

### Privy DFlow Swap

This plugin enables Solana Agent to swap tokens using DFlow's Swap API with Privy delegated wallets. DFlow offers faster swaps compared to Jupiter Ultra with competitive rates.

**Note:** Platform fees are not supported with DFlow. Use Privy Ultra (Jupiter) if you need to collect fees on swaps.

Transactions are signed via Privy and sent via your configured RPC (Helius recommended) for reliable blockhash handling and priority fees.

**Note:** Platform fees are not supported with DFlow. Use Jupiter Ultra (privy_ultra) if you need to collect fees on swaps.

```python
config = {
    "tools": {
        "privy_dflow_swap": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key", # Required - your Privy wallet authorization signing key
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY", # Required - Helius recommended for priority fees
            "payer_private_key": "payer-private-key", # Optional - for gasless/sponsored transactions
        },
    },
}
```

**Features:**
- **Fast Swaps**: DFlow typically executes faster than Jupiter Ultra
- **Privy Delegated Wallets**: Seamless user experience with embedded wallets
- **Helius Priority Fees**: Uses Helius priority fee estimation for reliable transaction landing
- **Gasless Transactions**: Optionally sponsor gas fees for users via `payer_private_key`

**RPC URL (Required):**
Helius RPC is strongly recommended (`https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`). Helius provides priority fee estimation and better blockhash handling, which significantly improves transaction success rates. Get a free API key at [helius.dev](https://helius.dev).

### Privy Wallet Address

This plugin enables Solana Agent to get the wallet address of a Privy delegated wallet.

```python
config = {
    "tools": {
        "privy_wallet_address": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
        },
    },
}
```

### Privy Create User

This plugin enables Solana Agent to create a new Privy user with a linked Telegram account. Used for **bot-first** Telegram bot flows where users first interact with the bot and wallets are created server-side.

```python
config = {
    "tools": {
        "privy_create_user": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
        },
    },
}
```

**Parameters:**
- `telegram_user_id` (required) - The Telegram user ID to link to the new Privy user

**Returns:**
- `user_id` - The Privy user ID (did:privy:...)
- `created_at` - Unix timestamp of when the user was created
- `linked_accounts` - List of linked accounts including the Telegram account

### Privy Create Wallet

This plugin enables Solana Agent to create a new Solana wallet for a Privy user with optional bot delegation. When `add_bot_signer` is true, the bot can execute transactions on behalf of the user.

**Prerequisites:**
1. Create an authorization key locally:
   ```bash
   openssl ecparam -name prime256v1 -genkey -noout -out private.pem
   openssl ec -in private.pem -pubout -outform DER | base64
   ```
2. Register the public key as a key quorum in the [Privy Dashboard](https://dashboard.privy.io/apps?authorization-keys)
3. Save the key quorum ID as `signer_id` in the config

```python
config = {
    "tools": {
        "privy_create_wallet": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
            "signer_id": "your-key-quorum-id", # Required if add_bot_signer=True - the key quorum ID from Privy Dashboard
            "policy_ids": [], # Optional - list of policy IDs to apply to the signer for restricted permissions
        },
    },
}
```

**Parameters:**
- `user_id` (required) - The Privy user ID (did:privy:...) to create a wallet for
- `chain_type` (optional) - "solana" or "ethereum" (default: "solana")
- `add_bot_signer` (optional) - Whether to add the bot as an additional signer for delegation (default: true)

**Returns:**
- `wallet_id` - The Privy wallet ID
- `address` - The wallet's public address
- `chain_type` - The blockchain type
- `additional_signers` - List of additional signers (including bot if enabled)

### Privy Get User by Telegram

This plugin enables Solana Agent to look up an existing Privy user by their Telegram user ID. Useful for checking if a user already has a Privy account and wallet before creating a new one.

```python
config = {
    "tools": {
        "privy_get_user_by_telegram": {
            "app_id": "your-privy-app-id", # Required - your Privy application ID
            "app_secret": "your-privy-app-secret", # Required - your Privy application secret
        },
    },
}
```

**Parameters:**
- `telegram_user_id` (required) - The Telegram user ID to look up

**Returns:**
- `status` - "success" if found, "not_found" if no user exists
- `user_id` - The Privy user ID (did:privy:...)
- `wallets` - List of embedded wallets with address, chain_type, and delegation status
- `has_wallet` - Boolean indicating if the user has at least one wallet

### DFlow Prediction Market

This plugin enables Solana Agent to discover and trade prediction markets on Solana via DFlow's Prediction Market API. It includes safety-first features to help users avoid scams.

⚠️ **PREDICTION MARKET RISKS:**
Unlike token swaps, prediction markets carry unique risks that cannot be fully detected:
- **Insider trading**: Market creators may have privileged information
- **Resolution risk**: Markets may resolve unfairly or not at all
- **Liquidity traps**: You may not be able to exit your position

This tool applies safety filters and provides warnings, but cannot guarantee market legitimacy. Only bet what you can afford to lose. Prefer established series (major elections, sports).

```python
config = {
    "tools": {
        "dflow_prediction": {
            "private_key": "my-private-key",  # Required for trading - base58 string
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY",  # Required for trading
            
            # Optional - Platform fee collection
            "platform_fee_bps": 50,  # Fee in basis points (0.5%)
            "fee_account": "your-usdc-token-account",  # Account to receive fees
            
            # Optional - Quality filters (defaults shown)
            "min_volume_usd": 1000,  # Minimum market volume
            "min_liquidity_usd": 500,  # Minimum market liquidity
            "include_risky": False,  # Show low-quality markets (with warnings)
        },
    },
}
```

**Features:**
- **Safety Scoring**: Every market gets a safety score (HIGH/MEDIUM/LOW) with warnings
- **Quality Filters**: Low-volume and low-liquidity markets filtered by default
- **Risk Warnings**: Clear warnings about unverified series, new markets, unclear rules
- **Blocking Execution**: Async orders poll internally so agent gets single response
- **Platform Fees**: Collect fees on all trades via Jupiter Referral Program

**Actions:**

Discovery:
- `search` - Search markets by text query (e.g., "trump", "bitcoin")
- `list_events` - List prediction events with filters (status, sort, series)
- `get_event` - Get specific event details with safety score
- `list_markets` - List prediction markets with filters
- `get_market` - Get market details including YES/NO token mints

Trading:
- `buy` - Buy YES or NO outcome tokens with USDC
- `sell` - Sell outcome tokens back to USDC
- `positions` - Get hints for checking prediction market positions

**Safety Scores:**
- **HIGH** (PROCEED): Established market, good volume/liquidity, verified series
- **MEDIUM** (CAUTION): Some warnings (moderate volume, young market)
- **LOW** (AVOID): Multiple red flags (low volume, unclear rules, unknown series)

**Example - Search and Buy:**
```
User: "Search for prediction markets about the 2028 election"
Agent uses dflow_prediction action="search" query="2028 election"

User: "Buy $10 of YES on Kamala Harris winning"
Agent uses dflow_prediction action="buy" market_id="PRES-2028-DEM-HARRIS" side="YES" amount=10
```

### Privy DFlow Prediction

This plugin enables Solana Agent to discover and trade prediction markets on Solana via DFlow's Prediction Market API using Privy delegated wallets. Same features as DFlow Prediction but for Privy embedded wallet users.

```python
config = {
    "tools": {
        "privy_dflow_prediction": {
            "app_id": "your-privy-app-id",  # Required - your Privy application ID
            "app_secret": "your-privy-app-secret",  # Required - your Privy application secret
            "signing_key": "wallet-auth:your-signing-key",  # Required - your Privy wallet authorization signing key
            "rpc_url": "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY",  # Required for trading
            
            # Optional - Platform fee collection
            "platform_fee_bps": 50,  # Fee in basis points (0.5%)
            "fee_account": "your-usdc-token-account",  # Account to receive fees
            
            # Optional - Quality filters (defaults shown)
            "min_volume_usd": 1000,  # Minimum market volume
            "min_liquidity_usd": 500,  # Minimum market liquidity
            "include_risky": False,  # Show low-quality markets (with warnings)
            
            # Optional - Gasless transactions
            "payer_private_key": "payer-private-key",  # For sponsored transactions
        },
    },
}
```

**Features:**
- Same safety scoring and quality filters as DFlow Prediction
- **Privy Delegated Wallets**: Seamless user experience with embedded wallets
- **Gasless Transactions**: Optionally sponsor gas fees for users via `payer_private_key`

**Actions:** Same as DFlow Prediction (search, list_events, get_event, list_markets, get_market, buy, sell, positions)

**Parameters:**
- All DFlow Prediction parameters plus:
- `privy_user_id` (required for trading) - Privy user ID (did:privy:xxx format)

### Rugcheck

This plugin enables Solana Agent to check if a token is a rug. 

No config is needed.

### Vybe

This plugin enables Solana Agent to look up and label known Solana wallet addresses using the Vybe Network API. It identifies CEX wallets, market makers, AMM pools, project treasuries, and influencers - useful for understanding who owns wallets when analyzing top holders or traders.

The tool caches the known accounts list in memory (1 hour TTL) and performs fast bulk lookups.

```python
config = {
    "tools": {
        "vybe": {
            "api_key": "your-vybe-api-key",  # Required - get your API key from vybenetwork.com
        },
    },
    "agents": [
        {
            "name": "wallet_analyst",
            "instructions": "You are an expert at analyzing Solana wallets. When showing top holders or traders, use the vybe tool to identify known accounts like CEX wallets or market makers.",
            "specialization": "Wallet analysis and labeling",
            "tools": ["birdeye", "vybe"],  # Often used together with birdeye
        }
    ]
}
```

**Parameters:**
- `addresses` (required) - Comma-separated list of wallet addresses to look up
- `refresh_cache` (optional) - Force refresh the cached known accounts list

**Returns:**
- Labels for each address (CEX, Exchange, AMM, Market Maker, DeFi, etc.)
- Entity names (Binance, Coinbase, Raydium, Wintermute, etc.)
- Summary of known vs unknown wallets

**Example Use Case:**
When querying top holders of a token via Birdeye, pass the wallet addresses to Vybe to identify which are CEX wallets or market makers vs real traders.

### Birdeye

This plugin enables Solana Agent to access comprehensive Solana token analytics via the Birdeye API. It provides 50 actions covering prices, OHLCV data, trades, wallet analytics, token information, and more.

```python
config = {
    "tools": {
        "birdeye": {
            "api_key": "your-birdeye-api-key",  # Required - get your API key from birdeye.so
            "chain": "solana",  # Optional - lock to a specific chain (default: "solana")
        },
    },
    "agents": [
        {
            "name": "token_analyst",
            "instructions": "You are an expert Solana token analyst. Use the birdeye tool to analyze tokens, wallets, and market trends.",
            "specialization": "Token and market analysis",
            "tools": ["birdeye"],
        }
    ]
}
```

**Available Actions:**

*Price Data:*
- `price` - Get current price of a token
- `multi_price` - Get prices for multiple tokens
- `multi_price_post` - Get prices for multiple tokens (POST)
- `history_price` - Get historical price data
- `historical_price_unix` - Get price at specific unix timestamp
- `price_volume_single` - Get price and volume for single token
- `price_volume_multi` - Get price and volume for multiple tokens

*OHLCV Data:*
- `ohlcv` - Get OHLCV candlestick data for a token
- `ohlcv_pair` - Get OHLCV data for a trading pair
- `ohlcv_base_quote` - Get OHLCV for base/quote pair
- `ohlcv_v3` - Get OHLCV v3 for token
- `ohlcv_pair_v3` - Get OHLCV v3 for pair

*Trade Data:*
- `trades_token` - Get recent trades for a token
- `trades_pair` - Get recent trades for a pair
- `trades_token_seek` - Get trades with time bounds
- `trades_pair_seek` - Get pair trades with time bounds
- `trades_v3` - Get trades v3 with filters
- `trades_token_v3` - Get token trades v3

*Token Information:*
- `token_list` - Get list of tokens
- `token_list_v3` - Get token list v3
- `token_list_scroll` - Get token list with pagination
- `token_overview` - Get detailed token overview
- `token_metadata_single` - Get metadata for single token
- `token_metadata_multiple` - Get metadata for multiple tokens
- `token_market_data` - Get market data for single token
- `token_market_data_multiple` - Get market data for multiple tokens
- `token_trade_data_single` - Get trade data for single token
- `token_trade_data_multiple` - Get trade data for multiple tokens
- `token_holder` - Get token holders
- `token_trending` - Get trending tokens
- `token_new_listing` - Get newly listed tokens
- `token_top_traders` - Get top traders for a token
- `token_markets` - Get markets for a token
- `token_security` - Get token security analysis
- `token_creation_info` - Get token creation information
- `token_mint_burn` - Get mint/burn transactions
- `token_all_time_trades_single` - Get all-time trade stats
- `token_all_time_trades_multiple` - Get all-time trade stats for multiple tokens

*Pair Data:*
- `pair_overview_single` - Get overview for single pair
- `pair_overview_multiple` - Get overview for multiple pairs

*Trader Data:*
- `trader_gainers_losers` - Get top gainers and losers
- `trader_txs_seek` - Get trader transactions with time bounds

*Wallet Data:*
- `wallet_token_list` - Get wallet token holdings
- `wallet_token_balance` - Get specific token balance in wallet
- `wallet_tx_list` - Get wallet transaction history
- `wallet_balance_change` - Get wallet balance changes
- `wallet_pnl_summary` - Get PNL summary for a wallet (realized/unrealized profit, win rate, etc.)
- `wallet_pnl_details` - Get PNL details broken down by token (POST, max 100 tokens)
- `wallet_pnl_multiple` - Get PNL for multiple wallets (max 50)
- `wallet_current_net_worth` - Get current net worth and portfolio
- `wallet_net_worth` - Get historical net worth by dates (hourly/daily)
- `wallet_net_worth_details` - Get asset details on a specific date

*Exit Liquidity:*
- `token_exit_liquidity` - Get exit liquidity for a token (available liquidity to exit position)
- `token_exit_liquidity_multiple` - Get exit liquidity for multiple tokens (max 50)

*Search:*
- `search` - Search for tokens/pairs

*Utilities:*
- `latest_block` - Get latest block info
- `networks` - Get supported networks
- `supported_chains` - Get supported chains

**Multi-Chain Support:**
All actions support a `chain` parameter (defaults to "solana"). Birdeye supports multiple chains including Ethereum, BSC, Arbitrum, etc.

### Internet Search
This plugin enables Solana Agent to search the internet for up-to-date information using Perplexity, OpenAI, or Grok.

Please ensure you include a prompt to instruct the agent to use the tool - otherwise it may not use it.

```python
config = {    
    "tools": {
        "search_internet": {
            "api_key": "your-api-key", # Required - either a Perplexity, Grok, or OpenAI API key
            "provider": "openai", # Optional, defaults to openai - can be "openai', "perplexity", or "grok" - grok also searches X
            "citations": True, # Optional, defaults to True - only applies for Perplexity and Grok
            "model": "gpt-4o-mini-search-preview",  # Optional, defaults to "sonar" for Perplexity or "gpt-4o-mini-search-preview" for OpenAI or "grok-4-1-fast-non-reasoning" for Grok
            # Grok-specific options:
            "grok_web_search": True,  # Optional, defaults to True - enable web search
            "grok_x_search": True,    # Optional, defaults to True - enable X/Twitter search
            "grok_timeout": 90,       # Optional, defaults to 90 - timeout in seconds (Grok can be slow)
        }
    },
    "agents": [
        {
            "name": "research_specialist",
            "instructions": "You are an expert researcher who synthesizes complex information clearly. You use your search_internet tool to get the latest information.",
            "specialization": "Research and knowledge synthesis",
            "tools": ["search_internet"],  # Enable the tool for this agent
        }
    ]
}
```

**Grok Performance Tips:**
- Grok search with both web and X search can take 30-90+ seconds
- For faster responses, disable one search type: `grok_x_search: False` or `grok_web_search: False`
- X-only search is useful for real-time social sentiment on crypto/tokens
- Web-only search is faster for general information

**Available Search Models for Perplexity**
* sonar
* sonar-pro

**Available Search Models for OpenAI**
* gpt-4o-mini-search-preview
* gpt-4o-search-preview

**Available Search Models for Grok**
* grok-4-1-fast-non-reasoning
* grok-4-fast
* grok-4.1-fast

### MCP

The MCP plugin supports both OpenAI and Grok as LLM providers for tool selection, and can connect to multiple MCP servers simultaneously with custom headers for each server.

**Single Server Configuration (Simple):**
```python
config = {
    "openai": {
        "api_key": "your-openai-api-key",  # Required if using OpenAI as LLM provider
    },
    "tools": {
        "mcp": {
            "url": "my-zapier-mcp-url",  # Required: Your MCP server URL
            "headers": {  # Optional: Custom headers for authentication/authorization
                "Authorization": "Bearer your-token",
                "X-Custom-Header": "value"
            },
            "llm_provider": "openai",  # Optional: "openai" (default) or "grok"
            "llm_model": "gpt-4.1-mini",  # Optional: defaults to "gpt-4.1-mini" for OpenAI or "grok-4-1-fast-non-reasoning" for Grok
        }
    },
    "agents": [
        {
            "name": "zapier_expert",
            "instructions": "You are an expert in using Zapier integrations using MCP. You always use the mcp tool to perform Zapier AI like actions.",
            "specialization": "Zapier service integration expert",
            "tools": ["mcp"],
        }
    ]
}
```

**Multiple Servers Configuration (Advanced):**
```python
config = {
    "grok": {
        "api_key": "your-grok-api-key",  # Required if using Grok as LLM provider
    },
    "tools": {
        "mcp": {
            "servers": [  # List of MCP servers to connect to
                {
                    "url": "https://zapier-mcp-server.com/api",
                    "headers": {
                        "Authorization": "Bearer zapier-token"
                    }
                },
                {
                    "url": "https://another-mcp-server.com/api",
                    "headers": {
                        "X-API-Key": "another-api-key"
                    }
                }
            ],
            "llm_provider": "grok",  # Use Grok for tool selection
            "llm_model": "grok-4-1-fast-non-reasoning",  # Optional: override default model
        }
    },
    "agents": [
        {
            "name": "mcp_expert",
            "instructions": "You are an expert in using MCP integrations. You always use the mcp tool to perform actions across multiple services.",
            "specialization": "Multi-service integration expert",
            "tools": ["mcp"],
        }
    ]
}
```

**Configuration Options:**
- `llm_provider`: Choose "openai" or "grok" for tool selection (default: "openai")
- `llm_model`: Override the default model for your chosen provider
- `headers`: Add custom HTTP headers for authentication or other purposes
- `servers`: Connect to multiple MCP servers simultaneously (tools from all servers are available)
- `api_key`: Can be provided in the tool config or in the provider-specific config section

### Image Generation

This plugin allows the agent to generate images using OpenAI's `gpt-image-1` model or Grok's `grok-2-image` and upload them to S3-compatible storage. It returns the public URL of the uploaded image.

This has been tested using [Cloudflare R2](https://developers.cloudflare.com/r2/).

```python
config = {
    "tools": {
        "image_gen": {
            "provider": "openai",                                        # Required: either "openai", "grok", or "gemini"
            "api_key": "your-api-key",                                   # Required: your OpenAI or Grok or Gemini API key
            "s3_endpoint_url": "https://your-s3-endpoint.com",           # Required: e.g., https://nyc3.digitaloceanspaces.com
            "s3_access_key_id": "YOUR_S3_ACCESS_KEY",                    # Required: Your S3 access key ID
            "s3_secret_access_key": "YOUR_S3_SECRET_KEY",                # Required: Your S3 secret access key
            "s3_bucket_name": "your-bucket-name",                        # Required: The name of your S3 bucket
            "s3_region_name": "your-region",                             # Optional: e.g., "nyc3", needed by some providers
            "s3_public_url_base": "https://your-cdn-or-bucket-url.com/", # Optional: Custom base URL for public links (include trailing slash). If omitted, a standard URL is constructed.
        }
    },
    "agents": [
        {
            "name": "image_creator",
            "instructions": "You are a creative assistant that generates images based on user descriptions. Use the image_gen tool to create and store the image.",
            "specialization": "Image generation and storage",
            "tools": ["image_gen"],  # Enable the tool for this agent
        }
    ]
}
```

**Image Models Used:**

* OpenAI - `gpt-image-1`
* Grok - `grok-2-image`
* Gemini - `imagen-3.0-generate-002`


### Technical Analysis

This plugin provides comprehensive technical analysis indicators for any token using Birdeye OHLCV data. It calculates indicators using the `pandas-ta` library and returns raw values without interpretation (your agent/app handles the interpretation).

**Requires a Birdeye API key** (same as the `birdeye` tool).

```python
config = {
    "tools": {
        "technical_analysis": {
            "api_key": "your-birdeye-api-key",  # Required: Your Birdeye API key
        }
    },
    "agents": [
        {
            "name": "technical_analyst",
            "instructions": """You are a crypto technical analyst. Use the technical_analysis tool to get indicator values for tokens.
            
            IMPORTANT: The tool returns RAW indicator values. YOU must interpret them:
            - RSI > 70 = overbought, RSI < 30 = oversold
            - Price above upper Bollinger Band = overbought
            - MACD above signal line = bullish momentum
            - ADX > 25 = strong trend
            - Price above key EMAs = bullish structure
            
            Always explain what the indicators mean for the user.""",
            "specialization": "Technical analysis and trading signals",
            "tools": ["technical_analysis", "birdeye"],
        }
    ]
}
```

**Parameters:**
- `token_address` (required) - The token's contract address (mint address on Solana)
- `timeframe` (optional) - Candle timeframe: "1m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "1d" (default: "4h")

**Indicators Returned:**

*Moving Averages:*
- EMA 9, 21, 50, 200
- SMA 20, 50, 200

*Momentum:*
- MACD (line, signal, histogram)
- RSI (14)
- Stochastic (K, D)
- Williams %R
- ROC (Rate of Change)
- MFI (Money Flow Index)
- CCI (Commodity Channel Index)
- ADX with +DI/-DI

*Volatility:*
- Bollinger Bands (upper, middle, lower, bandwidth, %B)
- ATR (Average True Range)
- Keltner Channels (upper, middle, lower)

*Volume:*
- OBV (On-Balance Volume)
- VWAP

*Price vs Indicators:*
Returns percentage difference between current price and key levels (EMA 50/200, Bollinger bands, etc.) for quick analysis.

**Example Response Structure:**
```json
{
  "token_address": "So11111111111111111111111111111111111111112",
  "timeframe": "4h",
  "current_price": 142.50,
  "symbol": "SOL",
  "name": "Wrapped SOL",
  "moving_averages": {
    "ema_9": 141.23,
    "ema_21": 140.15,
    "ema_50": 138.90,
    "ema_200": 125.45,
    "sma_20": 140.80,
    "sma_50": 139.20,
    "sma_200": 126.30
  },
  "momentum": {
    "macd": {"macd": 1.25, "signal": 0.98, "histogram": 0.27},
    "rsi": 58.5,
    "stochastic": {"k": 65.2, "d": 62.1},
    "adx": {"adx": 28.5, "plus_di": 25.3, "minus_di": 18.7}
  },
  "volatility": {
    "bollinger": {"upper": 148.50, "middle": 140.80, "lower": 133.10, "bandwidth": 10.94, "percent_b": 0.61},
    "atr": 4.25,
    "keltner": {"upper": 149.30, "middle": 140.80, "lower": 132.30}
  },
  "volume": {
    "obv": 123456789,
    "vwap": 141.15
  },
  "price_vs_indicators": {
    "vs_ema_50": 2.59,
    "vs_ema_200": 13.60,
    "vs_bb_upper": -4.04,
    "vs_bb_lower": 7.06
  }
}
```

### Token Math

This plugin provides reliable token amount calculations for swaps, limit orders, and transfers. **LLMs are notoriously bad at math** - they drop zeros, mess up decimal conversions, and hallucinate calculations. This tool does the math reliably so your agent doesn't lose the user money.

No config is needed - it's pure math with no external dependencies.

```python
config = {
    "agents": [
        {
            "name": "trading_agent",
            "instructions": """
                ALWAYS use the token_math tool BEFORE calling privy_ultra, privy_transfer, or privy_trigger!
                
                For swaps (privy_ultra):
                1. Get token price and decimals from Birdeye
                2. Call token_math action="swap" with usd_amount, token_price_usd, decimals
                3. Use the returned smallest_units as the amount for privy_ultra
                
                For transfers (privy_transfer):
                1. Get token price from Birdeye
                2. Call token_math action="transfer" with usd_amount, token_price_usd
                3. Use the returned amount for privy_transfer
                
                For limit orders (privy_trigger):
                1. Get prices and decimals for BOTH tokens from Birdeye
                2. Call token_math action="limit_order" with all params
                3. Use the returned making_amount and taking_amount for privy_trigger
                
                NEVER calculate amounts yourself - use token_math!
            """,
            "specialization": "Solana trading",
            "tools": ["token_math", "birdeye", "privy_ultra", "privy_transfer", "privy_trigger"],
        }
    ]
}
```

**Actions:**

- `swap` - Calculate smallest units for a swap given USD amount
  - Params: `usd_amount`, `token_price_usd`, `decimals`
  - Returns: `smallest_units` (use this for privy_ultra amount)

- `transfer` - Calculate human-readable token amount for transfers
  - Params: `usd_amount`, `token_price_usd`
  - Returns: `amount` (human-readable, use this for privy_transfer amount)

- `limit_order` - Calculate making_amount and taking_amount for limit orders
  - Params: `usd_amount`, `input_price_usd`, `input_decimals`, `output_price_usd`, `output_decimals`, `price_change_percentage`
  - Returns: `making_amount`, `taking_amount` (use these for privy_trigger)
  - `price_change_percentage`: How much MORE output you want than current market. ALWAYS POSITIVE for limit orders:
    - "0.5" = get 0.5% more output (buy the dip - wait for output token to drop)
    - "5" = get 5% more output (sell high - wait for input token to rise)
    - "0" = current market price (fills immediately)

- `limit_order_info` - Calculate trigger price and USD values for displaying order info
  - Params: `making_amount`, `taking_amount`, `input_price_usd`, `output_price_usd`, `input_decimals`, `output_decimals`
  - `making_amount` and `taking_amount` should be raw amounts from order's `rawMakingAmount` and `rawTakingAmount` fields
  - `input_decimals` and `output_decimals` are REQUIRED (e.g., SOL=9, USDC=6, BONK=5)
  - Returns: `making_usd`, `taking_usd_at_current`, `trigger_price_usd`, `current_output_price_usd`, `price_difference_percent`, `should_fill_now`
  - Use this when listing orders to show meaningful price info to users

- `to_smallest_units` - Convert human amount to smallest units
  - Params: `human_amount`, `decimals`
  - Returns: `smallest_units`

- `to_human` - Convert smallest units to human readable
  - Params: `smallest_units`, `decimals`
  - Returns: `human_amount`

- `usd_to_tokens` - Calculate token amount from USD value
  - Params: `usd_amount`, `token_price_usd`
  - Returns: `token_amount` (human readable)

**Example - Limit Order:**
```
User: "limit buy BONK when price drops 0.5% with $10 of SOL"

1. Birdeye: SOL price=$140, decimals=9, BONK price=$0.00001, decimals=5

2. token_math action="limit_order":
   - usd_amount="10"
   - input_price_usd="140" (SOL)
   - input_decimals=9
   - output_price_usd="0.00001" (BONK)
   - output_decimals=5
   - price_change_percentage="0.5"  # Want 0.5% MORE BONK than current market
   
   Returns:
   - making_amount="71428571" (SOL in lamports)
   - taking_amount="100500000000" (BONK - 0.5% more than current would give)

3. privy_trigger with those exact amounts - order waits until you can get 0.5% more BONK
```

## 🧩 Plugin Development
Want to add your own plugins to Solana Agent Kit? Follow these guidelines:

1. Create a new plugin directory under solana_agent_kit/
2. Implement a plugin class that follows Solana Agent's plugin architecture
3. Add your plugin to the list in __init__.py
4. Test thoroughly
5. Submit a PR!

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
