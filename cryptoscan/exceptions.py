"""
Custom exceptions for CryptoScan
"""


class CryptoScanError(Exception):
    """Base exception for all CryptoScan errors"""
    pass


class NetworkError(CryptoScanError):
    """Network-related errors (connection, timeout, etc.)"""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class PaymentNotFoundError(CryptoScanError):
    """Raised when expected payment is not found"""
    pass


class ValidationError(CryptoScanError):
    """Raised when validation fails (address, amount, etc.)"""
    pass


class RPCError(CryptoScanError):
    """RPC call errors"""
    
    def __init__(self, message: str, code: int = None, data: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}


class ConnectionError(NetworkError):
    """WebSocket connection errors"""
    pass


class TimeoutError(NetworkError):
    """Request timeout errors"""
    pass
