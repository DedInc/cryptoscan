"""Solana chain parser."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from ..core.exceptions import CSConnectionError, CSTimeoutError, RPCError
from ..core.models import (
    MatchMode,
    PaymentInfo,
    PaymentStatus,
    TokenConfig,
    match_amount,
)
from ..security import mask_address
from .base import ChainParser
from .solana_spl import (
    build_balance_map,
    build_spl_payment_info,
    compute_incoming_delta,
    find_spl_sender,
)

__all__ = ["SolanaParser"]

logger = logging.getLogger(__name__)

_NETWORK_ERRORS = (RPCError, CSConnectionError, CSTimeoutError)
_PARSE_ERRORS = (KeyError, ValueError, TypeError, IndexError)


def _resolve_token_address(token_contract: str | TokenConfig | None) -> str | None:
    if token_contract is None:
        return None
    if isinstance(token_contract, TokenConfig):
        return token_contract.contract_address
    return token_contract


class SolanaParser(ChainParser):
    """Parser for Solana transactions."""

    async def get_block_number(self) -> int:
        await self.client.connect()
        return int(await self.client.call("getSlot", []))

    async def get_block_for_payment(
        self,
        block_identifier: str,
        wallet_address: str,
        expected_amount: Decimal | None,
        latest_block_num: int | None = None,  # noqa: ARG002
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        await self.client.connect()
        mode = match_mode or MatchMode.EXACT
        try:
            slot = (
                int(block_identifier, 16)
                if isinstance(block_identifier, str)
                and block_identifier.startswith("0x")
                else int(block_identifier)
            )
            block = await self.client.call(
                "getBlock",
                [slot, {"encoding": "json", "maxSupportedTransactionVersion": 0}],
            )
            if not block or not block.get("transactions"):
                return None
            for tx_entry in block["transactions"]:
                result = self._build_result_from_entry(tx_entry, slot, block)
                payment = self._parse_with_token(result, wallet_address, token_contract)
                if payment and match_amount(payment.amount, expected_amount, mode):
                    return payment
        except _NETWORK_ERRORS as e:
            logger.warning(
                "Error fetching Solana block %s: %s",
                block_identifier,
                e.__class__.__name__,
            )
        except (*_PARSE_ERRORS, ArithmeticError) as e:
            logger.warning(
                "Error parsing Solana block %s: %s",
                block_identifier,
                e.__class__.__name__,
            )
        return None

    @staticmethod
    def _build_result_from_entry(tx_entry: dict, slot: int, block: dict) -> dict:
        return {
            "transaction": tx_entry.get("transaction", {}),
            "meta": tx_entry.get("meta") or {},
            "slot": slot,
            "blockTime": block.get("blockTime"),
        }

    async def get_transactions(
        self,
        address: str,
        limit: int,
        expected_amount: Decimal | None = None,
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> list[PaymentInfo]:
        await self.client.connect()
        mode = match_mode or MatchMode.EXACT
        token_display = _resolve_token_address(token_contract)
        logger.info(
            "Fetching Solana transactions for %s (mode=%s, token=%s)",
            mask_address(address),
            mode.value,
            mask_address(token_display) if token_display else "native",
        )
        signatures = await self.client.call(
            "getSignaturesForAddress", [address, {"limit": limit}]
        )
        if not signatures:
            return []
        transactions: list[PaymentInfo] = []
        for sig_info in signatures:
            matched = await self._process_signature(
                sig_info, address, token_contract, expected_amount, mode, transactions
            )
            if matched is not None:
                return [matched]
            if len(transactions) >= limit:
                return transactions
        return transactions

    async def _process_signature(
        self,
        sig_info: dict,
        address: str,
        token_contract: str | TokenConfig | None,
        expected_amount: Decimal | None,
        mode: MatchMode,
        transactions: list[PaymentInfo],
    ) -> PaymentInfo | None:
        sig = sig_info.get("signature", "")
        if not sig:
            return None
        try:
            result = await self._fetch_raw_transaction(sig)
            if not result:
                return None
            payment = self._parse_with_token(result, address, token_contract)
            if not payment:
                return None
            logger.info(
                "Found TX: %s, amount: %s %s",
                sig[:16],
                payment.amount,
                payment.currency,
            )
            if expected_amount is not None and match_amount(
                payment.amount, expected_amount, mode
            ):
                logger.info(
                    "MATCH! Amount %s matches expected %s (mode=%s)",
                    payment.amount,
                    expected_amount,
                    mode.value,
                )
                return payment
            transactions.append(payment)
        except _NETWORK_ERRORS as e:
            logger.debug(
                "Skipping transaction %s...: %s", sig[:16], e.__class__.__name__
            )
        return None

    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        await self.client.connect()
        try:
            result = await self._fetch_raw_transaction(tx_id)
            if not result:
                return None
            return self.parse_transaction(result)
        except _PARSE_ERRORS as e:
            logger.warning(
                "Failed to parse transaction %s: %s", tx_id[:16], e.__class__.__name__
            )
            return None

    def _parse_with_token(
        self,
        result: dict,
        wallet_address: str,
        token_contract: str | TokenConfig | None,
    ) -> PaymentInfo | None:
        if token_contract:
            spl_payment = self._parse_spl_transfer(
                result, token_contract, wallet_address
            )
            if spl_payment:
                return spl_payment
        return self.parse_transaction(result)

    def parse_transaction(self, result: dict) -> PaymentInfo | None:
        try:
            meta = result.get("meta") or {}
            message = result.get("transaction", {}).get("message", {})
            pre = meta.get("preBalances", [])
            post = meta.get("postBalances", [])
            amount = Decimal(abs(post[0] - pre[0]) if post and pre else 0) / Decimal(
                10**self.network_config.decimals
            )
            return PaymentInfo(
                transaction_id=(
                    result.get("transaction", {}).get("signatures", [""])[0]
                    if result.get("transaction")
                    else ""
                ),
                wallet_address=message.get("accountKeys", [""])[0],
                amount=amount,
                currency=self.currency_symbol,
                status=PaymentStatus.CONFIRMED
                if meta.get("err") is None
                else PaymentStatus.FAILED,
                timestamp=datetime.fromtimestamp(
                    result.get("blockTime", 0), tz=timezone.utc
                ),
                block_height=result.get("slot"),
                confirmations=0,
                fee=Decimal(meta.get("fee", 0))
                / Decimal(10**self.network_config.decimals),
                from_address=message.get("accountKeys", [""])[0]
                if message.get("accountKeys")
                else "",
                to_address=(
                    message.get("accountKeys", ["", ""])[1]
                    if len(message.get("accountKeys", [])) > 1
                    else ""
                ),
                raw_data=result,
            )
        except (*_PARSE_ERRORS, ArithmeticError) as e:
            logger.warning("Failed to parse Solana transaction data: %s", e)
            return None

    def _parse_spl_transfer(
        self,
        result: dict,
        token_contract: str | TokenConfig,
        wallet_address: str,
    ) -> PaymentInfo | None:
        meta = result.get("meta") or {}
        pre_balances = meta.get("preTokenBalances") or []
        post_balances = meta.get("postTokenBalances") or []
        token_addr, decimals, symbol = self._resolve_token_config(token_contract)
        pre_map = build_balance_map(pre_balances)
        delta = compute_incoming_delta(
            post_balances, pre_map, token_addr, wallet_address
        )
        if delta is None:
            return None
        delta_raw, _idx, _post_amt = delta
        amount = delta_raw / Decimal(10**decimals)
        from_address = find_spl_sender(
            pre_balances, post_balances, token_addr, wallet_address
        )
        return build_spl_payment_info(
            result,
            wallet_address,
            amount,
            token_addr,
            decimals,
            symbol,
            from_address,
            self.network_config.decimals,
        )

    @staticmethod
    def _find_spl_sender(
        pre_balances: list[dict],
        post_balances: list[dict],
        token_addr: str,
        wallet_address: str,
    ) -> str:
        return find_spl_sender(pre_balances, post_balances, token_addr, wallet_address)

    def _resolve_token_config(
        self, token_contract: str | TokenConfig
    ) -> tuple[str, int, str]:
        if isinstance(token_contract, TokenConfig):
            return (
                token_contract.contract_address,
                token_contract.decimals,
                token_contract.symbol,
            )
        return (token_contract, self.network_config.decimals, self.currency_symbol)

    async def _fetch_raw_transaction(self, tx_id: str) -> dict | None:
        return await self.client.call(
            "getTransaction",
            [tx_id, {"encoding": "json", "maxSupportedTransactionVersion": 0}],
        )
