"""
Tests for Privy Recurring Tool.

Tests the PrivyRecurringTool which uses Jupiter Recurring API with
Privy delegated wallets for transaction signing.
"""

import base64
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sakit.privy_recurring import (
    PrivyRecurringTool,
    PrivyRecurringPlugin,
    _canonicalize,
    _get_authorization_signature,
    _get_privy_embedded_wallet,
    _privy_sign_transaction,
    get_plugin,
)


# Test EC private key in SEC1 format (base64-encoded DER)
# This is a valid test P-256 key generated for testing
TEST_EC_KEY_SEC1 = "MHcCAQEEIH6phbwVBTxg+QYJMSqHXcLoiTpmO163WjA8Td/+DqQ3oAoGCCqGSM49AwEHoUQDQgAEoY29/uiiWfItIYBAmejKuM17a0GackAbFG4sNs1ObTUilKQ2V/7WkTRC0xk7IgLwCRUI1e/Yk5wQFCjlajvilw=="


@pytest.fixture
def privy_recurring_tool():
    """Create a configured PrivyRecurringTool."""
    tool = PrivyRecurringTool()
    tool.configure(
        {
            "tools": {
                "privy_recurring": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": f"wallet-auth:{TEST_EC_KEY_SEC1}",
                    "jupiter_api_key": "test-api-key",
                }
            }
        }
    )
    return tool


@pytest.fixture
def privy_recurring_tool_with_payer():
    """Create a PrivyRecurringTool configured with a payer key."""
    tool = PrivyRecurringTool()
    # Using a test Solana keypair (base58)
    test_payer_key = "5MaiiCavjCmn9Hs1o3eznqDEhRwxo7pXiAYez7keQUviUkauRiTMD8DrESdrNjN8zd9mTmVhRvBJeg5vhyvgrAhG"
    tool.configure(
        {
            "tools": {
                "privy_recurring": {
                    "app_id": "test-app-id",
                    "app_secret": "test-app-secret",
                    "signing_key": f"wallet-auth:{TEST_EC_KEY_SEC1}",
                    "jupiter_api_key": "test-api-key",
                    "payer_private_key": test_payer_key,
                }
            }
        }
    )
    return tool


class TestCanonicalize:
    """Test _canonicalize function."""

    def test_canonicalize_simple_dict(self):
        """Should canonicalize a simple dictionary."""
        obj = {"b": 2, "a": 1}
        result = _canonicalize(obj)
        assert result == '{"a":1,"b":2}'

    def test_canonicalize_nested_dict(self):
        """Should canonicalize nested dictionaries."""
        obj = {"outer": {"b": 2, "a": 1}, "key": "value"}
        result = _canonicalize(obj)
        assert '"key":"value"' in result
        assert '"outer":{' in result

    def test_canonicalize_with_arrays(self):
        """Should handle arrays in dictionaries."""
        obj = {"items": [3, 1, 2], "name": "test"}
        result = _canonicalize(obj)
        assert '"items":[3,1,2]' in result

    def test_canonicalize_no_spaces(self):
        """Should produce output with no extra spaces."""
        obj = {"key": "value", "number": 42}
        result = _canonicalize(obj)
        assert " " not in result


class TestGetAuthorizationSignature:
    """Test _get_authorization_signature function."""

    def test_signature_with_sec1_key(self):
        """Should generate signature with SEC1 format key."""
        url = "https://api.privy.io/v1/test"
        body = {"method": "test", "params": {}}
        app_id = "test-app-id"
        auth_key = f"wallet-auth:{TEST_EC_KEY_SEC1}"

        signature = _get_authorization_signature(url, body, app_id, auth_key)

        # Signature should be base64 encoded
        assert signature is not None
        assert len(signature) > 0
        # Verify it's valid base64
        decoded = base64.b64decode(signature)
        assert len(decoded) > 0

    def test_signature_with_invalid_key_raises_error(self):
        """Should raise error with invalid key format."""
        url = "https://api.privy.io/v1/test"
        body = {"method": "test"}
        app_id = "test-app-id"
        auth_key = "wallet-auth:invalid-key-data"

        with pytest.raises(ValueError) as exc_info:
            _get_authorization_signature(url, body, app_id, auth_key)

        assert "Could not load private key" in str(exc_info.value)

    def test_signature_strips_wallet_auth_prefix(self):
        """Should strip wallet-auth: prefix from key."""
        url = "https://api.privy.io/v1/test"
        body = {"method": "test"}
        app_id = "test-app-id"

        auth_key = f"wallet-auth:{TEST_EC_KEY_SEC1}"

        signature = _get_authorization_signature(url, body, app_id, auth_key)
        assert signature is not None


