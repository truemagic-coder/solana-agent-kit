# Solana Agent Kit

[![PyPI - Version](https://img.shields.io/pypi/v/sakit)](https://pypi.org/project/sakit)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-orange.svg)](https://www.python.org/downloads/)

A collection of powerful plugins to extend the capabilities of Solana Agent.

## 🚀 Features
Solana Agent Kit provides a growing library of plugins that enhance your Solana Agent with new capabilities:

* Internet Search - Search the internet in real-time using Perplexity AI
* MCP - Interface with any MCP server

## 📦 Installation

```bash
pip install sakit
```

🔌 Plugins

### Internet Search Plugin
This plugin enables Solana Agent to search the internet for up-to-date information using Perplexity AI.

```python
config = {    
    "tools": {
        "search_internet": {
            "api_key": "your-perplexity-key", # Required
            "citations": True, # Optional, defaults to True
            "model": "sonar"  # Optional, defaults to "sonar"
        }
    },
    "agents": [
        {
            "name": "research_specialist",
            "instructions": "You are an expert researcher who synthesizes complex information clearly.",
            "specialization": "Research and knowledge synthesis",
            "tools": ["search_internet"],  # Enable the tool for this agent
        }
    ]
}
```

**Available Search Models**
* sonar: Fast, general-purpose search
* sonar-pro: Enhanced search capabilities

**Notes**
* The sonar reasoning models will output their reasoning in the text or audio for Solana Agent which is bad so they should not be used.

### MCP
This plugin enables Solana Agent to interact with multiple MCP servers via URLs.

```python
    config = {
        "tools": {
            "mcp": {
                "server_urls": [
                    "http://mcp-server1.com/mcp",
                    "http://mcp-server2.com/mcp",
                    "http://mcp-server3.com/mcp"
                ]
            }
        },
        "agents": [
            {
                "name": "research_specialist",
                "instructions": "You are an expert researcher who synthesizes complex information clearly.",
                "specialization": "Research and knowledge synthesis",
                "tools": ["mcp"],  # Enable the tool for this agent
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
