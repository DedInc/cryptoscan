# CryptoScan 🚀

**Professional Real-Time Crypto Payment Monitoring Library for Python**

A fast, intelligent, production-ready Python library for monitoring cryptocurrency payments in **real-time** across multiple blockchain networks. Built with WebSocket subscriptions, automatic fallback to polling, HTTP/2 support, enterprise-grade reliability, and built-in security features.

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Async](https://img.shields.io/badge/async-supported-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![HTTP/2](https://img.shields.io/badge/HTTP%2F2-enabled-brightgreen.svg)](https://httpwg.org/specs/rfc7540.html)

</div>

## ✨ Features

### Real-Time Monitoring
- 📡 **WebSocket Subscriptions**: Instant notifications when new blocks arrive
- 🧠 **Smart Auto-Detection**: Uses WebSocket if available, falls back to polling
- ⚡ **Zero Configuration**: Create a monitor - it selects the best mode automatically
- 🔄 **Auto-Reconnect**: Graceful reconnection with exponential backoff

### Network Support
- 🌐 **Major Blockchains**: Ethereum, BSC, Polygon, Arbitrum, Avalanche, Base, Optimism, Solana, Sui, Osmosis, and more
- 🔥 **Real-Time Capable**: Major EVM chains, Solana, and Cosmos-based networks
- 🎯 **Universal Provider**: Single provider works with any blockchain type
- 📡 **PublicNode Powered**: Access to PublicNode's network infrastructure
- ✨ **Easy to Extend**: Add any network with simple configuration

### Developer Experience
- ⚡ **Async/Await**: Built for high-performance async applications
- 🚀 **HTTP/2**: Optimized API calls with HTTP/2 support
- 🔒 **Proxy Support**: Full proxy configuration (HTTPS, HTTP, auth)
- 🎯 **Exact Matching**: Precise payment amount detection with Decimal
- 📊 **Event System**: Payment and error callbacks with decorators
- 🛡️ **Production Ready**: Tenacity retry logic, comprehensive error handling

### Security & Monitoring
- 🔐 **Security Utilities**: URL validation, address masking for safe logging
- 📈 **Metrics Collection**: Optional performance monitoring and statistics
- 🚦 **Rate Limiting**: Built-in request throttling to prevent node overload
- 🔄 **Auto-Reconnect**: WebSocket subscription restoration after disconnection
- 🧵 **Thread-Safe**: Thread-safe network registry for multi-threaded applications


## 🚀 Quick Start

### Installation

```bash
pip install pycryptoscan
```

### Basic Usage

```python
import asyncio
from cryptoscan import create_monitor

async def main():
    # Create a payment monitor
    # Real-time mode is auto-detected (Ethereum has WebSocket support)
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        expected_amount="1.0",
        auto_stop=True,
        min_confirmations=3  # Wait for 3 confirmations before accepting payment
    )

    # Set up payment handler
    @monitor.on_payment
    async def handle_payment(event):
        payment = event.payment_info
        print(f"💰 Payment received: {payment.amount} {payment.currency}")
        print(f"📝 Transaction: {payment.transaction_id}")
        print(f"👤 From: {payment.from_address}")
        print(f"📦 Block: #{payment.block_height}")

    # Start monitoring (uses WebSocket automatically)
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🌐 Supported Networks

### 🔥 Popular Networks (Real-Time WebSocket)

| Network | Symbol | Usage | Network Type |
|---------|--------|-------|-------------|
| **Ethereum** | ETH | `ethereum`, `eth` | EVM (Layer 1) |
| **BSC** | BNB | `bsc`, `bnb` | EVM (Binance) |
| **Polygon** | MATIC | `polygon`, `matic` | EVM (Layer 2) |
| **Arbitrum** | ETH | `arbitrum`, `arb` | EVM (Layer 2) |
| **Avalanche** | AVAX | `avalanche`, `avax` | EVM (Layer 1) |
| **Base** | ETH | `base` | EVM (Coinbase Layer 2) |
| **Optimism** | ETH | `optimism`, `op` | EVM (Layer 2) |
| **Solana** | SOL | `solana`, `sol` | Non-EVM (High Performance) |
| **Sui** | SUI | `sui` | Move VM |
| **Osmosis** | OSMO | `osmosis` | Cosmos (DEX) |
| **Injective** | INJ | `injective`, `inj` | Cosmos (DeFi) |

### 🔵 Additional Networks (Polling Mode)

| Network | Symbol | Usage | Network Type |
|---------|--------|-------|-------------|
| **Aptos** | APT | `aptos`, `apt` | Move VM |
| **Bitcoin** | BTC | `bitcoin`, `btc` | UTXO |
| **TON** | TON | `ton` | TON VM |
| **USDT-Tron** | USDT | `usdt_tron`, `trc20` | Tron (TRC-20) |

### ✨ More Networks Available

CryptoScan leverages **PublicNode's infrastructure** with 100+ blockchain networks including:
- **Layer 2s**: Scroll, Linea, Blast, Mantle, Taiko, opBNB, Fraxtal
- **Cosmos Ecosystem**: Cosmos Hub, Terra, Kava, Neutron, Celestia, Sei, dYdX
- **Other EVMs**: Gnosis, Moonbeam, Celo, Cronos, PulseChain, Sonic
- **And many more...**

> 🔥 **Real-Time**: Instant WebSocket notifications when new blocks arrive  
> 🔵 **Polling**: HTTP checks every N seconds (fast and reliable)  
> ✨ **Easy to Add**: Configure any PublicNode network using registration functions

## 🔧 Network Registration

CryptoScan comes with **common networks pre-registered** (Ethereum, BSC, Polygon, Solana). You can add custom networks in several ways:

### 🚀 Pre-Registered Networks (Ready to Use)

These networks are automatically available:

```python
from cryptoscan import list_networks
print("Available networks:", list_networks())
# Output: ['binance', 'bnb', 'bsc', 'eth', 'ethereum', 'matic', 'polygon', 'sol', 'solana']

# Use directly by name or alias
monitor = create_monitor("ethereum", "0x...", "1.0")  # Name
monitor = create_monitor("eth", "0x...", "1.0")       # Alias
monitor = create_monitor("polygon", "0x...", "1.0")   # Name
monitor = create_monitor("matic", "0x...", "1.0")     # Alias
```

### 📝 Register Custom Networks

#### Method 1: Quick Registration
```python
from cryptoscan import register_network, create_network_config

# Register once, use everywhere
scroll_config = create_network_config(
    name="scroll",
    symbol="ETH",
    rpc_url="https://scroll-rpc.publicnode.com",
    ws_url="wss://scroll-rpc.publicnode.com",  # Optional: enables real-time
    aliases=["scrl"],
    address_pattern=r'^0x[a-fA-F0-9]{40}$',  # EVM address format
    decimals=18,
    chain_type="evm"
)

register_network(scroll_config)

# Now use anywhere in your app
monitor = create_monitor("scroll", "0x...", "1.0")  # By name
monitor = create_monitor("scrl", "0x...", "1.0")    # By alias
```

#### Method 2: Register Multiple Networks
```python
from cryptoscan import register_network, NetworkConfig

# Define multiple networks
custom_networks = [
    NetworkConfig(
        name="blast", symbol="ETH",
        rpc_url="https://blast-rpc.publicnode.com",
        ws_url="wss://blast-rpc.publicnode.com",
        aliases=["blst"], chain_type="evm", decimals=18
    ),
    NetworkConfig(
        name="linea", symbol="ETH",
        rpc_url="https://linea-rpc.publicnode.com",
        ws_url="wss://linea-rpc.publicnode.com",
        chain_type="evm", decimals=18
    )
]

# Register all at once
for network in custom_networks:
    register_network(network)

# Use them
monitor = create_monitor("blast", "0x...", "1.0")
monitor = create_monitor("linea", "0x...", "1.0")
```

### ⚡ Alternative: Direct Usage Without Registration

Skip registration by providing `rpc_url` directly:

```python
# No registration needed - works immediately
monitor = create_monitor(
    network="any-name",  # Can be anything
    wallet_address="0x...",
    expected_amount="1.0",
    rpc_url="https://your-rpc-endpoint.com",
    ws_url="wss://your-ws-endpoint.com"  # Optional
)
```

**💡 Pro Tips:**
- Registration is optional - use `rpc_url` parameter to skip it
- Pre-registered networks are available immediately after `import cryptoscan`
- Use `list_networks()` to see all available networks
- Aliases let you use short names (e.g., "eth" instead of "ethereum")
- Find RPC endpoints at [PublicNode.com](https://publicnode.com)

### 🌐 Real-World Examples

<details>
<summary>🔥 Scroll (EVM Layer 2)</summary>

```python
monitor = create_monitor(
    network="scroll",
    wallet_address="0xYourAddress",
    expected_amount="1.0",
    rpc_url="https://scroll-rpc.publicnode.com",
    ws_url="wss://scroll-rpc.publicnode.com"
)
```
</details>

<details>
<summary>🌟 Celestia (Cosmos)</summary>

```python
monitor = create_monitor(
    network="celestia",
    wallet_address="celestia1...",  # Cosmos address format
    expected_amount="1.0",
    rpc_url="https://celestia-rpc.publicnode.com",
    ws_url="wss://celestia-rpc.publicnode.com"
)
```
</details>

<details>
<summary>🌊 Sei (Parallel Execution)</summary>

```python
monitor = create_monitor(
    network="sei",
    wallet_address="sei1...",
    expected_amount="1.0",
    rpc_url="https://sei-rpc.publicnode.com",
    ws_url="wss://sei-rpc.publicnode.com"
)
```
</details>

## 📚 Examples

### Real-Time Monitoring (Auto-Detected)

```python
import asyncio
from cryptoscan import create_monitor

async def realtime_example():
    # WebSocket real-time monitoring (auto-detected)
    monitor = create_monitor(
        network="polygon",  # Has wss:// - uses real-time
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        expected_amount="10.0",
        auto_stop=True
    )
    
    @monitor.on_payment
    async def on_payment(event):
        print(f"⚡ Instant notification from new block")
        print(f"💰 {event.payment_info.amount} MATIC received")
        print(f"📦 Block #{event.payment_info.block_height}")
    
    await monitor.start()

asyncio.run(realtime_example())
```

### Multi-Chain Real-Time Monitoring

```python
import asyncio
from cryptoscan import create_monitor

async def multi_chain():
    # Monitor multiple chains simultaneously
    monitors = [
        create_monitor("ethereum", "0x...", "1.0", monitor_id="eth"),
        create_monitor("bsc", "0x...", "0.5", monitor_id="bsc"),
        create_monitor("polygon", "0x...", "10.0", monitor_id="matic"),
    ]
    
    # Unified handler
    async def on_payment(event):
        print(f"💰 Payment on {event.monitor_id}: {event.payment_info.amount}")
    
    for m in monitors:
        m.on_payment(on_payment)
    
    await asyncio.gather(*[m.start() for m in monitors])

asyncio.run(multi_chain())
```

### Basic Payment Monitoring

```python
import asyncio
from decimal import Decimal
from cryptoscan import create_monitor

async def bitcoin_example():
    monitor = create_monitor(
        network="bitcoin",  # or "btc"
        wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
        expected_amount=Decimal("0.00611813"),
        poll_interval=30.0,
        auto_stop=True
    )

    @monitor.on_payment
    async def on_payment(event):
        payment = event.payment_info
        print(f"💰 Payment received: {payment.amount} {payment.currency}")
        print(f"   Transaction: {payment.transaction_id}")
        print(f"   From: {payment.from_address}")

    await monitor.start()

asyncio.run(bitcoin_example())
```

### Payment with Confirmation Requirements

```python
import asyncio
from cryptoscan import create_monitor

async def confirmation_example():
    # Monitor payment and wait for 6 confirmations for security
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        expected_amount="100.0",
        min_confirmations=6,  # Require 6 confirmations
        auto_stop=True
    )

    @monitor.on_payment
    async def on_payment(event):
        payment = event.payment_info
        print(f"✅ Payment confirmed with {payment.confirmations} confirmations")
        print(f"💰 Amount: {payment.amount} {payment.currency}")
        print(f"🔒 Secure payment received!")

    await monitor.start()