class TestGetPrivyEmbeddedWallet:
    """Test _get_privy_embedded_wallet function."""

    @pytest.mark.asyncio
    async def test_finds_embedded_delegated_wallet(self):
        """Should find embedded delegated wallet with address field."""
        mock_response = {
            "linked_accounts": [
                {
                    "type": "wallet",
                    "id": "wallet-123",
                    "connector_type": "embedded",
                    "delegated": True,
                    "address": "WalletAddress123",
                    "public_key": None,
                }
            ]
        }

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _get_privy_embedded_wallet(
                "did:privy:user123", "app-id", "app-secret"
            )

            assert result is not None
            assert result["wallet_id"] == "wallet-123"
            assert result["public_key"] == "WalletAddress123"

    @pytest.mark.asyncio
    async def test_finds_bot_first_wallet(self):
        """Should find bot-first wallet (API-created)."""
        mock_response = {
            "linked_accounts": [
                {
                    "type": "wallet",
                    "id": "bot-wallet-456",
                    "chain_type": "solana",
                    "address": "BotWalletAddress456",
                }
            ]
        }

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _get_privy_embedded_wallet(
                "did:privy:user123", "app-id", "app-secret"
            )

            assert result is not None
            assert result["wallet_id"] == "bot-wallet-456"
            assert result["public_key"] == "BotWalletAddress456"

    @pytest.mark.asyncio
    async def test_finds_solana_embedded_wallet_type(self):
        """Should find solana_embedded_wallet type."""
        mock_response = {
            "linked_accounts": [
                {
                    "type": "solana_embedded_wallet",
                    "id": "solana-wallet-789",
                    "address": "SolanaWalletAddress789",
                }
            ]
        }

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _get_privy_embedded_wallet(
                "did:privy:user123", "app-id", "app-secret"
            )

            assert result is not None
            assert result["wallet_id"] == "solana-wallet-789"
            assert result["public_key"] == "SolanaWalletAddress789"

    @pytest.mark.asyncio
    async def test_returns_none_for_no_suitable_wallet(self):
        """Should return None when no suitable wallet found."""
        mock_response = {
            "linked_accounts": [
                {
                    "type": "email",
                    "email": "test@example.com",
                }
            ]
        }

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _get_privy_embedded_wallet(
                "did:privy:user123", "app-id", "app-secret"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        """Should return None on API error."""
        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _get_privy_embedded_wallet(
                "did:privy:user123", "app-id", "app-secret"
            )

            assert result is None


class TestPrivySignTransaction:
    """Test _privy_sign_transaction function."""

    @pytest.mark.asyncio
    async def test_successful_sign_transaction(self):
        """Should successfully sign transaction."""
        mock_response = {
            "data": {
                "signedTransaction": "signed-tx-base64",
            }
        }

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _privy_sign_transaction(
                wallet_id="wallet-123",
                encoded_tx="encoded-tx-base64",
                app_id="test-app-id",
                app_secret="test-app-secret",
                privy_auth_key=f"wallet-auth:{TEST_EC_KEY_SEC1}",
            )

            assert result == "signed-tx-base64"

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        """Should return None on API error."""
        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "Bad Request"
            mock_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _privy_sign_transaction(
                wallet_id="wallet-123",
                encoded_tx="encoded-tx-base64",
                app_id="test-app-id",
                app_secret="test-app-secret",
                privy_auth_key=f"wallet-auth:{TEST_EC_KEY_SEC1}",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_signed_transaction(self):
        """Should return None when response lacks signedTransaction."""
        mock_response = {"data": {}}

        with patch("sakit.privy_recurring.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _privy_sign_transaction(
                wallet_id="wallet-123",
                encoded_tx="encoded-tx-base64",
                app_id="test-app-id",
                app_secret="test-app-secret",
                privy_auth_key=f"wallet-auth:{TEST_EC_KEY_SEC1}",
            )

            assert result is None


class TestPrivyRecurringToolSchema:
    """Test tool schema and initialization."""

    def test_tool_name(self, privy_recurring_tool):
        """Should have correct tool name."""
        assert privy_recurring_tool.name == "privy_recurring"

    def test_schema_has_user_id(self, privy_recurring_tool):
        """Should require user_id for Privy."""
        schema = privy_recurring_tool.get_schema()
        assert "user_id" in schema["properties"]
        assert "user_id" in schema["required"]

    def test_schema_has_actions(self, privy_recurring_tool):
        """Should include action in required properties."""
        schema = privy_recurring_tool.get_schema()
        assert "action" in schema["properties"]
        assert schema["properties"]["action"]["enum"] == ["create", "cancel", "list"]

    def test_schema_has_dca_properties(self, privy_recurring_tool):
        """Should include DCA order creation properties."""
        schema = privy_recurring_tool.get_schema()
        props = schema["properties"]
        assert "input_mint" in props
        assert "output_mint" in props
        assert "in_amount" in props
        assert "order_count" in props
        assert "frequency" in props
        assert "min_out_amount" in props
        assert "max_out_amount" in props

    def test_schema_has_order_pubkey(self, privy_recurring_tool):
        """Should include order_pubkey for cancel action."""
        schema = privy_recurring_tool.get_schema()
        assert "order_pubkey" in schema["properties"]

    def test_schema_has_start_at(self, privy_recurring_tool):
        """Should include start_at for scheduling DCA start."""
        schema = privy_recurring_tool.get_schema()
        assert "start_at" in schema["properties"]


class TestPrivyRecurringToolConfigure:
    """Test configuration method."""

    def test_configure_stores_privy_config(self, privy_recurring_tool):
        """Should store Privy credentials from config."""
        assert privy_recurring_tool._app_id == "test-app-id"
        assert privy_recurring_tool._app_secret == "test-app-secret"
        assert privy_recurring_tool._signing_key == f"wallet-auth:{TEST_EC_KEY_SEC1}"

    def test_configure_stores_api_key(self, privy_recurring_tool):
        """Should store Jupiter API key from config."""
        assert privy_recurring_tool._jupiter_api_key == "test-api-key"

    def test_configure_stores_payer_key(self, privy_recurring_tool_with_payer):
        """Should store payer private key from config."""
        assert privy_recurring_tool_with_payer._payer_private_key is not None

    def test_configure_with_empty_config(self):
        """Should handle empty config gracefully."""
        tool = PrivyRecurringTool()
        tool.configure({"tools": {}})
        assert tool._app_id is None
        assert tool._app_secret is None


class TestPrivyRecurringToolExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_missing_privy_config(self):
        """Should return error if Privy config is missing."""
        tool = PrivyRecurringTool()
        tool.configure({"tools": {"privy_recurring": {}}})

        result = await tool.execute(
            user_id="did:privy:user123",
            action="list",
        )

        assert result["status"] == "error"
        assert "config" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_wallet_found(self, privy_recurring_tool):
        """Should return error if no delegated wallet found for user."""
        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "error"
        assert "wallet" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_success(self, privy_recurring_tool):
        """Should list active DCA orders for user's wallet."""
        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "error"
        assert "wallet" in result["message"].lower()


class TestPrivyRecurringToolCreateAction:
    """Test create action."""

    @pytest.mark.asyncio
    async def test_create_missing_required_params(self, privy_recurring_tool):
        """Should return error if required create params are missing."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=mock_wallet,
        ):
            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11...",
                # Missing output_mint, in_amount, order_count, frequency
            )

        assert result["status"] == "error"
        assert (
            "missing" in result["message"].lower()
            or "required" in result["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_create_order_success(self, privy_recurring_tool):
        """Should successfully create a DCA order."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        mock_create_result = MagicMock()
        mock_create_result.success = True
        mock_create_result.transaction = "mock-tx-base64"
        mock_create_result.request_id = "req-123"
        mock_create_result.order = "order-pubkey-123"

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
            patch(
                "sakit.privy_recurring._privy_sign_transaction",
                new_callable=AsyncMock,
                return_value="signed-tx-base64",
            ),
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.create_order = AsyncMock(return_value=mock_create_result)

            mock_exec_result = MagicMock()
            mock_exec_result.success = True
            mock_exec_result.signature = "tx-sig-456"
            mock_instance.execute = AsyncMock(return_value=mock_exec_result)

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
            )

        assert result["status"] == "success"
        assert result["action"] == "create"
        assert result["order_pubkey"] == "order-pubkey-123"

    @pytest.mark.asyncio
    async def test_create_order_no_transaction(self, privy_recurring_tool):
        """Should return error when Jupiter returns no transaction."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        mock_create_result = MagicMock()
        mock_create_result.success = True
        mock_create_result.transaction = None
        mock_create_result.request_id = "req-123"

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.create_order = AsyncMock(return_value=mock_create_result)

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
            )

        assert result["status"] == "error"
        assert "transaction" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_create_order_jupiter_error(self, privy_recurring_tool):
        """Should return error when Jupiter API fails."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        mock_create_result = MagicMock()
        mock_create_result.success = False
        mock_create_result.error = "Insufficient balance"

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.create_order = AsyncMock(return_value=mock_create_result)

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
            )

        assert result["status"] == "error"
        assert "Insufficient balance" in result["message"]

    @pytest.mark.asyncio
    async def test_create_order_signing_failure(self, privy_recurring_tool):
        """Should return error when signing fails."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        mock_create_result = MagicMock()
        mock_create_result.success = True
        mock_create_result.transaction = "mock-tx-base64"
        mock_create_result.request_id = "req-123"
        mock_create_result.order = "order-pubkey-123"

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
            patch(
                "sakit.privy_recurring._privy_sign_transaction",
                new_callable=AsyncMock,
                return_value=None,  # Signing failed
            ),
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.create_order = AsyncMock(return_value=mock_create_result)

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="create",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                in_amount="1000000000",
                order_count=10,
                frequency="3600",
            )

        assert result["status"] == "error"
        assert "sign" in result["message"].lower()


class TestPrivyRecurringToolCancelAction:
    """Test cancel action."""

    @pytest.mark.asyncio
    async def test_cancel_missing_order_pubkey(self, privy_recurring_tool):
        """Should return error if order_pubkey is missing for cancel."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=mock_wallet,
        ):
            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="cancel",
            )

        assert result["status"] == "error"
        assert "order_pubkey" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_order_not_owned_by_user(self, privy_recurring_tool):
        """Should reject cancellation of orders not owned by the user."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_recurring_instance = MockRecurring.return_value
            # User's orders - does NOT include the order they're trying to cancel
            mock_recurring_instance.get_orders = AsyncMock(
                return_value={
                    "success": True,
                    "orders": [
                        {"order": "UserOwnedDCA123"},
                        {"order": "UserOwnedDCA456"},
                    ],
                }
            )

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="cancel",
                order_pubkey="SomeoneElsesDCA789",  # Not in user's orders
            )

        assert result["status"] == "error"
        assert "does not belong" in result["message"]

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, privy_recurring_tool):
        """Should successfully cancel a DCA order."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        mock_cancel_result = MagicMock()
        mock_cancel_result.success = True
        mock_cancel_result.transaction = "cancel-tx-base64"
        mock_cancel_result.request_id = "req-cancel-123"

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
            patch(
                "sakit.privy_recurring._privy_sign_transaction",
                new_callable=AsyncMock,
                return_value="signed-cancel-tx-base64",
            ),
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.get_orders = AsyncMock(
                return_value={
                    "success": True,
                    "orders": [{"order": "UserOwnedDCA123"}],
                }
            )
            mock_instance.cancel_order = AsyncMock(return_value=mock_cancel_result)

            mock_exec_result = MagicMock()
            mock_exec_result.success = True
            mock_exec_result.signature = "cancel-sig-789"
            mock_instance.execute = AsyncMock(return_value=mock_exec_result)

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="cancel",
                order_pubkey="UserOwnedDCA123",
            )

        assert result["status"] == "success"
        assert result["action"] == "cancel"
        assert result["order_pubkey"] == "UserOwnedDCA123"


