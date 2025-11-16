"""
Chain-specific transaction parsers
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .models import PaymentInfo, PaymentStatus


class EVMParser:
    """Parser for EVM-compatible chains"""
    
    def __init__(self, client, network_config, currency_symbol):
        self.client = client
        self.network_config = network_config
        self.currency_symbol = currency_symbol
    
    async def get_transactions(self, address: str, limit: int) -> List[PaymentInfo]:
        """Get EVM transactions"""
        await self.client.connect()
        
        latest_block = await self.client.call("eth_blockNumber")
        block_num = int(latest_block, 16)
        
        transactions = []
        blocks_to_check = min(limit * 5, 100)
        
        for i in range(blocks_to_check):
            try:
                block = await self.client.call("eth_getBlockByNumber", [hex(block_num - i), True])
                if not block or not block.get("transactions"):
                    continue
                
                for tx in block["transactions"]:
                    if tx.get("to", "").lower() == address.lower():
                        payment = self.parse_transaction(tx, block)
                        transactions.append(payment)
                        if len(transactions) >= limit:
                            return transactions
            except:
                continue
        
        return transactions
    
    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single EVM transaction"""
        await self.client.connect()
        try:
            tx = await self.client.call("eth_getTransactionByHash", [tx_id])
            if not tx:
                return None
            receipt = await self.client.call("eth_getTransactionReceipt", [tx_id])
            return self.parse_transaction(tx, receipt=receipt)
        except:
            return None
    
    def parse_transaction(self, tx: dict, block: dict = None, receipt: dict = None) -> PaymentInfo:
        """Parse EVM transaction"""
        value_wei = int(tx.get("value", "0x0"), 16)
        amount = Decimal(value_wei) / Decimal(10 ** self.network_config.decimals)
        
        block_number = None
        timestamp = datetime.utcnow()
        if block:
            block_number = int(block.get("number", "0x0"), 16)
            timestamp = datetime.fromtimestamp(int(block.get("timestamp", "0x0"), 16))
        elif tx.get("blockNumber"):
            block_number = int(tx["blockNumber"], 16)
        
        status = PaymentStatus.CONFIRMED if block_number else PaymentStatus.PENDING
        if receipt and receipt.get("status") == "0x0":
            status = PaymentStatus.FAILED
        
        return PaymentInfo(
            transaction_id=tx["hash"],
            wallet_address=tx.get("to", ""),
            amount=amount,
            currency=self.currency_symbol,
            status=status,
            timestamp=timestamp,
            block_height=block_number,
            confirmations=0,
            fee=None,
            from_address=tx.get("from", ""),
            to_address=tx.get("to", ""),
            raw_data={"tx": tx, "receipt": receipt, "block": block}
        )


class SolanaParser:
    """Parser for Solana transactions"""
    
    def __init__(self, client, network_config, currency_symbol):
        self.client = client
        self.network_config = network_config
        self.currency_symbol = currency_symbol
    
    async def get_transactions(self, address: str, limit: int) -> List[PaymentInfo]:
        """Get Solana transactions"""
        await self.client.connect()
        signatures = await self.client.call("getSignaturesForAddress", [address, {"limit": limit}])
        
        transactions = []
        for sig_info in signatures or []:
            tx = await self.get_transaction(sig_info["signature"])
            if tx:
                transactions.append(tx)
        return transactions
    
    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get Solana transaction"""
        await self.client.connect()
        try:
            result = await self.client.call(
                "getTransaction",
                [tx_id, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            )
            if not result:
                return None
            
            return self.parse_transaction(result)
        except:
            return None
    
    def parse_transaction(self, result: dict) -> Optional[PaymentInfo]:
        """Parse Solana transaction"""
        try:
            meta = result.get("meta", {})
            message = result.get("transaction", {}).get("message", {})
            
            pre = meta.get("preBalances", [])
            post = meta.get("postBalances", [])
            amount = Decimal(abs(post[0] - pre[0]) if post and pre else 0) / Decimal(10 ** self.network_config.decimals)
            
            return PaymentInfo(
                transaction_id=result.get("transaction", {}).get("signatures", [""])[0] if result.get("transaction") else "",
                wallet_address=message.get("accountKeys", [""])[0],
                amount=amount,
                currency=self.currency_symbol,
                status=PaymentStatus.CONFIRMED if meta.get("err") is None else PaymentStatus.FAILED,
                timestamp=datetime.fromtimestamp(result.get("blockTime", 0)),
                block_height=result.get("slot"),
                confirmations=0,
                fee=Decimal(meta.get("fee", 0)) / Decimal(10 ** self.network_config.decimals),
                from_address=message.get("accountKeys", [""])[0] if message.get("accountKeys") else "",
                to_address=message.get("accountKeys", ["", ""])[1] if len(message.get("accountKeys", [])) > 1 else "",
                raw_data=result
            )
        except:
            return None


class BitcoinParser:
    """Parser for Bitcoin transactions using RPC"""
    
    def __init__(self, client, network_config, currency_symbol):
        self.client = client
        self.network_config = network_config
        self.currency_symbol = currency_symbol
    
    async def get_transactions(self, address: str, limit: int) -> List[PaymentInfo]:
        """Get Bitcoin transactions via RPC"""
        await self.client.connect()
        
        try:
            # Use Bitcoin RPC methods
            result = await self.client.call("scantxoutset", ["start", [f"addr({address})"]],)
            # Note: Bitcoin RPC has limited transaction history access
            # For full transaction history, users should use block explorers or indexers
            return []
        except:
            return []
    
    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get Bitcoin transaction via RPC"""
        await self.client.connect()
        
        try:
            tx = await self.client.call("getrawtransaction", [tx_id, True])
            if not tx:
                return None
            return self.parse_transaction(tx)
        except:
            return None
    
    def parse_transaction(self, tx: dict, address: str = None) -> PaymentInfo:
        """Parse Bitcoin RPC transaction"""
        amount = Decimal(0)
        to_addr = ""
        
        # Parse vout for receiving amounts
        for vout in tx.get("vout", []):
            value = Decimal(vout.get("value", 0))
            amount += value
            if vout.get("scriptPubKey", {}).get("addresses"):
                to_addr = vout["scriptPubKey"]["addresses"][0]
        
        from_addr = ""
        if tx.get("vin") and tx["vin"][0].get("txid"):
            from_addr = "<coinbase>" if "coinbase" in tx["vin"][0] else "<unknown>"
        
        return PaymentInfo(
            transaction_id=tx.get("txid", ""),
            wallet_address=to_addr,
            amount=amount,
            currency=self.currency_symbol,
            status=PaymentStatus.CONFIRMED if tx.get("confirmations", 0) > 0 else PaymentStatus.PENDING,
            timestamp=datetime.fromtimestamp(tx.get("time", 0)) if tx.get("time") else datetime.utcnow(),
            block_height=tx.get("blockheight"),
            confirmations=tx.get("confirmations", 0),
            fee=None,
            from_address=from_addr,
            to_address=to_addr,
            raw_data=tx
        )
