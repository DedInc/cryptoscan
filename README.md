# CryptoScan 🚀

**Professional Async Crypto Payment Monitoring Library for Python**

CryptoScan is a fast, reliable, and extensible Python library for monitoring cryptocurrency payments across multiple blockchain networks. Built with async/await support, HTTP/2 integration, and enterprise-grade reliability.

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Async](https://img.shields.io/badge/async-supported-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![HTTP/2](https://img.shields.io/badge/HTTP%2F2-enabled-brightgreen.svg)](https://httpwg.org/specs/rfc7540.html)

</div>

## ✨ Features

- 🌐 **Multi-Network Support**: Bitcoin, Ethereum, Solana, TON, USDT Tron (TRC-20)
- ⚡ **Async/Await**: Built for high-performance async applications
- 🚀 **HTTP/2 Ready**: Optimized API calls with HTTP/2 support
- 🔒 **Proxy Support**: Full proxy configuration for all providers
- 🎯 **Exact Matching**: Precise payment amount detection
- 🔄 **Auto-Stop**: Automatic monitoring termination after payment detection
- 📊 **Real-time Events**: Payment callbacks and event handling
- 🛡️ **Enterprise Ready**: Robust error handling and retry mechanisms

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
    monitor = create_monitor(
        network="bitcoin",
        wallet_address="3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG",
        expected_amount="0.00611813",
        auto_stop=True
    )

    # Set up payment handler
    @monitor.on_payment
    async def handle_payment(event):
        payment = event.payment_info
        print(f"💰 Payment received: {payment.amount} {payment.currency}")
        print(f"📝 Transaction: {payment.transaction_id}")
        print(f"👤 From: {payment.from_address}")

    # Start monitoring
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🌐 Supported Networks

| Network | Symbol | Factory Names | Status |
|---------|--------|---------------|--------|
| **Bitcoin** | BTC | `bitcoin`, `btc` | ✅ Ready |
| **Ethereum** | ETH | `ethereum`, `eth` | ✅ Ready |
| **Solana** | SOL | `solana`, `sol` | ✅ Ready |
| **TON** | TON | `ton` | ✅ Ready |
| **USDT Tether (TRC-20)** | USDT | `usdt_tron`, `usdt`, `trc20` | ✅ Ready |

## 📖 Examples

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
        print(f"� Payment received: {payment.amount} {payment.currency}")
        print(f"   Transaction: {payment.transaction_id}")
        print(f"   From: {payment.from_address}")

    await monitor.start()

asyncio.run(bitcoin_example())
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
        print(f"� {payment.currency} payment: {payment.amount}")

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
    connector_limit=50
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
        "Supported networks: bitcoin, ethereum, solana, usdt_tron, ton"
    )

@dp.message(Command("monitor"))
async def monitor_payment(message: Message):
    # Parse command: /monitor bitcoin 3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG 0.001
    args = message.text.split()[1:]
    if len(args) != 3:
        await message.answer(
            "❌ Invalid format!\n"
            "Usage: /monitor <network> <address> <amount>\n\n"
            "Example: /monitor bitcoin 3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG 0.001"
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

Creates a payment monitor for any supported network.

```python
def create_monitor(
    network: str,                    # Network name: "bitcoin", "ethereum", etc.
    wallet_address: str,             # Wallet address to monitor
    expected_amount: str | Decimal,  # Expected payment amount (exact match)
    poll_interval: float = 15.0,     # Seconds between checks
    max_transactions: int = 10,      # Max transactions to check per poll
    auto_stop: bool = False,         # Stop after finding payment
    rpc_url: str = None,            # Custom RPC URL
    **kwargs                        # Additional configuration
) -> PaymentMonitor
```

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

### Network Providers

Direct access to network providers for advanced use cases.

```python
from cryptoscan import BitcoinProvider, EthereumProvider, SolanaProvider

# Create provider directly
provider = BitcoinProvider()

# Validate address
is_valid = await provider.validate_wallet_address("3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG")

# Get recent transactions
transactions = await provider.get_recent_transactions("3DVSCqZdrNJHyu9Le7Sepdh1KgQTNR8reG", limit=10)

# Get specific transaction
tx_details = await provider.get_transaction_details("0fc6173f52a52d1c4701264db0dccb3dbe413a0716a3cd2805fed79990573ea3")
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Override default RPC URLs
export CRYPTOSCAN_BITCOIN_RPC_URL="https://your-bitcoin-node.com"
export CRYPTOSCAN_ETHEREUM_RPC_URL="https://your-ethereum-node.com"
export CRYPTOSCAN_SOLANA_RPC_URL="https://your-solana-node.com"

# Optional: Set default polling interval
export CRYPTOSCAN_POLL_INTERVAL="30.0"
```

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

## 🚀 Performance Tips

1. **Use HTTP/2**: All providers support HTTP/2 for better performance
2. **Optimize Poll Intervals**: Balance between responsiveness and API rate limits
3. **Proxy Rotation**: Use proxy rotation for high-volume applications
4. **Connection Pooling**: Providers automatically manage connection pools
5. **Async Best Practices**: Use `asyncio.gather()` for concurrent monitoring


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the crypto community**

*CryptoScan - Making crypto payment monitoring simple, fast, and reliable.*
```