asyncio.run(confirmation_example())
```

### Multi-Network Monitoring

```python
import asyncio
from cryptoscan import create_monitor

async def multi_network_example():
    # Monitor multiple networks simultaneously
    btc_monitor = create_monitor(
        network="bitcoin",
        wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
        expected_amount="0.00611813"
    )

    usdt_monitor = create_monitor(
        network="usdt_tron",
        wallet_address="TVRzaRqX9soeRpcJVT6zCAZjGtLtQXacCR",
        expected_amount="200.0"
    )

    # Unified payment handler
    async def handle_payment(event):
        payment = event.payment_info
        print(f"💰 {payment.currency} payment: {payment.amount}")

    btc_monitor.on_payment(handle_payment)
    usdt_monitor.on_payment(handle_payment)

    # Start all monitors
    await asyncio.gather(
        btc_monitor.start(),
        usdt_monitor.start()
    )

asyncio.run(multi_network_example())
```

## 🔧 Advanced Configuration

### Smart Real-Time Detection

```python
from cryptoscan import create_monitor

# Auto-detects real-time (default behavior)
monitor = create_monitor(
    network="ethereum",  # Has wss:// - uses real-time
    wallet_address="0x...",
    expected_amount="1.0"
)  # Real-time mode enabled

# Custom WebSocket endpoint
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    rpc_url="wss://eth.llamarpc.com"  # Detects wss:// - enables real-time
)

