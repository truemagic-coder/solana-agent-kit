"""
DFlow Swap API utility functions.

Provides a simplified interface to DFlow's Swap API for fast token swaps
on Solana with platform fee support.

DFlow offers three swap modes:
- Order API: Combined quote + transaction (best for gasless/sponsored swaps)
- Imperative: Two-step quote then swap (precise route control)
- Declarative: Intent-based swaps (deferred routing)

This module implements the Order API for optimal performance with Privy wallets.
"""

import logging
import base64
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import httpx

from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import to_bytes_versioned  # type: ignore

logger = logging.getLogger(__name__)

# DFlow Swap API base URL
DFLOW_API_URL = "https://quote-api.dflow.net"


@dataclass
class DFlowOrderResponse:
    """Response from DFlow /order endpoint."""

    success: bool
    transaction: Optional[str] = None  # Base64 encoded transaction
    in_amount: Optional[str] = None
    out_amount: Optional[str] = None
    min_out_amount: Optional[str] = None
    input_mint: Optional[str] = None
    output_mint: Optional[str] = None
    slippage_bps: Optional[int] = None
    execution_mode: Optional[str] = None  # "sync" or "async"
    price_impact_pct: Optional[str] = None
    platform_fee: Optional[Dict[str, Any]] = None
    context_slot: Optional[int] = None
    last_valid_block_height: Optional[int] = None
    compute_unit_limit: Optional[int] = None
    prioritization_fee_lamports: Optional[int] = None
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DFlowOrderStatusResponse:
    """Response from DFlow /order-status endpoint."""

    success: bool
    status: Optional[str] = (
        None  # "pending", "expired", "failed", "open", "pendingClose", "closed"
    )
    in_amount: Optional[str] = None
    out_amount: Optional[str] = None
    fills: Optional[list] = None
    reverts: Optional[list] = None
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


