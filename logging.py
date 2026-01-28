"""
Logging Configuration
=====================

Structured logging setup using structlog for production-ready logging.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if settings.APP_ENV == "production":
        # JSON logging for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable logging for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Set log levels for noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("filelock").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class RequestLogger:
    """Context manager for request logging."""
    
    def __init__(self, request_id: str, endpoint: str, method: str):
        self.request_id = request_id
        self.endpoint = endpoint
        self.method = method
        self.logger = get_logger("request")
    
    def __enter__(self):
        self.logger.info(
            "Request started",
            request_id=self.request_id,
            endpoint=self.endpoint,
            method=self.method,
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(
                "Request failed",
                request_id=self.request_id,
                endpoint=self.endpoint,
                error=str(exc_val),
            )
        else:
            self.logger.info(
                "Request completed",
                request_id=self.request_id,
                endpoint=self.endpoint,
            )