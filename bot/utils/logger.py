"""
Centralized logging configuration for VertBot.
Provides consistent logging across all modules.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional
from pathlib import Path

from config.constants import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "vertbot",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    console: bool = True,
    colored: bool = True
) -> logging.Logger:
    """
    Set up a logger with consistent configuration.
    
    Args:
        name: Logger name (usually module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        console: Whether to log to console
        colored: Whether to use colored output for console
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, level or LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        if colored and sys.stdout.isatty():
            console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        else:
            console_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the default configuration.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return setup_logger(name)


# Create default logger for the bot
bot_logger = setup_logger(
    "vertbot",
    log_file="logs/vertbot.log" if not os.getenv("DOCKER_ENV") else None
)


class LoggerMixin:
    """
    Mixin class that provides a logger property.
    Can be used with any class to add logging capabilities.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for the current class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


def log_command(command_name: str, user: str, guild: str, args: str = ""):
    """
    Log command usage for auditing and debugging.
    
    Args:
        command_name: Name of the command
        user: User who invoked the command
        guild: Guild where command was invoked
        args: Command arguments
    """
    logger = get_logger("vertbot.commands")
    logger.info(f"Command: {command_name} | User: {user} | Guild: {guild} | Args: {args}")


def log_api_call(api_name: str, endpoint: str, status: str, response_time: float = 0):
    """
    Log API calls for monitoring and debugging.
    
    Args:
        api_name: Name of the API (e.g., "finnhub", "yfinance")
        endpoint: API endpoint or ticker
        status: Response status (success/error)
        response_time: Time taken for the API call
    """
    logger = get_logger("vertbot.api")
    logger.info(f"API: {api_name} | Endpoint: {endpoint} | Status: {status} | Time: {response_time:.2f}s")


def log_error(module: str, error: Exception, context: str = ""):
    """
    Log errors with full context.
    
    Args:
        module: Module where error occurred
        error: The exception object
        context: Additional context about the error
    """
    logger = get_logger(f"vertbot.{module}")
    logger.error(f"Error in {module}: {str(error)} | Context: {context}", exc_info=True)