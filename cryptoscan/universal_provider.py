"""Universal blockchain provider for ALL networks"""

from decimal import Decimal
from typing import List, Optional

from .config import UserConfig
from .models import PaymentInfo
from .networks import NetworkConfig, get_network
from .rpc_client import RPCClient
from .adapters import get_adapter
from .chain_parsers import EVMParser, SolanaParser, BitcoinParser


class UniversalProvider:
    """
    Universal provider that works with ANY blockchain
    Dynamically adapts to network type (EVM, Solana, Cosmos, etc.)
    """
    
    def __init__(
        self,
        network: str | NetworkConfig,
        rpc_url: Optional[str] = None,
        user_config: Optional[UserConfig] = None
    ):
        # Get network config
        if isinstance(network, str):
            self.network_config = get_network(network)
            if not self.network_config:
                raise ValueError(f"Unknown network: {network}")
        else:
            self.network_config = network
        
        # Use custom RPC or default
        self.rpc_url = rpc_url or self.network_config.rpc_url
        self.config = user_config or UserConfig()
        
        # Check if network has custom API adapter
        self.api_adapter = None
        if self.network_config.api_adapter:
            self.api_adapter = get_adapter(
                self.network_config.api_adapter,
                self.rpc_url,
                self.network_config
            )
        
        self.client = RPCClient(self.rpc_url, self.config)
        self._parser = self._create_parser()
    
    @property
    def NETWORK_NAME(self) -> str:
        """Get network name"""
        return self.network_config.name
    
    @property
    def CURRENCY_SYMBOL(self) -> str:
        """Get currency symbol"""
        return self.network_config.symbol
    
    async def connect(self):
        """Connect to RPC"""
        await self.client.connect()
    
    async def close(self):
        """Close connections"""
        await self.client.close()
        if isinstance(self._parser, BitcoinParser):
            await self._parser.close()
        if self.api_adapter:
            await self.api_adapter.close()
    
    def _create_parser(self):
        """Create appropriate parser for chain type"""
        chain_type = self.network_config.chain_type
        
        if chain_type == "evm":
            return EVMParser(self.client, self.network_config, self.CURRENCY_SYMBOL)
        elif chain_type == "solana":
            return SolanaParser(self.client, self.network_config, self.CURRENCY_SYMBOL)
        elif chain_type == "bitcoin":
            return BitcoinParser(self.network_config, self.CURRENCY_SYMBOL, self.config.timeout)
        else:
            return None
    
    async def validate_wallet_address(self, address: str) -> bool:
        """Validate wallet address format"""
        return self.network_config.validate_address(address)
    
    async def get_recent_transactions(
        self,
        wallet_address: str,
        limit: int = 10
    ) -> List[PaymentInfo]:
        """Get recent transactions"""
        if self.api_adapter:
            return await self.api_adapter.get_transactions(wallet_address, limit)
        
        if self._parser and hasattr(self._parser, 'get_transactions'):
            return await self._parser.get_transactions(wallet_address, limit)
        
        return []
    
    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """Get transaction details"""
        if self.api_adapter:
            return await self.api_adapter.get_transaction(transaction_id)
        
        if self._parser and hasattr(self._parser, 'get_transaction'):
            return await self._parser.get_transaction(transaction_id)
        
        return None
    
    async def find_payment(
        self,
        wallet_address: str,
        expected_amount: Decimal,
        max_transactions: int = 10
    ) -> Optional[PaymentInfo]:
        """Find payment matching expected amount"""
        transactions = await self.get_recent_transactions(wallet_address, max_transactions)
        
        for tx in transactions:
            if tx.amount == expected_amount:
                return tx
        
        return None
    
    def _parse_evm_tx(self, tx: dict, block: dict = None, receipt: dict = None) -> PaymentInfo:
        """Parse EVM transaction (used by RealtimeStrategy)"""
        if self._parser and hasattr(self._parser, 'parse_transaction'):
            return self._parser.parse_transaction(tx, block, receipt)
        raise NotImplementedError("EVM parser not available")
    
    def __repr__(self):
        return f"UniversalProvider(network={self.NETWORK_NAME}, type={self.network_config.chain_type}, rpc={self.rpc_url})"
