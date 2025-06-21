from dataclasses import dataclass, field
from typing import Dict
from .core.base import NetworkConfig
from .exceptions import ConfigurationError


@dataclass
class CryptoScanConfig:
    default_poll_interval: float = 15.0
    default_max_transactions: int = 10
    default_timeout: int = 30
    default_max_retries: int = 3
    networks: Dict[str, NetworkConfig] = field(default_factory=dict)

    def __post_init__(self):
        if not self.networks:
            self._setup_default_networks()

    def _setup_default_networks(self):
        self.networks["solana"] = NetworkConfig(
            rpc_url="https://explorer-api.mainnet-beta.solana.com/",
            timeout=self.default_timeout,
            max_retries=self.default_max_retries,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'solana-client': 'js/1.0.0-maintenance',
                'origin': 'https://explorer.solana.com',
                'referer': 'https://explorer.solana.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        )

        self.networks["ethereum"] = NetworkConfig(
            rpc_url="https://api-v3.ethvm.dev/",
            timeout=self.default_timeout,
            max_retries=self.default_max_retries,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Origin': 'https://www.ethvm.com',
                'Referer': 'https://www.ethvm.com/',
                'Accept-Language': 'ru-RU,ru;q=0.9,kk-KZ;q=0.8,kk;q=0.7,en-US;q=0.6,en;q=0.5,zh-TW;q=0.4,zh;q=0.3,uk;q=0.2',
                'Accept-Encoding': 'gzip, deflate, br, zstd'
            }
        )

        self.networks["bitcoin"] = NetworkConfig(
            rpc_url="https://api.blockchain.info/haskoin-store/btc/",
            timeout=self.default_timeout,
            max_retries=self.default_max_retries,
            headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'accept': 'application/json, text/plain, */*',
                'origin': 'https://www.blockchain.com',
                'referer': 'https://www.blockchain.com/',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ru-RU,ru;q=0.9,kk-KZ;q=0.8,kk;q=0.7,en-US;q=0.6,en;q=0.5,zh-TW;q=0.4,zh;q=0.3,uk;q=0.2',
            }
        )

        self.networks["ton"] = NetworkConfig(
            rpc_url="https://api.tonscan.com/api/bt/",
            timeout=self.default_timeout,
            max_retries=self.default_max_retries,
            headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'accept': '*/*',
                'origin': 'https://tonscan.com',
                'referer': 'https://tonscan.com/',
                'accept-language': 'ru-RU,ru;q=0.9,kk-KZ;q=0.8,kk;q=0.7,en-US;q=0.6,en;q=0.5,zh-TW;q=0.4,zh;q=0.3,uk;q=0.2',
            }
        )

        self.networks["usdt_tron"] = NetworkConfig(
            rpc_url="https://usdt.tokenview.io/api/usdt/",
            timeout=self.default_timeout,
            max_retries=self.default_max_retries,
            headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'accept': 'application/json, text/plain, */*',
                'referer': 'https://usdt.tokenview.io/',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ru-RU,ru;q=0.9,kk-KZ;q=0.8,kk;q=0.7,en-US;q=0.6,en;q=0.5,zh-TW;q=0.4,zh;q=0.3,uk;q=0.2',
            }
        )

    def get_network_config(self, network_name: str) -> NetworkConfig:
        if network_name not in self.networks:
            raise ConfigurationError(f"Network '{network_name}' is not configured")
        return self.networks[network_name]

default_config = CryptoScanConfig()