# Force polling mode (if needed)
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    realtime=False  # Explicitly use polling
)
```

### User Configuration (Recommended)

```python
from cryptoscan import create_monitor, create_user_config, ProxyConfig

# Create user configuration with proxy and custom settings
user_config = create_user_config(
    proxy_url="https://proxy.example.com:8080",
    proxy_auth="username:password",
    timeout=60,
    max_retries=5,
    ssl_verify=True
)

monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    user_config=user_config
)
```

### Direct UserConfig Creation

```python
from cryptoscan import create_monitor, UserConfig, ProxyConfig

# Create proxy configuration
proxy_config = ProxyConfig(
    https_proxy="https://proxy.example.com:8080",
    proxy_auth="username:password",
    proxy_headers={"Custom-Header": "value"}
)

# Create user configuration
user_config = UserConfig(
    proxy_config=proxy_config,
    timeout=60,
    max_retries=5,
    retry_delay=2.0,
    ssl_verify=True,
    connector_limit=50,
    # WebSocket configuration
    ws_ping_interval=20.0,
    ws_ping_timeout=10.0,
    ws_max_reconnect_attempts=5,
    ws_reconnect_delay=2.0,
    # Block scanning configuration
    max_blocks_to_scan=100,
    blocks_per_tx_multiplier=5
)

