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
* Solana Swap - Swap Solana tokens on Jupiter in the agent's wallet
* Solana Balance - Get the token balances of a wallet
* Solana Price - Get the price of a token
* Solana SNS Lookup - Get the Solana address for a SNS domain
* Rugcheck - Check if a token is a rug
* Internet Search - Search the internet in real-time using Perplexity, Grok, or OpenAI
* MCP - Interface with any MCP web server - Zapier is supported
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

### Solana Swap

This plugin enables Solana Agent to swap tokens using Jupiter.

Don't use tickers - but mint addresses in your user queries.

```python
config = {
    "tools": {
        "solana_swap": {
            "rpc_url": "my-rpc-url", # Required - your RPC URL - Helius is recommended
            "private_key": "my-private-key", # Required - base58 string - please use env vars to store the key as it is very confidential
            "jupiter_url": "my-custom-url" # Optional - if you are using a custom Jupiter service like Metis from QuickNode
        },
    },
}
```

### Solana Balance

This plugin enables Solana Agent to get the token balances of a wallet.

```python
config = {
    "tools": {
        "solana_balance": {
            "api_key": "my-alphavybe-api-key", # Required - your AlphaVybe API key - the free plan allows this call
        },
    },
}
```

### Solana Price

This plugin enables Solana Agent to get the price in USD of a token.

```python
config = {
    "tools": {
        "solana_price": {
            "api_key": "my-birdeye-api-key", # Required - your Birdeye API key - the free plan allows this call
        },
    },
}
```

### Solana SNS Lookup

This plugin enables Solana Agent to get the Solana address of an SNS domain.

```python
config = {
    "tools": {
        "sns_lookup": {
            "quicknode_url": "my-quicknode-rpc-url", # Required - your QuickNode RPC URL with the SNS addon enabled
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
            "model": "gpt-4o-mini-search-preview"  # Optional, defaults to "sonar" for Perplexity or "gpt-4o-mini-search-preview" for OpenAI or "grok-3-mini-fast" for Grok
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
* grok-3
* grok-3-fast
* grok-3-mini
* grok-3-mini-fast

### MCP

[Zapier](https://zapier.com/mcp) MCP has been tested, works, and is supported.

Zapier integrates over 7,000+ apps with 30,000+ actions that your AI Agent can utilize.

Other MCP servers may work but are not supported.

OpenAI is a requirement.

```python
config = {
    "openai": {
        "api_key": "your-api-key",
    },
    "tools": {
        "mcp": {
            "url": "my-zapier-mcp-url",
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
