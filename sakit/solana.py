import logging
from typing import Dict, Any, List, Optional, Union
from agentipy import SolanaAgentKit  # type: ignore # types: ignore[import]
from solana_agent import AutoTool, ToolRegistry
from solders.pubkey import Pubkey  # type: ignore # types: ignore[import]

logger = logging.getLogger(__name__)


class SolanaAgentKitTool(AutoTool):
    """
    Tool for interacting with the Solana blockchain via SolanaAgentKit (agentipy).
    Provides access to various Solana functions like transfers, trades, balance checks, etc.
    """

    def __init__(self, registry=None):
        """Initialize with auto-registration."""
        super().__init__(
            name="solana",
            description="Interact with the Solana blockchain using the Agentipy SolanaAgentKit. Allows calling methods like get_balance, transfer, trade, deploy_token, etc.",
            registry=registry,
        )
        self._kit = None

    def get_schema(self) -> Dict[str, Any]:
        """Define a static tool schema for LLM interaction with all known actions."""

        # --- Static List of Actions ---
        # Manually generated or pasted from previous inspection
        available_actions = [
            "approve_multisig_proposal",
            "burn_and_close_accounts",
            "burn_tokens",
            "buy_token",
            "buy_using_moonshot",
            "buy_with_raydium",
            "calculate_pump_curve_price",
            "cancel_all_orders",
            "cancel_listing",
            "cancel_open_order",
            "cancel_open_orders",
            "check_if_drift_account_exists",
            "check_transaction_status",
            "close_accounts",
            "close_perp_trade_long",
            "close_perp_trade_short",
            "close_position",
            "create_3land_collection",
            "create_3land_nft",
            "create_clmm",
            "create_debridge_transaction",
            "create_drift_user_account",
            "create_drift_vault",
            "create_gibwork_task",
            "create_liquidity_pool",
            "create_manifest_market",
            "create_meteora_dlmm_pool",
            "create_multisig_proposal",
            "create_openbook_market",
            "create_squads_multisig",
            "create_tiplink",
            "create_webhook",
            "cybers_create_coin",
            "delete_webhook",
            "deploy_collection",
            "deploy_token",
            "deposit_into_drift_vault",
            "deposit_strategy",
            "deposit_to_drift_user_account",
            "deposit_to_multisig_treasury",
            "derive_drift_vault_address",
            "drift_swap_spot_token",
            "drift_user_account_info",
            "edit_webhook",
            "execute_borrow_lend",
            "execute_debridge_transaction",
            "execute_multisig_proposal",
            "execute_order",
            "fetch_all_domains",
            "fetch_domain_records",
            "fetch_domains_csv",
            "fetch_leaderboard",
            "fetch_most_viewed_tokens",
            "fetch_new_tokens",
            "fetch_positions",
            "fetch_price",
            "fetch_recently_verified_tokens",
            "fetch_token_detailed_report",
            "fetch_token_flux_lp_lockers",
            "fetch_token_lp_lockers",
            "fetch_token_report_summary",
            "fetch_token_votes",
            "fetch_trending_tokens",
            "flash_close_trade",
            "flash_open_trade",
            "fluxbeam_create_pool",
            "get_account_balances",
            "get_account_deposits",
            "get_account_settings",
            "get_active_listings",
            "get_address_name",
            "get_all_domains_for_owner",
            "get_all_domains_tlds",
            "get_all_topics",
            "get_all_webhooks",
            "get_available_drift_markets",
            "get_balance",
            "get_balances",
            "get_borrow_history",
            "get_borrow_lend_positions",
            "get_borrow_position_history",
            "get_bundle_statuses",
            "get_collateral_info",
            "get_depth",
            "get_drift_entry_quote_of_perp_trade",
            "get_drift_lend_borrow_apy",
            "get_drift_perp_market_funding_rate",
            "get_drift_vault_info",
            "get_elfa_ai_api_key_status",
            "get_favourite_domain",
            "get_fill_history",
            "get_funding_interval_rates",
            "get_funding_payments",
            "get_inference_by_topic_id",
            "get_inflight_bundle_statuses",
            "get_interest_history",
            "get_klines",
            "get_latest_pools",
            "get_market",
            "get_markets",
            "get_mark_price",
            "get_metaplex_asset",
            "get_metaplex_assets_by_authority",
            "get_metaplex_assets_by_creator",
            "get_mintlists",
            "get_nft_events",
            "get_nft_fingerprint",
            "get_nft_metadata",
            "get_open_interest",
            "get_open_orders",
            "get_open_positions",
            "get_order_history",
            "get_owned_all_domains",
            "get_owned_domains_for_tld",
            "get_parsed_transaction_history",
            "get_parsed_transactions",
            "get_pnl_history",
            "get_position_values",
            "get_price_prediction",
            "get_pump_curve_state",
            "get_random_tip_account",
            "get_raw_transactions",
            "get_recent_trades",
            "get_registration_transaction",
            "get_settlement_history",
            "get_smart_mentions",
            "get_smart_twitter_account_stats",
            "get_status",
            "get_supported_assets",
            "get_system_time",
            "get_ticker_information",
            "get_tickers",
            "get_tip_accounts",
            "get_token_data_by_address",
            "get_token_data_by_ticker",
            "get_token_info",
            "get_token_price_data",
            "get_top_gainers",
            "get_top_mentions_by_ticker",
            "get_tps",
            "get_trending_pools",
            "get_trending_tokens",
            "get_trending_tokens_using_elfa_ai",
            "get_users_open_orders",
            "get_webhook",
            "launch_pump_fun_token",
            "lend_assets",
            "list_nft_for_sale",
            "list_tools",
            "lookup_domain",
            "lulo_lend",
            "lulo_withdraw",
            "merge_tokens",
            "mint_metaplex_core_nft",
            "multiple_burn_and_close_accounts",
            "open_centered_position",
            "open_perp_trade_long",
            "open_perp_trade_short",
            "open_single_sided_position",
            "parse_key_value_string",
            "ping_elfa_ai_api",
            "place_batch_orders",
            "place_limit_order",
            "pyth_fetch_price",
            "reject_multisig_proposal",
            "request_faucet_funds",
            "request_unstake_from_drift_insurance_fund",
            "request_withdrawal",
            "request_withdrawal_from_drift_vault",
            "resolve_all_domains",
            "resolve_name_to_address",
            "restake",
            "rock_paper_scissors",
            "search_mentions_by_keywords",
            "sell_token",
            "sell_using_moonshot",
            "sell_with_raydium",
            "send_bundle",
            "send_compressed_airdrop",
            "send_ping",
            "send_txn",
            "simulate_switchboard_feed",
            "spread_token",
            "stake",
            "stake_to_drift_insurance_fund",
            "stork_fetch_price",
            "trade",
            "trade_using_delegated_drift_vault",
            "trade_using_drift_perp_account",
            "transfer",
            "transfer_from_multisig_treasury",
            "unstake_from_drift_insurance_fund",
            "update_account_settings",
            "update_drift_vault",
            "update_drift_vault_delegate",
            "withdraw_all",
            "withdraw_from_drift_user_account",
            "withdraw_from_drift_vault",
            "withdraw_strategy",
        ]
        available_actions.sort()  # Keep it sorted

        # --- Static Description with Full List ---
        args_description = """
Arguments to pass to the specified action (method), provided as key-value pairs.
Arguments MUST match the parameters of the chosen action listed below.
Provide Pubkey types as Base58 encoded strings.

Available Actions and their Expected Arguments:
-----------------------------------------------
- `approve_multisig_proposal(transaction_index: int) -> Optional[Dict[str, Any]]`
- `burn_and_close_accounts(token_account: str)`
- `burn_tokens(mints: List[str]) -> Optional[Dict[str, Any]]`
- `buy_token(mint: Pubkey, bonding_curve: Pubkey, associated_bonding_curve: Pubkey, amount: float, slippage: float, max_retries: int)`
- `buy_using_moonshot(mint_str: str, collateral_amount: float = 0.01, slippage_bps: int = 500)`
- `buy_with_raydium(pair_address: str, sol_in: float = 0.01, slippage: int = 5)`
- `calculate_pump_curve_price(curve_state: BondingCurveState)`
- `cancel_all_orders(market_id: str) -> Optional[Dict[str, Any]]`
- `cancel_listing(nft_mint: str) -> Optional[Dict[str, Any]]`
- `cancel_open_order(**kwargs)`
- `cancel_open_orders(**kwargs)`
- `check_if_drift_account_exists() -> Optional[Dict[str, Any]]`
- `check_transaction_status(tx_hash: str)`
- `close_accounts(mints: List[str]) -> Optional[Dict[str, Any]]`
- `close_perp_trade_long(price: float, trade_mint: str) -> Optional[Dict[str, Any]]`
- `close_perp_trade_short(price: float, trade_mint: str) -> Optional[Dict[str, Any]]`
- `close_position(position_mint_address: str) -> Optional[Dict[str, Any]]`
- `create_3land_collection(collection_symbol: str, collection_name: str, collection_description: str, main_image_url: Optional[str] = None, cover_image_url: Optional[str] = None, is_devnet: Optional[bool] = False) -> Optional[Dict[str, Any]]`
- `create_3land_nft(item_name: str, seller_fee: float, item_amount: int, item_symbol: str, item_description: str, traits: Any, price: Optional[float] = None, main_image_url: Optional[str] = None, cover_image_url: Optional[str] = None, spl_hash: Optional[str] = None, pool_name: Optional[str] = None, is_devnet: Optional[bool] = False, with_pool: Optional[bool] = False) -> Optional[Dict[str, Any]]`
- `create_clmm(mint_deploy: str, mint_pair: str, initial_price: float, fee_tier: str) -> Optional[Dict[str, Any]]`
- `create_debridge_transaction(src_chain_id: str, src_chain_token_in: str, src_chain_token_in_amount: str, dst_chain_id: str, dst_chain_token_out: str, dst_chain_token_out_recipient: str, src_chain_order_authority_address: str, dst_chain_order_authority_address: str, affiliate_fee_percent: str = '0', affiliate_fee_recipient: str = '', prepend_operating_expenses: bool = True, dst_chain_token_out_amount: str = 'auto')`
- `create_drift_user_account(deposit_amount: float, deposit_symbol: str) -> Optional[Dict[str, Any]]`
- `create_drift_vault(name: str, market_name: str, redeem_period: int, max_tokens: int, min_deposit_amount: float, management_fee: float, profit_share: float, hurdle_rate: Optional[float] = None, permissioned: Optional[bool] = None) -> Optional[Dict[str, Any]]`
- `create_gibwork_task(title: str, content: str, requirements: str, tags: list[str], token_mint_address: Pubkey, token_amount: int)`
- `create_liquidity_pool(deposit_token_amount: float, deposit_token_mint: str, other_token_mint: str, initial_price: float, max_price: float, fee_tier: str) -> Optional[Dict[str, Any]]`
- `create_manifest_market(base_mint: str, quote_mint: str) -> Optional[Dict[str, Any]]`
- `create_meteora_dlmm_pool(bin_step: int, token_a_mint: Pubkey, token_b_mint: Pubkey, initial_price: float, price_rounding_up: bool, fee_bps: int, activation_type: ActivationType, has_alpha_vault: bool, activation_point: Optional[int])`
- `create_multisig_proposal(transaction_index: int) -> Optional[Dict[str, Any]]`
- `create_openbook_market(base_mint: str, quote_mint: str, lot_size: Optional[float] = 1, tick_size: Optional[float] = 0.01) -> Optional[Dict[str, Any]]`
- `create_squads_multisig(creator: str) -> Optional[Dict[str, Any]]`
- `create_tiplink(amount: float, spl_mint_address: Optional[str] = None) -> Optional[Dict[str, Any]]`
- `create_webhook(webhook_url: str, transaction_types: list, account_addresses: list, webhook_type: str, txn_status: str = 'all', auth_header: Optional[str] = None)`
- `cybers_create_coin(name: str, symbol: str, image_path: str, tweet_author_id: str, tweet_author_username: str)`
- `delete_webhook(webhook_id: str)`
- `deploy_collection(name: str, uri: str, royalty_basis_points: int, creator_address: str)`
- `deploy_token(decimals: int = 6)`
- `deposit_into_drift_vault(amount: float, vault: str) -> Optional[Dict[str, Any]]`
- `deposit_strategy(deposit_amount: str, vault: str, strategy: str) -> Optional[Dict[str, Any]]`
- `deposit_to_drift_user_account(amount: float, symbol: str, is_repayment: Optional[bool] = None) -> Optional[Dict[str, Any]]`
- `deposit_to_multisig_treasury(amount: float, vault_index: int, mint: Optional[str] = None) -> Optional[Dict[str, Any]]`
- `derive_drift_vault_address(name: str) -> Optional[Dict[str, Any]]`
- `drift_swap_spot_token(from_symbol: str, to_symbol: str, slippage: Optional[float] = None, to_amount: Optional[float] = None, from_amount: Optional[float] = None) -> Optional[Dict[str, Any]]`
- `drift_user_account_info() -> Optional[Dict[str, Any]]`
- `edit_webhook(webhook_id: str, webhook_url: str, transaction_types: list, account_addresses: list, webhook_type: str, txn_status: str = 'all', auth_header: Optional[str] = None)`
- `execute_borrow_lend(quantity: str, side: str, symbol: str)`
- `execute_debridge_transaction(transaction_data: dict)`
- `execute_multisig_proposal(transaction_index: int) -> Optional[Dict[str, Any]]`
- `execute_order(**kwargs)`
- `fetch_all_domains(page: int = 1, limit: int = 50, verified: bool = False)`
- `fetch_domain_records(domain: str)`
- `fetch_domains_csv(verified: bool = False)`
- `fetch_leaderboard()`
- `fetch_most_viewed_tokens()`
- `fetch_new_tokens()`
- `fetch_positions() -> Optional[Dict[str, Any]]`
- `fetch_price(token_id: str)`
- `fetch_recently_verified_tokens()`
- `fetch_token_detailed_report(mint: str)`
- `fetch_token_flux_lp_lockers(token_id: str)`
- `fetch_token_lp_lockers(token_id: str)`
- `fetch_token_report_summary(mint: str)`
- `fetch_token_votes(mint: str)`
- `fetch_trending_tokens()`
- `flash_close_trade(token: str, side: str) -> Optional[Dict[str, Any]]`
- `flash_open_trade(token: str, side: str, collateral_usd: float, leverage: float) -> Optional[Dict[str, Any]]`
- `fluxbeam_create_pool(token_a: Pubkey, token_a_amount: float, token_b: Pubkey, token_b_amount: float) -> str`
- `get_account_balances()`
- `get_account_deposits(**kwargs)`
- `get_account_settings()`
- `get_active_listings(first_verified_creators: List[str], verified_collection_addresses: Optional[List[str]] = None, marketplaces: Optional[List[str]] = None, limit: Optional[int] = None, pagination_token: Optional[str] = None)`
- `get_address_name(address: str)`
- `get_all_domains_for_owner(owner: str)`
- `get_all_domains_tlds() -> Optional[List[str]]`
- `get_all_topics()`
- `get_all_webhooks()`
- `get_available_drift_markets() -> Optional[Dict[str, Any]]`
- `get_balance(token_address: Optional[Pubkey] = None)`
- `get_balances(address: str)`
- `get_borrow_history(**kwargs)`
- `get_borrow_lend_positions()`
- `get_borrow_position_history(**kwargs)`
- `get_bundle_statuses(bundle_uuids)`
- `get_collateral_info(sub_account_id: Optional[int] = None)`
- `get_depth(symbol: str)`
- `get_drift_entry_quote_of_perp_trade(amount: float, symbol: str, action: str) -> Optional[Dict[str, Any]]`
- `get_drift_lend_borrow_apy(symbol: str) -> Optional[Dict[str, Any]]`
- `get_drift_perp_market_funding_rate(symbol: str, period: str = 'year') -> Optional[Dict[str, Any]]`
- `get_drift_vault_info(vault_name: str) -> Optional[Dict[str, Any]]`
- `get_elfa_ai_api_key_status() -> dict`
- `get_favourite_domain(owner: str)`
- `get_fill_history(**kwargs)`
- `get_funding_interval_rates(symbol: str, limit: int = 100, offset: int = 0)`
- `get_funding_payments(**kwargs)`
- `get_inference_by_topic_id(topic_id: int)`
- `get_inflight_bundle_statuses(bundle_uuids)`
- `get_interest_history(**kwargs)`
- `get_klines(symbol: str, interval: str, start_time: int, end_time: Optional[int] = None)`
- `get_latest_pools()`
- `get_market(**kwargs)`
- `get_markets()`
- `get_mark_price(symbol: str)`
- `get_metaplex_asset(assetId: str)`
- `get_metaplex_assets_by_authority(authority: str, sortBy: Optional[Union[str, None]] = None, sortDirection: Optional[Union[str, None]] = None, limit: Optional[Union[int, None]] = None, page: Optional[Union[int, None]] = None, before: Optional[Union[str, None]] = None, after: Optional[Union[str, None]] = None)`
- `get_metaplex_assets_by_creator(creator: str, onlyVerified: bool = False, sortBy: Optional[Union[str, None]] = None, sortDirection: Optional[Union[str, None]] = None, limit: Optional[Union[int, None]] = None, page: Optional[Union[int, None]] = None, before: Optional[Union[str, None]] = None, after: Optional[Union[str, None]] = None)`
- `get_mintlists(first_verified_creators: List[str], verified_collection_addresses: Optional[List[str]] = None, limit: Optional[int] = None, pagination_token: Optional[str] = None)`
- `get_nft_events(accounts: List[str], types: Optional[List[str]] = None, sources: Optional[List[str]] = None, start_slot: Optional[int] = None, end_slot: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None, first_verified_creator: Optional[List[str]] = None, verified_collection_address: Optional[List[str]] = None, limit: Optional[int] = None, sort_order: Optional[str] = None, pagination_token: Optional[str] = None)`
- `get_nft_fingerprint(mints: List[str])`
- `get_nft_metadata(mint_accounts: List[str])`
- `get_open_interest(symbol: str)`
- `get_open_orders(**kwargs)`
- `get_open_positions()`
- `get_order_history(**kwargs)`
- `get_owned_all_domains(owner: str) -> Optional[List[str]]`
- `get_owned_domains_for_tld(tld: str) -> Optional[List[str]]`
- `get_parsed_transaction_history(address: str, before: str = '', until: str = '', commitment: str = '', source: str = '', type: str = '')`
- `get_parsed_transactions(transactions: List[str], commitment: Optional[str] = None)`
- `get_pnl_history(**kwargs)`
- `get_position_values(vault: str) -> Optional[Dict[str, Any]]`
- `get_price_prediction(asset: PriceInferenceToken, timeframe: PriceInferenceTimeframe, signature_format: SignatureFormat = <SignatureFormat.ETHEREUM_SEPOLIA: 'ethereum_sepolia'>)`
- `get_pump_curve_state(conn: AsyncClient, curve_address: Pubkey)`
- `get_random_tip_account()`
- `get_raw_transactions(accounts: List[str], start_slot: Optional[int] = None, end_slot: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: Optional[int] = None, sort_order: Optional[str] = None, pagination_token: Optional[str] = None)`
- `get_recent_trades(symbol: str, limit: int = 100)`
- `get_registration_transaction(domain: str, buyer: str, buyer_token_account: str, space: int, mint: Optional[str] = None, referrer_key: Optional[str] = None)`
- `get_settlement_history(**kwargs)`
- `get_smart_mentions(limit: int = 100, offset: int = 0) -> dict`
- `get_smart_twitter_account_stats(username: str) -> dict`
- `get_status()`
- `get_supported_assets()`
- `get_system_time()`
- `get_ticker_information(**kwargs)`
- `get_tickers()`
- `get_tip_accounts()`
- `get_token_data_by_address(mint: str)`
- `get_token_data_by_ticker(ticker: str)`
- `get_token_info(token_address: str)`
- `get_token_price_data(token_addresses: list[str])`
- `get_top_gainers(duration: str = '24h', top_coins: Union[int, str] = 'all')`
- `get_top_mentions_by_ticker(ticker: str, time_window: str = '1h', page: int = 1, page_size: int = 10, include_account_details: bool = False) -> dict`
- `get_tps()`
- `get_trending_pools(duration: str = '24h')`
- `get_trending_tokens()`
- `get_trending_tokens_using_elfa_ai(time_window: str = '24h', page: int = 1, page_size: int = 50, min_mentions: int = 5) -> dict`
- `get_users_open_orders(**kwargs)`
- `get_webhook(webhook_id: str)`
- `launch_pump_fun_token(token_name: str, token_ticker: str, description: str, image_url: str, options: Optional[PumpfunTokenOptions] = None)`
- `lend_assets(amount: float)`
- `list_nft_for_sale(price: float, nft_mint: str) -> Optional[Dict[str, Any]]`
- `list_tools(selected_actions: Dict[str, Tool]) -> List[Tool]`
- `lookup_domain(domain: str)`
- `lulo_lend(mint_address: Pubkey, amount: float) -> str`
- `lulo_withdraw(mint_address: Pubkey, amount: float) -> str`
- `merge_tokens(input_assets: List[Dict[str, Any]], output_mint: str, priority_fee: str) -> Optional[Dict[str, Any]]`
- `mint_metaplex_core_nft(collectionMint: str, name: str, uri: str, sellerFeeBasisPoints: Optional[Union[int, None]] = None, address: Optional[Union[str, None]] = None, share: Optional[Union[str, None]] = None, recipient: Optional[Union[str, None]] = None)`
- `multiple_burn_and_close_accounts(token_accounts: list[str])`
- `open_centered_position(whirlpool_address: str, price_offset_bps: int, input_token_mint: str, input_amount: float) -> Optional[Dict[str, Any]]`
- `open_perp_trade_long(price: float, collateral_amount: float, collateral_mint: Optional[str] = None, leverage: Optional[float] = None, trade_mint: Optional[str] = None, slippage: Optional[float] = None) -> Optional[Dict[str, Any]]`
- `open_perp_trade_short(price: float, collateral_amount: float, collateral_mint: Optional[str] = None, leverage: Optional[float] = None, trade_mint: Optional[str] = None, slippage: Optional[float] = None) -> Optional[Dict[str, Any]]`
- `open_single_sided_position(whirlpool_address: str, distance_from_current_price_bps: int, width_bps: int, input_token_mint: str, input_amount: float) -> Optional[Dict[str, Any]]`
- `parse_key_value_string(s: str) -> dict`
- `ping_elfa_ai_api() -> dict`
- `place_batch_orders(market_id: str, orders: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]`
- `place_limit_order(market_id: str, quantity: float, side: str, price: float) -> Optional[Dict[str, Any]]`
- `pyth_fetch_price(mint_str: str)`
- `reject_multisig_proposal(transaction_index: int) -> Optional[Dict[str, Any]]`
- `request_faucet_funds()`
- `request_unstake_from_drift_insurance_fund(amount: float, symbol: str) -> Optional[Dict[str, Any]]`
- `request_withdrawal(address: str, blockchain: str, quantity: str, symbol: str, **kwargs)`
- `request_withdrawal_from_drift_vault(amount: float, vault: str) -> Optional[Dict[str, Any]]`
- `resolve_all_domains(domain: str) -> Optional[str]`
- `resolve_name_to_address(domain: str)`
- `restake(amount: float)`
- `rock_paper_scissors(amount: float, choice: str)`
- `search_mentions_by_keywords(keywords: str, from_timestamp: int, to_timestamp: int, limit: int = 20, cursor: Optional[str] = None) -> dict`
- `sell_token(mint: Pubkey, bonding_curve: Pubkey, associated_bonding_curve: Pubkey, amount: float, slippage: float, max_retries: int)`
- `sell_using_moonshot(mint_str: str, token_balance: float = 0.01, slippage_bps: int = 500)`
- `sell_with_raydium(pair_address: str, percentage: int = 100, slippage: int = 5)`
- `send_bundle(params=None)`
- `send_compressed_airdrop(mint_address: str, amount: float, decimals: int, recipients: List[str], priority_fee_in_lamports: int, should_log: Optional[bool] = False) -> Optional[List[str]]`
- `send_ping()`
- `send_txn(params=None, bundleOnly=False)`
- `simulate_switchboard_feed(feed: str, crossbar_url: Optional[str] = None) -> Optional[Dict[str, Any]]`
- `spread_token(input_asset: Dict[str, Any], target_tokens: List[Dict[str, Any]], priority_fee: str) -> Optional[Dict[str, Any]]`
- `stake(amount: int)`
- `stake_to_drift_insurance_fund(amount: float, symbol: str) -> Optional[Dict[str, Any]]`
- `stork_fetch_price(asset_id: str)`
- `trade(output_mint: Pubkey, input_amount: float, input_mint: Optional[Pubkey] = None, slippage_bps: int = 500)`
- `trade_using_delegated_drift_vault(vault: str, amount: float, symbol: str, action: str, trade_type: str, price: Optional[float] = None) -> Optional[Dict[str, Any]]`
- `trade_using_drift_perp_account(amount: float, symbol: str, action: str, trade_type: str, price: Optional[float] = None) -> Optional[Dict[str, Any]]`
- `transfer(to: str, amount: float, mint: Optional[Pubkey] = None)`
- `transfer_from_multisig_treasury(amount: float, to: str, vault_index: int, mint: str) -> Optional[Dict[str, Any]]`
- `unstake_from_drift_insurance_fund(symbol: str) -> Optional[Dict[str, Any]]`
- `update_account_settings(**kwargs)`
- `update_drift_vault(vault_address: str, name: str, market_name: str, redeem_period: int, max_tokens: int, min_deposit_amount: float, management_fee: float, profit_share: float, hurdle_rate: Optional[float] = None, permissioned: Optional[bool] = None) -> Optional[Dict[str, Any]]`
- `update_drift_vault_delegate(vault: str, delegate_address: str) -> Optional[Dict[str, Any]]`
- `withdraw_all(market_id: str) -> Optional[Dict[str, Any]]`
- `withdraw_from_drift_user_account(amount: float, symbol: str, is_borrow: Optional[bool] = None) -> Optional[Dict[str, Any]]`
- `withdraw_from_drift_vault(vault: str) -> Optional[Dict[str, Any]]`
- `withdraw_strategy(withdraw_amount: str, vault: str, strategy: str) -> Optional[Dict[str, Any]]`

Common Examples (Illustrative):
- Get agent's SOL balance: {"action": "get_balance"}
- Get SOL balance of another wallet: {"action": "get_balance", "owner": "SomeOtherWalletAddressString"}
- Get agent's USDC balance: {"action": "get_balance", "token_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}
- Transfer 0.5 SOL: {"action": "transfer", "to": "RecipientPublicKeyString", "amount": 0.5}
- Fetch price for SOL: {"action": "fetch_price", "token_id": "SOL"}
- Swap 0.1 SOL for USDC: {"action": "trade", "input_amount": 0.1, "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}
"""

        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The specific SolanaAgentKit method to call.",
                    "enum": available_actions,  # Use the static list
                },
                # Define args as a generic object, relying *heavily* on the static description
                "args": {
                    "type": "object",
                    "description": args_description,  # Use the static description
                    "additionalProperties": True,
                },
            },
            "required": ["action"],
            # Examples remain the same, matching the flat structure handled by execute(**kwargs)
            "examples": [
                {
                    "summary": "Get agent's SOL balance",
                    "value": {"action": "get_balance"},
                },
                {
                    "summary": "Get agent's USDC balance",
                    "value": {
                        "action": "get_balance",
                        "token_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    },
                },
                {
                    "summary": "Transfer 0.5 SOL",
                    "value": {
                        "action": "transfer",
                        "to": "RecipientPublicKeyString",
                        "amount": 0.5,
                    },
                },
                {
                    "summary": "Transfer 10 USDC",
                    "value": {
                        "action": "transfer",
                        "to": "RecipientPublicKeyString",
                        "amount": 10.0,
                        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    },
                },
                {
                    "summary": "Fetch price for SOL",
                    "value": {"action": "fetch_price", "token_id": "SOL"},
                },
                {
                    "summary": "Swap 0.1 SOL for USDC",
                    "value": {
                        "action": "trade",
                        "input_amount": 0.1,
                        "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    },
                },
            ],
        }

    # --- Keep configure method as is ---
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the tool and initialize SolanaAgentKit."""
        super().configure(config)
        kit_config = {}

        if "tools" in config and "solana" in config["tools"]:
            kit_config = config["tools"].get("solana", {})

            try:
                self._kit = SolanaAgentKit(**kit_config)
                logger.info(
                    f"SolanaAgentKit initialized successfully for wallet: {self._kit.wallet_address}"
                )
            except Exception as e:
                logger.error(f"ERROR: Failed to initialize SolanaAgentKit: {e}")
                logger.error(
                    "Ensure configuration contains necessary keys like 'private_key', 'rpc_url', etc."
                )
                self._kit = None

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the specified SolanaAgentKit method with type conversion.
        Accepts 'action' and other parameters via kwargs, reconstructing 'args'.
        """
        logger.debug(
            f"Received kwargs in execute: {kwargs}"
        )  # Changed print to logger.debug
        if not self._kit:
            return {"status": "error", "message": "SolanaAgentKit is not initialized."}
        if "action" not in kwargs:
            return {"status": "error", "message": "Missing 'action' parameter."}
        action = kwargs.pop("action")
        args = kwargs
        logger.debug(
            f"Reconstructed action='{action}', args={args}"
        )  # Changed print to logger.debug
        if not isinstance(args, dict):
            return {
                "status": "error",
                "message": f"Internal Error: Args not a dict. Got {type(args)}",
            }

        processed_args = {}
        method_to_call = None

        try:
            method_to_call = getattr(self._kit, action, None)
            if not method_to_call or not callable(method_to_call):
                # Check if action exists even if not in the static enum (shouldn't happen often now)
                if hasattr(SolanaAgentKit, action) and callable(
                    getattr(SolanaAgentKit, action)
                ):
                    logger.warning(  # Changed print to logger.warning
                        f"Action '{action}' exists but was not in the static schema enum. Attempting execution."
                    )
                else:
                    return {"status": "error", "message": f"Invalid action '{action}'."}

            # Need inspect here ONLY for the execute logic, not schema generation
            import inspect

            sig = inspect.signature(method_to_call)
            parameters = sig.parameters

            for arg_name, arg_value in args.items():
                if arg_name in parameters:
                    param = parameters[arg_name]
                    expected_type = param.annotation
                    is_optional = False

                    # Handle Optional[T] and Union[T, None]
                    if hasattr(expected_type, "__origin__") and (
                        expected_type.__origin__ is Optional
                        or expected_type.__origin__ is Union
                    ):
                        inner_types = getattr(expected_type, "__args__", ())
                        actual_inner_types = [
                            t for t in inner_types if t is not type(None)
                        ]
                        if type(None) in inner_types:
                            is_optional = True
                        if len(actual_inner_types) == 1:
                            expected_type = actual_inner_types[0]
                        elif len(actual_inner_types) > 1:
                            expected_type = Any  # Treat complex Union as Any
                        else:
                            expected_type = Any  # Only NoneType

                    if is_optional and arg_value is None:
                        processed_args[arg_name] = None
                        continue

                    # --- Type Casting Logic ---
                    try:
                        if expected_type == Pubkey:
                            if isinstance(arg_value, str):
                                processed_args[arg_name] = Pubkey.from_string(arg_value)
                            elif isinstance(arg_value, Pubkey):
                                processed_args[arg_name] = arg_value
                            else:
                                raise ValueError(
                                    "Expected string for Pubkey conversion"
                                )
                        elif expected_type is float:
                            processed_args[arg_name] = float(arg_value)
                        elif expected_type is int:
                            processed_args[arg_name] = int(arg_value)
                        elif expected_type is str:
                            processed_args[arg_name] = str(arg_value)
                        elif expected_type is bool:
                            if isinstance(arg_value, str):
                                if arg_value.lower() in ["true", "1", "yes", "y"]:
                                    processed_args[arg_name] = True
                                elif arg_value.lower() in ["false", "0", "no", "n"]:
                                    processed_args[arg_name] = False
                                else:
                                    raise ValueError(
                                        f"Cannot convert string '{arg_value}' to bool"
                                    )
                            else:
                                processed_args[arg_name] = bool(arg_value)
                        elif (
                            hasattr(expected_type, "__origin__")
                            and expected_type.__origin__ is list
                            and isinstance(arg_value, list)
                        ):
                            inner_list_type = getattr(
                                expected_type, "__args__", (Any,)
                            )[0]
                            if inner_list_type is str:
                                processed_args[arg_name] = [
                                    str(item) for item in arg_value
                                ]
                            elif inner_list_type is int:
                                processed_args[arg_name] = [
                                    int(item) for item in arg_value
                                ]
                            elif inner_list_type is float:
                                processed_args[arg_name] = [
                                    float(item) for item in arg_value
                                ]
                            # Add Pubkey list handling if needed
                            # elif inner_list_type == Pubkey: processed_args[arg_name] = [Pubkey.from_string(item) if isinstance(item, str) else item for item in arg_value]
                            else:
                                processed_args[arg_name] = arg_value
                        # Handle specific complex types used in signatures
                        # Add BondingCurveState, PumpfunTokenOptions if they need specific casting from dict/str
                        # elif expected_type == BondingCurveState and isinstance(arg_value, dict):
                        #     processed_args[arg_name] = BondingCurveState(**arg_value) # Example if it takes kwargs
                        else:
                            processed_args[arg_name] = arg_value
                            logger.debug(  # Changed print to logger.debug
                                f"Passing arg '{arg_name}' as is (type: {type(arg_value)}, expected: {expected_type})"
                            )

                    except (ValueError, TypeError) as cast_err:
                        # Need format_type_hint back just for this error message, or use simple str()
                        # param_annotation_str = format_type_hint(param.annotation) # Option 1
                        param_annotation_str = str(
                            param.annotation
                        )  # Option 2 (simpler)
                        return {
                            "status": "error",
                            "message": f"Failed to convert argument '{arg_name}' with value '{arg_value}' to expected type {param_annotation_str}. Error: {cast_err}",
                        }
                    # --- End Type Casting ---

                else:
                    logger.warning(  # Changed print to logger.warning
                        f"Unexpected argument '{arg_name}' provided for action '{action}'. Ignoring."
                    )

            logger.debug(
                f"Executing {action} with processed args: {processed_args}"
            )  # Changed print to logger.debug
            result = await method_to_call(**processed_args)

            # Convert result
            if isinstance(result, dict):
                final_result = {
                    k: str(v) if isinstance(v, Pubkey) else v for k, v in result.items()
                }
            elif isinstance(result, Pubkey):
                final_result = str(result)
            elif isinstance(result, list):
                final_result = [
                    str(item) if isinstance(item, Pubkey) else item for item in result
                ]
            else:
                final_result = result

            return {
                "status": "success",
                "action_called": action,
                "result": final_result,
            }

        except TypeError as e:
            logger.error(
                f"Type Error executing '{action}' with {processed_args}: {e}"
            )  # Changed print to logger.error
            sig_repr = "N/A"
            if method_to_call:
                try:
                    # Need inspect here ONLY for the error message
                    import inspect

                    sig_repr = inspect.signature(method_to_call)
                except Exception:
                    pass
            return {
                "status": "error",
                "message": f"Type mismatch for '{action}'. Expected: {sig_repr}. Error: {e}",
            }
        except Exception as e:
            # Use logger.exception to include traceback automatically
            logger.exception(
                f"Unexpected Error executing '{action}': {e}"
            )  # Changed print to logger.exception and removed traceback.format_exc()
            return {"status": "error", "message": f"Unexpected Error: {e}"}


# --- Keep Plugin class and get_plugin function as is ---
class SolanaAgentKitPlugin:
    """Plugin for integrating SolanaAgentKit (agentipy) with Solana Agent."""

    def __init__(self):
        self.name = "solana"
        self.config = None
        self.tool_registry = None
        self._tool = None
        logger.info(
            f"Created SolanaAgentKitPlugin object with name: {self.name}"
        )  # Changed print to logger.info

    @property
    def description(self):
        return "Plugin providing access to Solana blockchain functions via Agentipy's SolanaAgentKit."

    def initialize(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        logger.info(f"Initializing {self.name} plugin")  # Changed print to logger.info
        self._tool = SolanaAgentKitTool(registry=tool_registry)
        all_tools = tool_registry.list_all_tools()
        logger.info(
            f"All registered tools after {self.name} init: {all_tools}"
        )  # Changed print to logger.info
        registered_tool = tool_registry.get_tool(self.name)
        logger.info(  # Changed print to logger.info
            f"{self.name} registration verification: {'Success' if registered_tool else 'Failed'}"
        )

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = config
        logger.info(f"Configuring {self.name} plugin")  # Changed print to logger.info
        if self._tool:
            self._tool.configure(self.config)
            logger.info(f"{self.name} tool configured.")  # Changed print to logger.info
        else:
            logger.warning(
                f"Warning: {self.name} tool instance not found during configuration."
            )  # Changed print to logger.warning

    def get_tools(self) -> List[AutoTool]:
        if self._tool:
            logger.debug(
                f"Returning tool: {self._tool.name}"
            )  # Changed print to logger.debug
            return [self._tool]
        logger.warning(
            f"Warning: No tool instance found for {self.name} in get_tools."
        )  # Changed print to logger.warning
        return []


def get_plugin():
    return SolanaAgentKitPlugin()