monitor = create_monitor(
    network="solana",
    wallet_address="39eda9Jzabcr1HPkmjt7sZPCznZqngkfXZn1utwE8uwk",
    expected_amount="0.000542353",
    user_config=user_config
)
```



### Multiple Payment Monitoring

```python
import asyncio
from cryptoscan import create_monitor

async def multi_network_monitoring():
    # Monitor multiple networks simultaneously
    monitors = []

    # Bitcoin monitor
    btc_monitor = create_monitor(
        network="bitcoin",
        wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
        expected_amount="0.001",
        monitor_id="btc-payment-1"
    )

    # Ethereum monitor
    eth_monitor = create_monitor(
        network="ethereum",
        wallet_address="0xD45F36545b373585a2213427C12AD9af2bEFCE18",
        expected_amount="0.15",
        monitor_id="eth-payment-1"
    )

    # Unified payment handler
    async def handle_any_payment(event):
        payment = event.payment_info
        monitor_id = event.monitor_id
        print(f"💰 Payment on {monitor_id}: {payment.amount} {payment.currency}")

    btc_monitor.on_payment(handle_any_payment)
    eth_monitor.on_payment(handle_any_payment)

    # Start all monitors
    await asyncio.gather(
        btc_monitor.start(),
        eth_monitor.start()
    )

asyncio.run(multi_network_monitoring())
```

## 🛡️ Error Handling & Reliability

### Robust Error Handling

```python
import asyncio
from cryptoscan import create_monitor, NetworkError, PaymentNotFoundError