class DFlowSwap:
    """DFlow Swap API client for fast token swaps."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize DFlow Swap client.

        Args:
            base_url: Optional custom base URL (defaults to quote-api.dflow.net)
        """
        self.base_url = base_url or DFLOW_API_URL
        self._headers = {
            "Content-Type": "application/json",
        }

    async def get_order(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        user_public_key: str,
        slippage_bps: Optional[int] = None,
        platform_fee_bps: Optional[int] = None,
        platform_fee_mode: Optional[str] = None,
        fee_account: Optional[str] = None,
        referral_account: Optional[str] = None,
        sponsor: Optional[str] = None,
        destination_wallet: Optional[str] = None,
        wrap_and_unwrap_sol: bool = True,
        prioritization_fee_lamports: Optional[str] = None,
        dynamic_compute_unit_limit: bool = True,
        only_direct_routes: bool = False,
        max_route_length: Optional[int] = None,
    ) -> DFlowOrderResponse:
        """
        Get a swap order from DFlow (combined quote + transaction).

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input token (in smallest units/lamports)
            user_public_key: User's wallet address (required for transaction)
            slippage_bps: Max slippage in basis points (or None for "auto")
            platform_fee_bps: Platform fee in basis points (e.g., 50 = 0.5%)
            platform_fee_mode: "outputMint" (default) or "inputMint"
            fee_account: Token account to receive platform fee (must match fee mint)
            referral_account: Referral account if using Jupiter referral program
            sponsor: Sponsor wallet for gasless swaps (pays tx fees)
            destination_wallet: Wallet to receive output (defaults to user)
            wrap_and_unwrap_sol: Whether to auto wrap/unwrap SOL (default: True)
            prioritization_fee_lamports: Priority fee ("auto", "medium", "high", "veryHigh", or lamports)
            dynamic_compute_unit_limit: Whether to simulate for CU limit (default: True)
            only_direct_routes: Only use single-leg routes (default: False)
            max_route_length: Max number of route legs

        Returns:
            DFlowOrderResponse with transaction to sign
        """
        params: Dict[str, Any] = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": str(wrap_and_unwrap_sol).lower(),
            "dynamicComputeUnitLimit": str(dynamic_compute_unit_limit).lower(),
        }

        # Slippage - use "auto" if not specified
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps
        else:
            params["slippageBps"] = "auto"

        # Platform fee configuration
        if platform_fee_bps is not None and platform_fee_bps > 0:
            params["platformFeeBps"] = platform_fee_bps
            if fee_account:
                params["feeAccount"] = fee_account
            if platform_fee_mode:
                params["platformFeeMode"] = platform_fee_mode
            if referral_account:
                params["referralAccount"] = referral_account

        # Gasless/sponsored swap
        if sponsor:
            params["sponsor"] = sponsor

        # Custom destination
        if destination_wallet:
            params["destinationWallet"] = destination_wallet

        # Priority fee
        if prioritization_fee_lamports:
            params["prioritizationFeeLamports"] = prioritization_fee_lamports
        else:
            params["prioritizationFeeLamports"] = "auto"

        # Route options
        if only_direct_routes:
            params["onlyDirectRoutes"] = "true"
        if max_route_length is not None:
            params["maxRouteLength"] = max_route_length

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/order",
                    params=params,
                    headers=self._headers,
                )

                if response.status_code != 200:
                    error_text = response.text
                    try:
                        error_data = response.json()
                        error_text = error_data.get("error", error_text)
                    except Exception:
                        pass
                    return DFlowOrderResponse(
                        success=False,
                        error=f"DFlow API error: {response.status_code} - {error_text}",
                    )

                data = response.json()

                return DFlowOrderResponse(
                    success=True,
                    transaction=data.get("transaction"),
                    in_amount=data.get("inAmount"),
                    out_amount=data.get("outAmount"),
                    min_out_amount=data.get("minOutAmount")
                    or data.get("otherAmountThreshold"),
                    input_mint=data.get("inputMint"),
                    output_mint=data.get("outputMint"),
                    slippage_bps=data.get("slippageBps"),
                    execution_mode=data.get("executionMode"),
                    price_impact_pct=data.get("priceImpactPct"),
                    platform_fee=data.get("platformFee"),
                    context_slot=data.get("contextSlot"),
                    last_valid_block_height=data.get("lastValidBlockHeight"),
                    compute_unit_limit=data.get("computeUnitLimit"),
                    prioritization_fee_lamports=data.get("prioritizationFeeLamports"),
                    raw_response=data,
                )
        except httpx.TimeoutException:
            return DFlowOrderResponse(
                success=False,
                error="Request timed out. Please try again.",
            )
        except Exception as e:
            logger.exception("Failed to get DFlow order")
            return DFlowOrderResponse(success=False, error=str(e))

    async def get_order_status(
        self,
        signature: str,
        last_valid_block_height: Optional[int] = None,
    ) -> DFlowOrderStatusResponse:
        """
        Get the status of an order by transaction signature.

        Args:
            signature: Base58-encoded transaction signature
            last_valid_block_height: Optional block height for expiry check

        Returns:
            DFlowOrderStatusResponse with order status
        """
        params: Dict[str, Any] = {
            "signature": signature,
        }

        if last_valid_block_height is not None:
            params["lastValidBlockHeight"] = last_valid_block_height

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/order-status",
                    params=params,
                    headers=self._headers,
                )

                if response.status_code == 404:  # pragma: no cover
                    return DFlowOrderStatusResponse(
                        success=False,
                        error="Order not found",
                    )

                if response.status_code != 200:  # pragma: no cover
                    error_text = response.text
                    try:
                        error_data = response.json()
                        error_text = error_data.get("error", error_text)
                    except Exception:
                        pass
                    return DFlowOrderStatusResponse(
                        success=False,
                        error=f"DFlow API error: {response.status_code} - {error_text}",
                    )

                data = response.json()

                return DFlowOrderStatusResponse(
                    success=True,
                    status=data.get("status"),
                    in_amount=data.get("inAmount"),
                    out_amount=data.get("outAmount"),
                    fills=data.get("fills"),
                    reverts=data.get("reverts"),
                    raw_response=data,
                )
        except Exception as e:
            logger.exception("Failed to get DFlow order status")
            return DFlowOrderStatusResponse(success=False, error=str(e))


def sign_dflow_transaction(  # pragma: no cover
    transaction_base64: str,
    sign_message_func,
    sponsor_sign_func=None,
) -> str:
    """
    Sign a DFlow transaction.

    Args:
        transaction_base64: Base64 encoded transaction from DFlow
        sign_message_func: Function that signs a message and returns signature (user)
        sponsor_sign_func: Optional function for sponsor signature (for gasless)

    Returns:
        Base64 encoded signed transaction
    """
    transaction_bytes = base64.b64decode(transaction_base64)
    transaction = VersionedTransaction.from_bytes(transaction_bytes)

    message_bytes = to_bytes_versioned(transaction.message)

    if sponsor_sign_func:
        # Gasless: sponsor signs first, then user
        sponsor_signature = sponsor_sign_func(message_bytes)
        user_signature = sign_message_func(message_bytes)
        signed_transaction = VersionedTransaction.populate(
            transaction.message, [sponsor_signature, user_signature]
        )
    else:
        # Normal: only user signs
        signature = sign_message_func(message_bytes)
        signed_transaction = VersionedTransaction.populate(
            transaction.message, [signature]
        )

    return base64.b64encode(bytes(signed_transaction)).decode("utf-8")
