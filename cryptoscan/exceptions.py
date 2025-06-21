"""
CryptoScan Exception Classes

Custom exception hierarchy for the CryptoScan library providing
specific error types for different failure scenarios.
"""

from typing import Optional


class CryptoScanError(Exception):
    """Base exception class for all CryptoScan errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class NetworkError(CryptoScanError):
    """Raised when network communication fails."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_text: Optional[str] = None):
        details = {}
        if status_code is not None:
            details["status_code"] = status_code
        if response_text is not None:
            details["response_text"] = response_text
        super().__init__(message, details)
        self.status_code = status_code
        self.response_text = response_text


class PaymentNotFoundError(CryptoScanError):
    """Raised when expected payment is not found."""
    pass


class ConfigurationError(CryptoScanError):
    """Raised when configuration is invalid."""
    pass


class ProviderError(CryptoScanError):
    """Raised when a network provider encounters an error."""
    
    def __init__(self, message: str, provider_name: str, 
                 original_error: Optional[Exception] = None):
        details = {"provider": provider_name}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details)
        self.provider_name = provider_name
        self.original_error = original_error


class ValidationError(CryptoScanError):
    """Raised when input validation fails."""
    pass


class TimeoutError(CryptoScanError):
    """Raised when operations timeout."""
    pass


class RateLimitError(NetworkError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after