async def reliable_monitoring():
    monitor = create_monitor(
        network="bitcoin",
        wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
        expected_amount="0.001",
        max_transactions=20,  # Check more transactions
        poll_interval=30.0
    )

    @monitor.on_payment
    async def on_payment(event):
        print(f"✅ Payment confirmed: {event.payment_info.amount} BTC")

    @monitor.on_error
    async def on_error(event):
        error = event.error
        if isinstance(error, NetworkError):
            print(f"🌐 Network error: {error.message}")
            print("🔄 Will retry automatically...")
        else:
            print(f"❌ Unexpected error: {error}")

    try:
        await monitor.start()
    except Exception as e:
        print(f"💥 Monitor failed: {e}")
    finally:
        await monitor.stop()

asyncio.run(reliable_monitoring())
```

### Timeout and Retry Configuration

```python
from cryptoscan import create_monitor

# High-reliability configuration
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    poll_interval=15.0,
    timeout=60,  # 60 second timeout
    max_retries=5,  # Retry failed requests 5 times
    auto_stop=True
)
```

## 🔐 Security & Monitoring Features

### Quick Reference

| Feature | Import | Purpose |
|---------|--------|---------|
| **URL Validation** | `validate_rpc_url`, `validate_ws_url` | Verify endpoint safety |
| **Data Masking** | `mask_address`, `mask_transaction_id` | Protect sensitive data in logs |
| **Metrics** | `enable_global_metrics`, `get_global_metrics` | Performance monitoring |
| **Constants** | `MAX_BLOCKS_TO_SCAN`, `DEFAULT_HTTP_TIMEOUT` | Configuration values |
| **Exceptions** | `ParserError`, `BlockFetchError`, `AdapterError` | Specific error types |

### Security Utilities

CryptoScan includes built-in security utilities for safe URL validation and data masking:

```python
from cryptoscan import (
    validate_rpc_url,
    validate_ws_url,
    mask_address,
    mask_transaction_id
)

# Validate RPC URLs before use
if validate_rpc_url("https://ethereum-rpc.publicnode.com"):
    print("✅ Valid RPC URL")

if validate_ws_url("wss://ethereum-rpc.publicnode.com"):
    print("✅ Valid WebSocket URL")

# Mask sensitive data for logging
address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"
masked = mask_address(address)
print(f"Address: {masked}")  # Output: 0x742d35...f8fE23

tx_id = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
masked_tx = mask_transaction_id(tx_id)
print(f"TX: {masked_tx}")  # Output: 0x1234567890abcd...
```

### Metrics Collection

Monitor performance and collect statistics for debugging and optimization:

```python
from cryptoscan import (
    create_monitor,
    enable_global_metrics,
    get_global_metrics,
    MetricsCollector
)
import asyncio

async def metrics_example():
    # Enable global metrics collection
    enable_global_metrics()
    
    # Create monitor as usual
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0x...",
        expected_amount="1.0",
        auto_stop=True
    )
    
    @monitor.on_payment
    async def on_payment(event):
        # Get metrics summary
        metrics = get_global_metrics()
        if metrics:
            print(f"📊 Total Requests: {metrics.total_requests}")
            print(f"⏱️  Avg Response Time: {metrics.avg_response_time:.2f}s")
            print(f"✅ Success Rate: {metrics.success_rate:.1%}")
            print(f"❌ Failed Requests: {metrics.failed_requests}")
    
    await monitor.start()

asyncio.run(metrics_example())
```

### Advanced Configuration Constants

Access and customize internal configuration constants:

```python
from cryptoscan import (
    MAX_BLOCKS_TO_SCAN,
    BLOCKS_PER_TX_MULTIPLIER,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    UserConfig
)

# Use default constants
print(f"Max blocks to scan: {MAX_BLOCKS_TO_SCAN}")
print(f"Default timeout: {DEFAULT_HTTP_TIMEOUT}s")
print(f"Default retries: {DEFAULT_MAX_RETRIES}")

# Override in UserConfig
custom_config = UserConfig(
    timeout=DEFAULT_HTTP_TIMEOUT * 2,  # Double the default
    max_retries=DEFAULT_MAX_RETRIES + 2,  # Add 2 more retries
    max_blocks_to_scan=MAX_BLOCKS_TO_SCAN * 2  # Scan more blocks
)
```

### Enhanced Error Handling

New specific exception types for better error handling:

```python
from cryptoscan import (
    create_monitor,
    ParserError,
    BlockFetchError,
    AdapterError,
    RPCError,
    NetworkError
)

