# pycryptoscan

Async cryptocurrency payment detection and wallet tracking for Python.

Unlike heavy full-node SDKs (`web3.py`, `solana-py`), **CryptoScan** does exactly one thing: it watches a wallet address and fires a Python callback when money arrives. Built for payment gateways, Telegram bots, and automated billing systems.

[![PyPI version](https://img.shields.io/pypi/v/pycryptoscan.svg)](https://pypi.org/project/pycryptoscan/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Capabilities

* **Stablecoin Support**: Native parsing for ERC-20 (USDT, USDC on EVM) and SPL tokens (Solana).
* **Flexible Matching**: Trigger on exact amounts, "at least X", or track ALL incoming transfers.
* **Dual Engine**: Uses lightweight WebSocket log subscriptions where possible (EVM), falls back to optimized HTTP polling for others (Solana, TRON, Bitcoin).
* **Confirmation Control**: Set `min_confirmations` to wait for block finality before triggering callbacks.
* **Enterprise Security**: Built-in SSRF protection (blocks private IPs/metadata endpoints) and automated API key masking in logs.
* **Resilient**: Fully async (`httpx`, `asyncio`) with exponential backoff and auto-reconnects via `tenacity`.

## Installation

```bash
pip install pycryptoscan
```

For WebSocket-based real-time monitoring:

```bash
pip install pycryptoscan[realtime]
```

## Quick Start

### 1. Basic Wallet Tracker (Listen to everything)
If you just want to track a wallet and be notified of any incoming transfer:

```python
import asyncio
from cryptoscan import create_monitor, MatchMode

async def main():
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        match_mode=MatchMode.ANY
    )

    @monitor.on_payment
    async def handle_payment(event):
        info = event.payment_info
        print(f"Received: {info.amount} {info.currency} from {info.from_address}")
        print(f"TX: {info.transaction_id}")

    try:
        await monitor.start()
    except KeyboardInterrupt:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. E-commerce Gateway (USDT/USDC Support)
Wait for a specific stablecoin payment (e.g., user needs to pay *at least* 50 USDT). The library will automatically scan `Transfer` logs instead of heavy blocks.

```python
from cryptoscan import create_monitor, MatchMode, TokenConfig

usdt_config = TokenConfig(
    contract_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
    symbol="USDT",
    decimals=6
)

monitor = create_monitor(
    network="ethereum",
    wallet_address="0xYOUR_MERCHANT_ADDRESS",
    expected_amount="50.0",
    match_mode=MatchMode.AT_LEAST,
    token_contract=usdt_config,
    auto_stop=True
)

@monitor.on_payment
async def release_product(event):
    print("Payment confirmed! Releasing digital goods...")
```

### 3. Solana & SPL Tokens
CryptoScan supports Solana natively and can monitor SPL token transfers (e.g., USDC on Solana) by parsing `preTokenBalances`/`postTokenBalances`.

```python
from cryptoscan import create_monitor, MatchMode, TokenConfig

usdc_solana = TokenConfig(
    contract_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    symbol="USDC",
    decimals=6
)

monitor = create_monitor(
    network="solana",
    wallet_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    expected_amount="25.0",
    match_mode=MatchMode.AT_LEAST,
    token_contract=usdc_solana,
    auto_stop=True
)
```

### 4. Bitcoin with Polling & Confirmations
For chains without WebSocket support (or when you prefer polling), force polling mode and set confirmation thresholds.

```python
monitor = create_monitor(
    network="bitcoin",
    wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
    expected_amount="0.00611813",
    poll_interval=30.0,
    min_confirmations=3,
    realtime=False,
    auto_stop=True
)
```

## Supported Networks

The library includes pre-configurations for PublicNode endpoints, but you can inject ANY standard RPC.

| Protocol | Networks | Token Support | Method |
|----------|----------|---------------|--------|
| **EVM** | Ethereum, BSC, Polygon (+ any EVM chain via custom config) | Native + ERC-20 | WebSockets (`eth_subscribe logs`) |
| **SVM** | Solana | Native + SPL | Polling (`getSignaturesForAddress`) |
| **TRON** | TRON | Native + TRC-20 | Polling (TRON Grid REST) |
| **TON** | TON | Native | Polling (TON Center REST) |
| **Other** | Bitcoin | Native only | Polling (RPC) |

*Want to add any EVM-compatible chain? Just pass `rpc_url`/`ws_url` or a `NetworkConfig` — see below.*

## Custom Network Configuration

### Direct RPC Injection

Pass custom endpoints directly to `create_monitor()` without registering anything:

```python
monitor = create_monitor(
    network="scroll",
    wallet_address="0x...",
    expected_amount="1.0",
    rpc_url="https://scroll-rpc.publicnode.com",
    ws_url="wss://scroll-rpc.publicnode.com"
)
```

You can also pass a `NetworkConfig` object directly:

```python
from cryptoscan import create_monitor, NetworkConfig

my_chain = NetworkConfig(
    name="my-chain",
    symbol="ETH",
    rpc_url="https://my-chain-rpc.example.com",
    ws_url="wss://my-chain-rpc.example.com",
    chain_type="evm",
    decimals=18,
)

monitor = create_monitor(
    network=my_chain,
    wallet_address="0x...",
    expected_amount="1.0",
)
```

### Registering a Network

Register custom networks globally so they can be referenced by name (useful for private chains or testnets):

```python
from cryptoscan import register_network, create_network_config

config = create_network_config(
    name="local-testnet",
    symbol="ETH",
    rpc_url="http://localhost:8545",
    chain_type="evm",
    decimals=18,
)

register_network(config)
monitor = create_monitor("local-testnet", "0x...", "1.0")
```

## Advanced: Proxies, Timeouts & Error Handling

### Proxy and Connection Pooling

Use `UserConfig` to control connection pooling, timeouts, proxy routing, and WebSocket behavior.

```python
from cryptoscan import create_monitor, UserConfig, ProxyConfig

proxy_settings = ProxyConfig(
    https_proxy="http://10.10.1.10:3128",
    proxy_auth="user:pass",
)

config = UserConfig(
    proxy_config=proxy_settings,
    timeout=10.0,
    max_retries=5,
    retry_delay=2.0,
    connector_limit=20,
    ssl_verify=True,
)

monitor = create_monitor(
    network="solana",
    wallet_address="...",
    expected_amount="1.5",
    user_config=config,
)
```

You can also pass `timeout` and `max_retries` directly to `create_monitor()` as shortcuts — they override the corresponding `UserConfig` fields:

```python
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    timeout=15.0,
    max_retries=5,
)
```

### Error Handling

The library provides domain-specific exceptions for fine-grained error handling. Strategies catch errors, emit `ErrorEvent`, and continue retrying — your callbacks are for logging and external integrations.

```python
from cryptoscan import (
    create_monitor, NetworkError, CSConnectionError,
    CSTimeoutError, PaymentNotFoundError, RPCError,
)

monitor = create_monitor(...)

@monitor.on_error
async def on_error(event):
    error = event.error
    if isinstance(error, NetworkError):
        print(f"Connection instability (auto-retrying): {error}")
    elif isinstance(error, RPCError):
        print(f"RPC error (code={error.code}): {error}")
    else:
        print(f"Unexpected error: {error}")
```

Full exception hierarchy:

```
CryptoScanError
├── NetworkError
│   ├── CSConnectionError
│   ├── CSTimeoutError
│   └── BlockFetchError
├── PaymentNotFoundError
├── ValidationError
├── RPCError
├── ParserError
└── AdapterError
```

## Ad-Hoc Provider Access

Use `get_provider()` for direct RPC interaction without running a full monitor (e.g., balance checks, block queries):

```python
import asyncio
from cryptoscan import get_provider

async def main():
    provider = get_provider("ethereum")
    await provider.connect()
    try:
        block = await provider.get_block_number()
        print(f"Latest block: {block}")
    finally:
        await provider.close()

asyncio.run(main())
```

## Metrics & Observability

If you are running CryptoScan in a long-lived billing microservice, you can collect per-method request metrics and export them as Prometheus text format:

```python
from cryptoscan import enable_global_metrics, get_global_metrics

enable_global_metrics()

# ... monitor runs ...

collector = get_global_metrics()
summary = collector.get_summary()
print(f"Requests: {summary.total_requests} | Failed: {summary.failed_requests}")
print(f"Avg Latency: {summary.avg_response_time_ms:.2f}ms")
print(f"Error Rate: {summary.error_rate:.1%}")

print(collector.export_prometheus())
```

## User Guides

### Adding Litecoin (LTC), Dogecoin (DOGE), or Other Bitcoin-like Coins

Since Litecoin and Dogecoin are Bitcoin forks, their nodes expose the same RPC API. No custom parser is needed — just create a `NetworkConfig` with `chain_type="bitcoin"`:

```python
import asyncio
from cryptoscan import create_network_config, register_network, create_monitor, MatchMode

doge_config = create_network_config(
    name="dogecoin",
    symbol="DOGE",
    rpc_url="https://rpc.your-doge-node.com",
    chain_type="bitcoin",
    decimals=8
)

ltc_config = create_network_config(
    name="litecoin",
    symbol="LTC",
    rpc_url="https://rpc.your-ltc-node.com",
    chain_type="bitcoin",
    decimals=8
)

register_network(doge_config)
register_network(ltc_config)

async def main():
    monitor = create_monitor(
        network="dogecoin",
        wallet_address="D7q...your_doge_address",
        expected_amount="150.0",
        match_mode=MatchMode.AT_LEAST,
        realtime=False
    )

    @monitor.on_payment
    async def on_payment(event):
        info = event.payment_info
        print(f"Received {info.amount} {info.currency}! TX: {info.transaction_id}")

    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Tracking Any ERC-20 or SPL Token (DAI, SHIB, PEPE, etc.)

The library supports **any** ERC-20 token (Ethereum, BSC, Polygon, etc.) and SPL token (Solana) via `TokenConfig`. Find the token's contract address and decimals on Etherscan or CoinMarketCap:

```python
from cryptoscan import create_monitor, MatchMode, TokenConfig

pepe_token = TokenConfig(
    contract_address="0x6982508145454Ce325dDbE47a25d4ec3d2311933",
    symbol="PEPE",
    decimals=18
)

monitor = create_monitor(
    network="ethereum",
    wallet_address="0xYOUR_WALLET_ADDRESS",
    expected_amount="1000000.0",
    match_mode=MatchMode.AT_LEAST,
    token_contract=pepe_token,
    auto_stop=True
)
```

### Adding a Custom Blockchain Parser (Monero, Ripple, etc.)

For chains that are neither Bitcoin-like nor EVM-compatible, write a custom parser and register it:

```python
from cryptoscan import ChainParser, register_parser, create_network_config

class RippleParser(ChainParser):
    async def get_transactions(self, address, limit, expected_amount=None, match_mode=None, token_contract=None):
        # Your XRP API logic here
        pass

    async def get_transaction(self, tx_id):
        # Your XRP API logic here
        pass

    async def get_block_number(self):
        return 0

    async def get_block_for_payment(self, block_identifier, wallet_address, expected_amount, latest_block_num=None, match_mode=None, token_contract=None):
        return None

register_parser("ripple", RippleParser)

xrp_net = create_network_config(
    name="ripple_mainnet",
    symbol="XRP",
    rpc_url="...",
    chain_type="ripple"
)
```

## Security

CryptoScan includes built-in protections for production deployments:

* **SSRF Protection**
* **Log Masking**
* **Response Limits**: 1MB for WebSocket messages, 10MB for HTTP responses.
* **SSL Verification**: Enabled by default; can be disabled via `UserConfig(ssl_verify=False)`.

## License

MIT License. See [LICENSE](LICENSE) for details.