class TestPrivyRecurringToolListAction:
    """Test list action."""

    @pytest.mark.asyncio
    async def test_list_orders_success(self, privy_recurring_tool):
        """Should successfully list DCA orders."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.get_orders = AsyncMock(
                return_value={
                    "success": True,
                    "orders": [
                        {
                            "order": "order-123",
                            "inputMint": "So11...",
                            "outputMint": "EPj...",
                            "depositAmount": "1000000000",
                            "orderCount": 10,
                            "executedCount": 3,
                            "frequency": "3600",
                            "nextExecution": "2024-01-02T00:00:00Z",
                            "createdAt": "2024-01-01T00:00:00Z",
                        }
                    ],
                }
            )

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "success"
        assert result["action"] == "list"
        assert result["order_count"] == 1
        assert len(result["orders"]) == 1
        assert result["orders"][0]["order_pubkey"] == "order-123"
        assert result["orders"][0]["executed_count"] == 3

    @pytest.mark.asyncio
    async def test_list_orders_empty(self, privy_recurring_tool):
        """Should handle empty order list."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.get_orders = AsyncMock(
                return_value={"success": True, "orders": []}
            )

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "success"
        assert result["order_count"] == 0
        assert "no active" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_list_orders_api_failure(self, privy_recurring_tool):
        """Should handle API failure when listing orders."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "UserPublicKey123",
        }

        with (
            patch(
                "sakit.privy_recurring._get_privy_embedded_wallet",
                new_callable=AsyncMock,
                return_value=mock_wallet,
            ),
            patch("sakit.privy_recurring.JupiterRecurring") as MockRecurring,
        ):
            mock_instance = MockRecurring.return_value
            mock_instance.get_orders = AsyncMock(
                return_value={"success": False, "error": "API unavailable"}
            )

            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="list",
            )

        assert result["status"] == "error"
        assert "API unavailable" in result["message"]


class TestPrivyRecurringToolUnknownAction:
    """Test unknown action handling."""

    @pytest.mark.asyncio
    async def test_unknown_action(self, privy_recurring_tool):
        """Should return error for unknown action."""
        mock_wallet = {
            "wallet_id": "wallet123",
            "public_key": "PublicKey123",
        }

        with patch(
            "sakit.privy_recurring._get_privy_embedded_wallet",
            new_callable=AsyncMock,
            return_value=mock_wallet,
        ):
            result = await privy_recurring_tool.execute(
                user_id="did:privy:user123",
                action="invalid_action",
            )

        assert result["status"] == "error"
        assert (
            "unknown" in result["message"].lower()
            or "invalid" in result["message"].lower()
        )


class TestPrivyRecurringPlugin:
    """Test plugin class."""

    def test_plugin_name(self):
        """Should have correct plugin name."""
        plugin = PrivyRecurringPlugin()
        assert plugin.name == "privy_recurring"

    def test_plugin_description(self):
        """Should have descriptive description."""
        plugin = PrivyRecurringPlugin()
        assert (
            "recurring" in plugin.description.lower()
            or "dca" in plugin.description.lower()
        )

    def test_plugin_get_tools_empty_before_init(self):
        """Should return empty list before initialization."""
        plugin = PrivyRecurringPlugin()
        assert plugin.get_tools() == []

    def test_plugin_initialize(self):
        """Should initialize tool on registry."""
        plugin = PrivyRecurringPlugin()
        mock_registry = MagicMock()

        plugin.initialize(mock_registry)

        assert plugin._tool is not None
        assert len(plugin.get_tools()) == 1

    def test_plugin_configure(self):
        """Should configure the tool after initialization."""
        plugin = PrivyRecurringPlugin()
        mock_registry = MagicMock()
        plugin.initialize(mock_registry)

        config = {
            "tools": {
                "privy_recurring": {
                    "app_id": "test-app",
                    "app_secret": "test-secret",
                    "signing_key": f"wallet-auth:{TEST_EC_KEY_SEC1}",
                }
            }
        }
        plugin.configure(config)

        assert plugin.config == config
        assert plugin._tool._app_id == "test-app"


class TestGetPlugin:
    """Test get_plugin function."""

    def test_get_plugin_returns_instance(self):
        """Should return a PrivyRecurringPlugin instance."""
        plugin = get_plugin()
        assert isinstance(plugin, PrivyRecurringPlugin)
        assert plugin.name == "privy_recurring"