async def advanced_error_handling():
    monitor = create_monitor(
        network="ethereum",
        wallet_address="0x...",
        expected_amount="1.0"
    )
    
    @monitor.on_error
    async def on_error(event):
        error = event.error
        
        if isinstance(error, ParserError):
            print(f"❌ Transaction parsing failed: {error.message}")
            print(f"   TX ID: {error.transaction_id}")
        
        elif isinstance(error, BlockFetchError):
            print(f"❌ Block retrieval failed: {error.message}")
            print(f"   Block: #{error.block_number}")
        
        elif isinstance(error, AdapterError):
            print(f"❌ API adapter error: {error.message}")
            print(f"   Adapter: {error.adapter_name}")
        
        elif isinstance(error, RPCError):
            print(f"❌ RPC error: {error.message}")
            print(f"   Code: {error.code}")
        
        elif isinstance(error, NetworkError):
            print(f"❌ Network error: {error.message}")
    
    await monitor.start()
```

### Rate Limiting

CryptoScan includes built-in rate limiting to prevent overwhelming RPC nodes:

```python
# Rate limiting is automatically enabled by default
# Default: 10 concurrent requests per RPC client

# The library manages this internally when you use create_monitor()
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0"
)
# Rate limiting is handled automatically ✅

# For advanced use cases with custom UserConfig:
from cryptoscan import UserConfig

user_config = UserConfig(
    timeout=30.0,        # Request timeout
    max_retries=3,       # Retry failed requests
    connector_limit=100  # HTTP connection pool size
)
```

**Note:** Rate limiting is managed internally and works automatically. The default of 10 concurrent requests provides a good balance between performance and node protection.

## 🔌 Integration Examples

### Aiogram v3.x (Telegram Bot) Integration

```python
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from cryptoscan import create_monitor
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token="YOUR_BOT_TOKEN")
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🚀 CryptoScan Bot\n\n"
        "Monitor crypto payments with ease!\n"
        "Usage: /monitor <network> <address> <amount>\n\n"
        "Pre-registered: ethereum, bsc, polygon, solana\n"
        "Or use any network with custom RPC URL"
    )

@dp.message(Command("monitor"))
async def monitor_payment(message: Message):
    # Parse command: /monitor ethereum 0x... 1.0
    args = message.text.split()[1:]
    if len(args) != 3:
        await message.answer(
            "❌ Invalid format!\n"
            "Usage: /monitor <network> <address> <amount>\n\n"
            "Example: /monitor ethereum 0xD45F36545b373585a2213427C12AD9af2bEFCE18 1.0"
        )
        return

    network, address, amount = args

    try:
        monitor = create_monitor(
            network=network,
            wallet_address=address,
            expected_amount=amount,
            auto_stop=True
        )

        @monitor.on_payment
        async def on_payment(event):
            payment = event.payment_info
            await message.answer(
                f"✅ Payment Received!\n\n"
                f"💰 Amount: {payment.amount} {payment.currency}\n"
                f"🔗 Transaction: {payment.transaction_id[:16]}...\n"
                f"👤 From: {payment.from_address[:16]}...\n"
                f"⏰ Time: {payment.timestamp}"
            )

        @monitor.on_error
        async def on_error(event):
            await message.answer(f"❌ Monitoring error: {event.error}")

        await message.answer(
            f"🔍 Monitoring started!\n\n"
            f"Network: {network.upper()}\n"
            f"Amount: {amount}\n"
            f"Address: {address[:16]}...\n\n"
            f"I'll notify you when payment is received!"
        )

        # Start monitoring in background
        asyncio.create_task(monitor.start())

    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

async def main():
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 API Reference

### Core Functions

#### `create_monitor()`

Creates a payment monitor for any supported network with smart real-time detection.

