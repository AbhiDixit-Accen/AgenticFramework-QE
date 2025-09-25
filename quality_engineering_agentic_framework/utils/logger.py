"""
Logger Module

This module provides logging functionality for the framework.
"""

import logging
import os
from typing import Dict, Any

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(config: Dict[str, Any] = None) -> None:
    """
    Set up logging based on configuration.
    
    Args:
        config: Dictionary containing logging configuration
    """
    if config is None:
        config = {}
    
    log_level_str = config.get("level", "INFO")
    log_level = getattr(logging, log_level_str.upper(), DEFAULT_LOG_LEVEL)
    
    log_format = config.get("format", DEFAULT_LOG_FORMAT)
    log_file = config.get("file")
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        filename=log_file,
        filemode="a" if log_file else None
    )
    
    # If log file is specified, also log to console
    if log_file:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(console_handler)
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name for the logger, typically __name__
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)