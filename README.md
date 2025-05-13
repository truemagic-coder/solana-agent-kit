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

* Solana - Interact with the Solana blockchain ecosystem using AgentiPy
* Internet Search - Search the internet in real-time using Perplexity or OpenAI
* MCP - Interface with any MCP server via its SSE URL - Zapier is supported
* Image Generation - Generate images with OpenAI, Grok, or Gemini with uploading to S3 compatible storage
* Nemo Agent - Generate Python projects with Nemo Agent with uploading to S3 compatible storage

## 📦 Installation

```bash
pip install sakit
```

## 🔌 Plugins

### Solana
This plugin integrates the [agentipy](https://github.com/niceberginc/agentipy) package, providing your Solana Agent with direct access to Solana ecosystem.

```python
config = {
    "tools": {
        "solana": {
            # Core Solana Settings
            "private_key": "YOUR_SOLANA_WALLET_PRIVATE_KEY",       # Required (unless generate_wallet=True): Your wallet's private key (base58 encoded string).
            "rpc_url": "https://api.mainnet-beta.solana.com",      # Optional: Defaults to Solana mainnet RPC.
            "generate_wallet": False,                              # Optional: If True, ignores private_key and generates a new wallet. Defaults to False.

            # Optional RPC/Service API Keys & URLs
            "helius_api_key": "YOUR_HELIUS_API_KEY",               # Optional: Helius API key for enhanced data/RPC.
            "helius_rpc_url": "YOUR_HELIUS_RPC_URL",               # Optional: Specific Helius RPC URL.
            "quicknode_rpc_url": "YOUR_QUICKNODE_RPC_URL",         # Optional: QuickNode RPC URL.
            "jito_block_engine_url": "YOUR_JITO_BLOCK_ENGINE_URL", # Optional: Jito block engine URL for bundles.
            "jito_uuid": "YOUR_JITO_UUID",                         # Optional: Jito authentication UUID.

            # Optional Integration API Keys
            "openai_api_key": "YOUR_OPENAI_API_KEY",               # Optional: OpenAI API key (if needed by specific agentipy features).
            "backpack_api_key": "YOUR_BACKPACK_API_KEY",           # Optional: Backpack Exchange API key.
            "backpack_api_secret": "YOUR_BACKPACK_API_SECRET",     # Optional: Backpack Exchange API secret.
            "stork_api_key": "YOUR_STORK_API_KEY",                 # Optional: Stork oracle API key.
            "coingecko_api_key": "YOUR_COINGECKO_PRO_API_KEY",     # Optional: CoinGecko Pro API key.
            "coingecko_demo_api_key": "YOUR_COINGECKO_DEMO_KEY",   # Optional: CoinGecko Demo API key.
            "elfa_ai_api_key": "YOUR_ELFA_AI_API_KEY",             # Optional: Elfa AI API key.
            "flexland_api_key": "YOUR_FLEXLAND_API_KEY",           # Optional: Flexlend API key.
            "allora_api_key": "YOUR_ALLORA_API_KEY",               # Optional: Allora Network API key.
            "solutiofi_api_key": "YOUR_SOLUTIOFI_API_KEY"          # Optional: Solutio Finance API key.
        },
    },
    "agents": [
        {
            "name": "solana_expert",
            "instructions": """
                You are an expert Solana blockchain assistant. 
                You always use the Solana tool to perform actions on the Solana blockchain.
            """,
            "specialization": "Solana blockchain interaction",
            "tools": ["solana"],  # Enable the tool for this agent
        }
    ]
}
```

### Internet Search
This plugin enables Solana Agent to search the internet for up-to-date information using Perplexity or OpenAI.

Please ensure you include a prompt to instruct the agent to use the tool - otherwise it may not use it.

```python
config = {    
    "tools": {
        "search_internet": {
            "api_key": "your-api-key", # Required - either a Perplexity or OpenAI API key
            "provider": "perplexity", # Optional, defaults to perplexity - can also be openai (lowercase)
            "citations": True, # Optional, defaults to True - only applies for Perplexity
            "model": "sonar"  # Optional, defaults to "sonar" for Perplexity and "gpt-4o-mini-search-preview" for OpenAI
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

**Notes**
* The sonar reasoning models will output their reasoning in the text or audio for Solana Agent which is bad so they should not be used.


### MCP

[Zapier](https://zapier.com/mcp) MCP has been tested, works, and is supported.

Zapier integrates over 7,000+ apps with 30,000+ actions that your Solana Agent can utilize.

Other MCP servers may work but are not supported.

```python
config = {
    "tools": {
        "mcp": {
            "urls": ["my-zapier-mcp-url"],
        }
    },
    "agents": [
        {
            "name": "zapier_expert",
            "instructions": "You are an expert in using Zapier integrations using MCP. You always use the mcp tool to perform Zapier AI like actions.",
            "specialization": "Zapier service integration expert",
            "tools": ["mcp"],  # Enable the tool for this agent
        }
    ]
}
```

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