```python
def create_monitor(
    network: str,                    # Network name: "ethereum", "polygon", "solana", etc.
    wallet_address: str,             # Wallet address to monitor
    expected_amount: str | Decimal,  # Expected payment amount (exact match)
    poll_interval: float = 15.0,     # Seconds between checks (polling mode)
    max_transactions: int = 10,      # Max transactions to check per poll
    auto_stop: bool = False,         # Stop after finding payment
    rpc_url: str = None,             # Custom RPC URL (can be wss://)
    ws_url: str = None,              # Custom WebSocket URL (for real-time mode)
    realtime: bool = None,           # None=auto-detect, True=force, False=polling
    min_confirmations: int = 1,      # Minimum confirmations required (default: 1)
    user_config: UserConfig = None,  # User configuration (proxy, timeout, etc.)
    monitor_id: str = None,          # Custom monitor identifier
    timeout: float = None,           # Override default timeout
    max_retries: int = None,         # Override default max retries
    **kwargs                         # Additional configuration
) -> PaymentMonitor
```

**Real-Time Detection Logic:**
- `realtime=None` (default): Auto-detects based on network WebSocket availability
- `rpc_url` starts with `wss://`: Uses real-time mode
- Network has WebSocket configured: Uses real-time mode
- Otherwise: Uses polling mode
- Force mode with `realtime=True` or `realtime=False`

**Confirmation Handling:**
- `min_confirmations=1` (default): Accepts payment after 1 confirmation
- Set higher values for critical payments (e.g., `min_confirmations=3` or `6`)
- Monitor will only trigger payment callback once confirmations meet the threshold

### PaymentMonitor Class

#### Methods

- `async start()` - Start monitoring for payments
- `async stop()` - Stop monitoring
- `on_payment(callback)` - Register payment event handler
- `on_error(callback)` - Register error event handler

#### Properties

- `provider` - Access to the underlying network provider
- `is_running` - Check if monitor is currently running
- `monitor_id` - Unique identifier for this monitor

### PaymentInfo Class

Payment information returned when a payment is detected.

```python
@dataclass
class PaymentInfo:
    transaction_id: str      # Transaction hash/ID
    wallet_address: str      # Receiving wallet address
    amount: Decimal         # Payment amount in main units
    currency: str           # Currency symbol (BTC, ETH, etc.)
    status: PaymentStatus   # PENDING, CONFIRMED, FAILED
    timestamp: datetime     # Transaction timestamp
    block_height: int       # Block number (if available)
    confirmations: int      # Number of confirmations
    fee: Decimal           # Transaction fee (if available)
    from_address: str      # Sender address
    to_address: str        # Receiver address
    raw_data: dict         # Raw API response data
```

### UniversalProvider

Direct access to the universal provider for advanced use cases.

```python
from cryptoscan import UniversalProvider, NetworkConfig, UserConfig

# Create provider for any network
network_config = NetworkConfig(
    name="ethereum",
    symbol="ETH",
    rpc_url="https://ethereum-rpc.publicnode.com",
    ws_url="wss://ethereum-rpc.publicnode.com",
    chain_type="evm",
    decimals=18
)

# Optional: Configure rate limiting and other settings
user_config = UserConfig(
    timeout=60,
    max_retries=5,
    connector_limit=100  # Max concurrent connections
)

provider = UniversalProvider(
    network=network_config,
    user_config=user_config
)
await provider.connect()

# Get recent transactions
transactions = await provider.get_recent_transactions(
    "0xD45F36545b373585a2213427C12AD9af2bEFCE18",
    limit=10
)

await provider.close()
```

### Security Functions

Functions for validating URLs and masking sensitive data.

```python
from cryptoscan import (
    validate_rpc_url,
    validate_ws_url,
    mask_address,
    mask_transaction_id
)

# Validate URLs
validate_rpc_url(url: str) -> bool
validate_ws_url(url: str) -> bool

# Mask sensitive data
mask_address(address: str, prefix_length: int = 8, suffix_length: int = 6) -> str
mask_transaction_id(tx_id: str, visible_length: int = 16) -> str
```

### Metrics Functions

Functions for collecting and retrieving performance metrics.

```python
from cryptoscan import (
    MetricsCollector,
    RequestMetric,
    MetricsSummary,
    enable_global_metrics,
    disable_global_metrics,
    get_global_metrics
)

# Enable/disable global metrics
enable_global_metrics() -> None
disable_global_metrics() -> None

# Get metrics summary
get_global_metrics() -> MetricsSummary | None

# MetricsSummary attributes
@dataclass
class MetricsSummary:
    total_requests: int          # Total number of requests
    successful_requests: int     # Number of successful requests
    failed_requests: int         # Number of failed requests
    avg_response_time: float     # Average response time in seconds
    min_response_time: float     # Minimum response time
    max_response_time: float     # Maximum response time
    success_rate: float          # Success rate (0.0 to 1.0)
```

