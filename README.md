# pycryptoscan

An async Python library for monitoring cryptocurrency transactions across multiple blockchains. It supports both WebSocket subscriptions (for real-time events) and HTTP polling with automatic fallback.

Designed for payment gateways and monitoring services that need to track incoming transactions on EVM (Ethereum, BSC, Polygon), SVM (Solana), and Cosmos-based networks.

[![PyPI version](https://img.shields.io/pypi/v/pycryptoscan.svg)](https://pypi.org/project/pycryptoscan/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Capabilities

*   **Hybrid Monitoring**: Prioritizes WebSocket connections for supported chains; falls back to HTTP polling if WS is unavailable or unstable.
*   **Async/Await**: Built on `asyncio`, using `aiohttp` for requests.
*   **Resilience**: Implements exponential backoff for reconnections and retries via `tenacity`.
*   **HTTP/2**: Uses HTTP/2 where supported to reduce latency.
*   **Type Safety**: Fully typed for better IDE support.
*   **Network Support**: Pre-configured defaults for major chains, but allows injection of custom RPC/WS endpoints.

## Installation

```bash
pip install pycryptoscan
```

## Usage

### Basic Monitor

The library exposes a `create_monitor` factory function. By default, it attempts to identify the network settings and connection type.

```python
import asyncio
from cryptoscan import create_monitor

async def main():
    # Monitors an ETH address. 
    # Since Ethereum supports WebSockets, this will open a WS connection.
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        expected_amount="1.0",
        auto_stop=True  # Stop the loop after finding the transaction
    )

    @monitor.on_payment
    async def handle_payment(event):
        payment = event.payment_info
        print(f"Payment detected: {payment.amount} {payment.currency}")
        print(f"Tx Hash: {payment.transaction_id}")
        print(f"Block: {payment.block_height}")

    try:
        await monitor.start()
    except KeyboardInterrupt:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Polling and Confirmations

For networks without stable WebSocket endpoints (or if you prefer polling), you can force polling mode and set confirmation thresholds.

```python
monitor = create_monitor(
    network="bitcoin",
    wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
    expected_amount="0.00611813",
    poll_interval=30.0,    # Check every 30 seconds
    min_confirmations=3,   # Wait for 3 confirmations before triggering callback
    realtime=False         # Force polling mode
)
```

### Custom RPC Configuration

You are not limited to the built-in network defaults. You can register custom networks or pass RPC endpoints directly.

**Direct Injection:**

```python
monitor = create_monitor(
    network="scroll",
    wallet_address="0x...",
    expected_amount="1.0",
    rpc_url="https://scroll-rpc.publicnode.com",
    ws_url="wss://scroll-rpc.publicnode.com" # Optional, enables WS mode
)
```

**Registering a Network:**

```python
from cryptoscan import register_network, create_network_config

# useful for private chains or testnets
config = create_network_config(
    name="local-testnet",
    symbol="ETH",
    rpc_url="http://localhost:8545",
    chain_type="evm",
    decimals=18
)

register_network(config)
monitor = create_monitor("local-testnet", "0x...", "1.0")
```

## Advanced Configuration

### Proxy and Limits

Use `UserConfig` to control connection pooling, timeouts, and proxies.

```python
from cryptoscan import create_monitor, UserConfig, ProxyConfig

proxy_settings = ProxyConfig(
    https_proxy="http://10.10.1.10:3128",
    proxy_auth="user:pass"
)

config = UserConfig(
    proxy_config=proxy_settings,
    timeout=10,
    max_retries=3,
    connector_limit=20  # Limit concurrent connections
)

monitor = create_monitor(
    network="solana",
    wallet_address="...",
    expected_amount="1.5",
    user_config=config
)
```

### Error Handling

The library provides specific exceptions for control flow.

```python
from cryptoscan import NetworkError, PaymentNotFoundError

@monitor.on_error
async def on_error(event):
    error = event.error
    if isinstance(error, NetworkError):
        # The library retries internally, but you can log external stats here
        print(f"Connection instability: {error}")
    else:
        print(f"Critical error: {error}")
```

## Supported Networks

The library includes pre-configurations for PublicNode endpoints.

| Protocol | Networks                                                                 |
|----------|--------------------------------------------------------------------------|
| **EVM**  | Ethereum, BSC, Polygon, Arbitrum, Avalanche, Base, Optimism, Linea, Scroll, Blast |
| **SVM**  | Solana                                                                   |
| **Cosmos** | Osmosis, Injective, Celestia, Sei                                      |
| **Move** | Sui, Aptos                                                               |
| **Other** | Bitcoin, TRON (USDT)                                                    |

*Note: Bitcoin and TRON implementations rely on specific public APIs and are polling-only by default.*

## Metrics

If you are running this in a long-lived service, you can enable metrics collection.

```python
from cryptoscan import enable_global_metrics, get_global_metrics

enable_global_metrics()

# ... application runs ...

stats = get_global_metrics()
print(f"Requests: {stats.total_requests} | Failed: {stats.failed_requests}")
print(f"Avg Latency: {stats.avg_response_time:.4f}s")
```

## License

MIT License. See [LICENSE](LICENSE) for details.
