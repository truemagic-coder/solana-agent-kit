# Solana Agent Kit

[![PyPI - Version](https://img.shields.io/pypi/v/sakit)](https://pypi.org/project/sakit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/sakit)](https://pypi.org/project/sakit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Ruff Style](https://img.shields.io/badge/style-ruff-41B5BE)](https://github.com/astral-sh/ruff)
[![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/truemagic-coder/solana-agent-kit)](https://libraries.io/pypi/sakit)

A collection of powerful plugins to extend the capabilities of Solana Agent.

## 🚀 Features
Solana Agent Kit provides a growing library of plugins that enhance your Solana Agent with new capabilities:

* Solana Transfer - Transfer Solana tokens between the agent's wallet and the destination wallet
* Solana Ultra - Swap Solana tokens using Jupiter Ultra API with automatic slippage, priority fees, and transaction landing
* Jupiter Holdings - Get token holdings with USD values for any wallet
* Jupiter Shield - Get security warnings and risk information for tokens
* Jupiter Token Search - Search for tokens by symbol, name, or address
* Privy Transfer - Transfer tokens using Privy delegated wallets with sponsored transactions
* Privy Ultra - Swap tokens using Jupiter Ultra with Privy delegated wallets
* Privy Wallet Address - Get the wallet address of a Privy delegated wallet
* Rugcheck - Check if a token is a rug
* Internet Search - Search the internet in real-time using Perplexity, Grok, or OpenAI
* MCP - Interface with MCP web servers
* Image Generation - Generate images with OpenAI, Grok, or Gemini with uploading to S3 compatible storage
* Nemo Agent - Generate Python projects with Nemo Agent with uploading to S3 compatible storage

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
            "rpc_url": "my-rpc-url", # Required - your RPC URL - Helius is recommended
            "private_key": "my-private-key", # Required - base58 string - please use env vars to store the key as it is very confidential
            "referral_account": "my-referral-account", # Optional - your Jupiter referral account public key for collecting fees
            "referral_fee": 50, # Optional - fee in basis points (50-255 bps, e.g., 50 = 0.5%). Jupiter takes 20% of this fee.
            "payer_private_key": "payer-private-key", # Optional - base58 private key for gasless transactions (integrator pays gas)
        },
    },
}
```

**Features:**
- **Jupiter Ultra API**: Access to competitive pricing with automatic slippage protection
- **Priority Fees**: Automatically calculated to ensure transaction landing
- **Transaction Landing**: Jupiter handles retries and transaction confirmation
- **Referral Fees**: Optionally collect integrator fees (50-255 bps) via your Jupiter referral account
- **Integrator Gas Payer**: Optionally pay for gas on behalf of users for truly gasless swaps

**Setting up Referral Account:**
To collect fees, you need a Jupiter referral account. Create one at [referral.jup.ag](https://referral.jup.ag/). Jupiter takes 20% of the referral fee you set. You also need to create token accounts for the tokens you want to collect fees in.

**Gasless Transactions:**
By default, Jupiter Ultra provides gasless swaps when the user has < 0.01 SOL and trade is > $10. However, this **doesn't work with referral fees**. To enable gasless + referral fees, configure `payer_private_key` - this wallet will pay all gas fees and you recoup costs via referral fees.

### Jupiter Holdings

This plugin enables Solana Agent to get token holdings with USD values for any wallet address using Jupiter Ultra API.

```python
config = {
    "tools": {
        "jupiter_holdings": {}, # No configuration required
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
        "jupiter_shield": {}, # No configuration required
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
        "jupiter_token_search": {}, # No configuration required
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
- **Referral Fees**: Optionally collect integrator fees (50-255 bps) via your Jupiter referral account
- **Integrator Gas Payer**: Optionally pay for gas on behalf of users for truly gasless swaps

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


### Rugcheck

This plugin enables Solana Agent to check if a token is a rug. 

No config is needed.

### Internet Search
This plugin enables Solana Agent to search the internet for up-to-date information using Perplexity or OpenAI.

Please ensure you include a prompt to instruct the agent to use the tool - otherwise it may not use it.

```python
config = {    
    "tools": {
        "search_internet": {
            "api_key": "your-api-key", # Required - either a Perplexity, Grok, or OpenAI API key
            "provider": "openai", # Optional, defaults to openai - can be "openai', "perplexity", or "grok" - grok also searches X
            "citations": True, # Optional, defaults to True - only applies for Perplexity and Grok
            "model": "gpt-4o-mini-search-preview"  # Optional, defaults to "sonar" for Perplexity or "gpt-4o-mini-search-preview" for OpenAI or "grok-4-1-fast-non-reasoning" for Grok
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


### Nemo Agent

This plugin allows the agent to generate python programs using [Nemo Agent](https://nemo-agent.com) and uploads the files in a ZIP file to s3-compatible storage. It returns the public URL of the zip file.

This has been tested using [Cloudflare R2](https://developers.cloudflare.com/r2/).

```python
config = {
    "tools": {
        "nemo_agent": {
            "provider": "openai",                                        # Required: either "openai" or "gemini"
            "api_key": "your-api-key",                                   # Required: your OpenAI or Gemini API key
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
            "name": "python_dev",
            "instructions": "You are an expert Python Developer. You always use your nemo_agent tool to generate python code.",
            "specialization": "Python Developer",
            "tools": ["nemo_agent"],  # Enable the tool for this agent
        }
    ]
}
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