### Configuration Constants

Exported configuration constants for customization.

```python
from cryptoscan import (
    MAX_BLOCKS_TO_SCAN,           # Default: 100
    BLOCKS_PER_TX_MULTIPLIER,     # Default: 5
    DEFAULT_HTTP_TIMEOUT,         # Default: 30.0 seconds
    DEFAULT_MAX_RETRIES,          # Default: 3
    DEFAULT_WS_PING_INTERVAL,     # Default: 20.0 seconds
    DEFAULT_WS_PING_TIMEOUT,      # Default: 10.0 seconds
)
```

### Exception Classes

Specific exception types for granular error handling.

```python
from cryptoscan import (
    CryptoScanError,        # Base exception
    ValidationError,        # Invalid input/configuration
    NetworkError,           # Network-related errors
    ConnectionError,        # Connection failures
    TimeoutError,           # Request timeouts
    PaymentNotFoundError,   # Payment not found
    ParserError,            # Transaction parsing errors
    BlockFetchError,        # Block retrieval errors
    AdapterError,           # API adapter errors
    RPCError,               # RPC-specific errors
)

# ParserError attributes
class ParserError(CryptoScanError):
    message: str
    transaction_id: str | None
    original_error: Exception | None

# BlockFetchError attributes
class BlockFetchError(NetworkError):
    message: str
    block_number: int | None
    original_error: Exception | None

# AdapterError attributes
class AdapterError(CryptoScanError):
    message: str
    adapter_name: str | None
    original_error: Exception | None

# RPCError attributes
class RPCError(NetworkError):
    message: str
    code: int | None
    data: Any | None
```

## 🔧 Configuration

### Proxy Configuration

```python
from cryptoscan import create_monitor, create_user_config

# Simple proxy configuration
monitor = create_monitor(
    network="ethereum",
    wallet_address="0x...",
    expected_amount="1.0",
    user_config=create_user_config(
        proxy_url="https://proxy.example.com:8080",
        proxy_auth="username:password",
        timeout=60,
        max_retries=5
    )
)

# Advanced proxy configuration
from cryptoscan import UserConfig, ProxyConfig

proxy_config = ProxyConfig(
    https_proxy="https://proxy.example.com:8080",
    http_proxy="http://proxy.example.com:8080",
    proxy_auth="username:password",
    proxy_headers={"Custom-Header": "value"}
)

user_config = UserConfig(
    proxy_config=proxy_config,
    timeout=60,
    max_retries=5
)

monitor = create_monitor(
    network="solana",
    wallet_address="39eda9Jzabcr1HPkmjt7sZPCznZqngkfXZn1utwE8uwk",
    expected_amount="0.1",
    user_config=user_config
)
```

## 🚀 Performance

### Real-Time vs Polling

| Feature | Real-Time (WebSocket) | Polling (HTTP) |
|---------|----------------------|----------------|
| **Latency** | <1s (instant) | 15-30s (poll interval) |
| **Efficiency** | Push-based | Pull-based |
| **Load** | Single connection | Multiple requests |
| **Networks** | When ws_url provided | All networks |
| **Auto-Detect** | ✅ Yes | ✅ Yes |

### Performance Tips

1. **Real-Time First**: Use networks with WebSocket for instant notifications
2. **HTTP/2**: All HTTP calls use HTTP/2 for better performance
3. **Connection Pooling**: Automatic connection reuse reduces overhead
4. **Tenacity Retry**: Intelligent exponential backoff for high reliability
5. **Async Concurrent**: Use `asyncio.gather()` for multi-chain monitoring
6. **Optimize Polling**: Balance poll interval with responsiveness needs
7. **Rate Limiting**: Built-in request throttling prevents node overload (default: 10 concurrent)
8. **Auto-Reconnect**: WebSocket subscriptions automatically restored after disconnection
9. **Thread-Safe**: Network registry is thread-safe for multi-threaded applications
10. **Metrics Monitoring**: Enable metrics to identify performance bottlenecks


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the crypto community**