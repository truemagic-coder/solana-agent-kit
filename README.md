# Solana Agent Kit

[![PyPI - Version](https://img.shields.io/pypi/v/sakit)](https://pypi.org/project/sakit)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-orange.svg)](https://www.python.org/downloads/)

A collection of powerful plugins to extend the capabilities of Solana Agent.

## 🚀 Features
Solana Agent Kit provides a growing library of plugins that enhance your Solana Agent with new capabilities:

🔍 Internet Search - Search the internet in real-time using Perplexity AI

📝 More plugins coming soon!

## 📦 Installation

```bash
# Using pip
pip install sakit

# Using Poetry
poetry add sakit
```

🔌 Plugins
Internet Search Plugin
This plugin enables Solana Agent to search the internet for up-to-date information using Perplexity AI.

Configuration
Add your Perplexity API key to your Solana Agent configuration:

```python
config = {
    # Standard Solana Agent config
    "openai": {
        "api_key": "your-openai-key",
        "default_model": "gpt-4o-mini"
    },
    
    # Required for the internet search plugin
    "perplexity_api_key": "your-perplexity-key",
    
    # Optional: Configure default search model
    "tools": {
        "search_internet": {
            "default_model": "sonar-reasoning-pro"  # Optional, defaults to "sonar"
        }
    },
    
    # Grant access to specific agents
    "agents": [
        {
            "name": "research_specialist",
            "tools": ["search_internet"],  # Enable the tool for this agent
            "instructions": "You are an expert researcher who synthesizes complex information clearly.",
            "specialization": "Research and knowledge synthesis",
            "model": "gpt-4o-mini"
        }
    ]
}
```

**Available Search Models**
* sonar: Fast, general-purpose search
* sonar-pro: Enhanced search capabilities
* sonar-reasoning-pro: Advanced reasoning with search
* sonar-reasoning: Basic reasoning with search

## 🧩 Plugin Development
Want to add your own plugins to Solana Agent Kit? Follow these guidelines:

1. Create a new plugin directory under solana_agent_kit/
2. Implement a plugin class that follows Solana Agent's plugin architecture
3. Add your plugin to the list in __init__.py
4. Test thoroughly
5. Submit a PR!

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
