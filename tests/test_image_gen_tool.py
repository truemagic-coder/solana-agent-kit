"""
Tests for Image Generation Tool.

Tests the ImageGenTool which generates images using OpenAI/Grok/Gemini
and uploads them to S3-compatible storage.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestImageGenToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self):
        """Should have correct tool name."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            assert tool.name == "image_gen"

    def test_schema_has_required_properties(self):
        """Should include prompt in required properties."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            schema = tool.get_schema()
            assert "prompt" in schema["properties"]
            assert "prompt" in schema["required"]

    def test_schema_prompt_description(self):
        """Should have descriptive prompt field."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            schema = tool.get_schema()
            assert "description" in schema["properties"]["prompt"]


class TestImageGenToolConfigure:
    """Test configuration method."""

    def test_configure_stores_api_key(self):
        """Should store API key from config."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-openai-key",
                            "s3_endpoint_url": "https://s3.example.com",
                            "s3_access_key_id": "access-key",
                            "s3_secret_access_key": "secret-key",
                            "s3_bucket_name": "test-bucket",
                        }
                    }
                }
            )
            assert tool._openai_api_key == "test-openai-key"

    def test_configure_stores_s3_config(self):
        """Should store S3 configuration."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-key",
                            "s3_endpoint_url": "https://s3.example.com",
                            "s3_access_key_id": "access-key",
                            "s3_secret_access_key": "secret-key",
                            "s3_bucket_name": "test-bucket",
                            "s3_region_name": "us-east-1",
                        }
                    }
                }
            )
            assert tool._s3_endpoint_url == "https://s3.example.com"
            assert tool._s3_bucket_name == "test-bucket"
            assert tool._s3_region_name == "us-east-1"

    def test_configure_grok_provider(self):
        """Should configure Grok provider correctly."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-key",
                            "provider": "grok",
                            "s3_endpoint_url": "https://s3.example.com",
                            "s3_access_key_id": "access-key",
                            "s3_secret_access_key": "secret-key",
                            "s3_bucket_name": "test-bucket",
                        }
                    }
                }
            )
            assert tool._provider == "grok"
            assert tool._openai_base_url == "https://api.x.ai/v1"

    def test_configure_gemini_provider(self):
        """Should configure Gemini provider correctly."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-key",
                            "provider": "gemini",
                            "s3_endpoint_url": "https://s3.example.com",
                            "s3_access_key_id": "access-key",
                            "s3_secret_access_key": "secret-key",
                            "s3_bucket_name": "test-bucket",
                        }
                    }
                }
            )
            assert tool._provider == "gemini"


class TestImageGenToolIsConfigured:
    """Test configuration validation."""

    def test_is_configured_returns_false_when_incomplete(self):
        """Should return False when config is incomplete."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-key",
                            # Missing S3 config
                        }
                    }
                }
            )
            assert tool._is_configured() is False

    def test_is_configured_returns_true_when_complete(self):
        """Should return True when config is complete."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure(
                {
                    "tools": {
                        "image_gen": {
                            "api_key": "test-key",
                            "s3_endpoint_url": "https://s3.example.com",
                            "s3_access_key_id": "access-key",
                            "s3_secret_access_key": "secret-key",
                            "s3_bucket_name": "test-bucket",
                        }
                    }
                }
            )
            assert tool._is_configured() is True


class TestImageGenToolExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_not_configured_error(self):
        """Should return error when not configured."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenTool

            tool = ImageGenTool()
            tool.configure({"tools": {"image_gen": {}}})

            result = await tool.execute(prompt="A beautiful sunset")

            assert result["status"] == "error"
            assert "not configured" in result["message"].lower()


class TestImageGenPlugin:
    """Test plugin class."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenPlugin

            plugin = ImageGenPlugin()
            assert plugin.name == "image_gen"

    def test_plugin_description(self):
        """Should have descriptive description."""
        with patch.dict("sys.modules", {"openai": MagicMock(), "boto3": MagicMock()}):
            from sakit.image_gen import ImageGenPlugin

            plugin = ImageGenPlugin()
            assert "image" in plugin.description.lower()
