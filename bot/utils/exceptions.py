"""
Custom exception classes for VertBot.
Provides consistent error handling and user-friendly error messages.
"""

from typing import Optional


class VertBotException(Exception):
    """Base exception class for all VertBot exceptions."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        """
        Initialize exception.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message to display in Discord
        """
        super().__init__(message)
        self.user_message = user_message or "An error occurred. Please try again later."


class APIException(VertBotException):
    """Exception for API-related errors."""
    
    def __init__(self, api_name: str, message: str, user_message: Optional[str] = None):
        """
        Initialize API exception.
        
        Args:
            api_name: Name of the API that failed
            message: Technical error message
            user_message: User-friendly message
        """
        super().__init__(f"{api_name} API error: {message}", user_message)
        self.api_name = api_name


class MarketDataException(APIException):
    """Exception for market data API errors."""
    
    def __init__(self, ticker: str, message: str):
        super().__init__(
            "Market Data",
            f"Failed to fetch data for {ticker}: {message}",
            f"❌ Unable to fetch market data for **{ticker}**. Please try again later."
        )
        self.ticker = ticker


class NewsDataException(APIException):
    """Exception for news API errors."""
    
    def __init__(self, ticker: str, message: str):
        super().__init__(
            "News",
            f"Failed to fetch news for {ticker}: {message}",
            f"❌ Unable to fetch news for **{ticker}**. Please try again later."
        )
        self.ticker = ticker


class OllamaException(APIException):
    """Exception for Ollama/AI service errors."""
    
    def __init__(self, message: str):
        super().__init__(
            "Ollama",
            message,
            "❌ AI service is currently unavailable. Please try again later."
        )


class ConfigurationException(VertBotException):
    """Exception for configuration-related errors."""
    
    def __init__(self, config_name: str, message: str):
        super().__init__(
            f"Configuration error for {config_name}: {message}",
            "❌ Configuration error. Please contact an administrator."
        )
        self.config_name = config_name


class InvalidTickerException(VertBotException):
    """Exception for invalid ticker symbols."""
    
    def __init__(self, ticker: str):
        super().__init__(
            f"Invalid ticker symbol: {ticker}",
            f"❌ **{ticker}** is not a valid ticker symbol."
        )
        self.ticker = ticker


class MarketClosedException(VertBotException):
    """Exception for operations that require market to be open."""
    
    def __init__(self):
        super().__init__(
            "Market is closed",
            "📊 **Market is closed**\n"
            "Trading hours: Monday-Friday, 9:30 AM - 4:00 PM ET\n"
            "Use `!price` for the last closing price."
        )


class RateLimitException(VertBotException):
    """Exception for rate limit violations."""
    
    def __init__(self, service: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {service}"
        user_msg = f"⏱️ Rate limit exceeded. Please try again"
        if retry_after:
            user_msg += f" in {retry_after} seconds"
        else:
            user_msg += " later"
        
        super().__init__(message, user_msg + ".")
        self.service = service
        self.retry_after = retry_after


class PermissionException(VertBotException):
    """Exception for permission-related errors."""
    
    def __init__(self, required_permission: str):
        super().__init__(
            f"Missing required permission: {required_permission}",
            f"❌ You need **{required_permission}** permission to use this command."
        )
        self.required_permission = required_permission


class DataNotFoundException(VertBotException):
    """Exception when requested data is not found."""
    
    def __init__(self, data_type: str, identifier: str):
        super().__init__(
            f"{data_type} not found for {identifier}",
            f"❌ No {data_type.lower()} found for **{identifier}**."
        )
        self.data_type = data_type
        self.identifier = identifier


class ValidationException(VertBotException):
    """Exception for input validation errors."""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            f"Validation error for {field}: {message}",
            f"❌ Invalid {field}: {message}"
        )
        self.field = field