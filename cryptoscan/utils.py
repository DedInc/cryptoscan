from typing import Dict, Optional, List
from .core.base import NetworkConfig, ProxyConfig, UserConfig





def create_user_config(
    proxy_url: Optional[str] = None,
    proxy_auth: Optional[str] = None,
    proxy_headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    ssl_verify: bool = True,
    ssl_cert_path: Optional[str] = None,
    ssl_key_path: Optional[str] = None,
    connector_limit: int = 100,
    connector_limit_per_host: int = 30,
    cookie_jar: Optional[str] = None,
    trust_env: bool = True
) -> UserConfig:
    """
    Create a UserConfig with user-configurable settings.

    This is the recommended way to configure proxy, timeouts, and other user settings
    while preserving provider-specific network configurations.

    Args:
        proxy_url: HTTPS proxy URL
        proxy_auth: Proxy authentication string (username:password)
        proxy_headers: Additional headers for proxy requests
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        retry_delay: Delay between retries in seconds
        ssl_verify: Whether to verify SSL certificates
        ssl_cert_path: Path to SSL certificate file
        ssl_key_path: Path to SSL key file
        connector_limit: Maximum number of connections in pool
        connector_limit_per_host: Maximum connections per host
        cookie_jar: Path to cookie jar file
        trust_env: Whether to trust environment variables for proxy

    Returns:
        UserConfig instance
    """
    proxy_config = None
    if proxy_url:
        proxy_config = ProxyConfig(
            https_proxy=proxy_url,
            http_proxy=proxy_url,
            proxy_auth=proxy_auth,
            proxy_headers=proxy_headers
        )

    return UserConfig(
        proxy_config=proxy_config,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        ssl_verify=ssl_verify,
        ssl_cert_path=ssl_cert_path,
        ssl_key_path=ssl_key_path,
        connector_limit=connector_limit,
        connector_limit_per_host=connector_limit_per_host,
        cookie_jar=cookie_jar,
        trust_env=trust_env
    )





def load_proxy_list(file_path: str) -> List[ProxyConfig]:
    proxies = []

    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '@' in line:
                    protocol, rest = line.split('://', 1)
                    auth_part, host_part = rest.split('@', 1)
                    proxy_url = f"{protocol}://{host_part}"
                    proxy_auth = auth_part
                else:
                    proxy_url = line
                    proxy_auth = None

                proxy_config = ProxyConfig(
                    https_proxy=proxy_url,
                    http_proxy=proxy_url,
                    proxy_auth=proxy_auth
                )
                proxies.append(proxy_config)

    except FileNotFoundError:
        raise FileNotFoundError(f"Proxy list file not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error parsing proxy list: {e}")

    return proxies


def test_proxy_config(proxy_config: ProxyConfig,
                     test_url: str = "https://httpbin.org/ip",
                     timeout: int = 10) -> bool:
    import asyncio

    async def _test():
        network_config = NetworkConfig(
            rpc_url=test_url,
            proxy_config=proxy_config,
            timeout=timeout,
            max_retries=1
        )

        from .providers.solana import SolanaProvider
        provider = SolanaProvider(network_config)

        try:
            response = await provider._make_request("GET", test_url)
            return response.status_code == 200
        except:
            return False
        finally:
            await provider.close()

    try:
        return asyncio.run(_test())
    except:
        return False

