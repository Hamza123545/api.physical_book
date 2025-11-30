"""
Structured logging utility for Physical AI Textbook Backend
Provides consistent logging across all services with contextual information
"""
import logging
import sys
import os
from typing import Optional
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields from extra dict
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    structured: bool = True
) -> logging.Logger:
    """
    Setup and configure a logger with structured formatting
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use JSON structured logging (default: True)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Get log level from environment or use provided level
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **kwargs
):
    """
    Log a message with additional context fields
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context fields to include in log
    """
    log_method = getattr(logger, level.lower())
    extra = {"extra_fields": kwargs}
    log_method(message, extra=extra)


# Create default application logger
app_logger = setup_logger("physical_ai_backend")


# Example usage helper functions
def log_api_request(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    session_id: Optional[str] = None,
    **kwargs
):
    """Log API request with standardized context"""
    log_with_context(
        logger,
        "info",
        f"{method} {endpoint}",
        endpoint=endpoint,
        method=method,
        session_id=session_id,
        **kwargs
    )


def log_db_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    duration_ms: Optional[float] = None,
    **kwargs
):
    """Log database operation with standardized context"""
    log_with_context(
        logger,
        "info",
        f"DB operation: {operation} on {table}",
        operation=operation,
        table=table,
        duration_ms=duration_ms,
        **kwargs
    )


def log_external_api_call(
    logger: logging.Logger,
    service: str,
    operation: str,
    duration_ms: Optional[float] = None,
    success: bool = True,
    **kwargs
):
    """Log external API call (OpenAI, Qdrant) with standardized context"""
    level = "info" if success else "warning"
    log_with_context(
        logger,
        level,
        f"External API: {service} - {operation}",
        service=service,
        operation=operation,
        duration_ms=duration_ms,
        success=success,
        **kwargs
    )
