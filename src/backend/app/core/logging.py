"""
Logging configuration for JDA AI Portal Backend.
Implements structured logging with correlation IDs and proper formatting.
"""
import logging
import logging.config
import sys
from typing import Any, Dict

import structlog
from structlog.types import EventDict

from .config import get_settings

settings = get_settings()


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add correlation ID to log events when available.
    """
    # This will be populated by middleware
    correlation_id = getattr(logger._context, 'correlation_id', None)
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add timestamp to log events.
    """
    import datetime
    event_dict['timestamp'] = datetime.datetime.utcnow().isoformat() + 'Z'
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add log level to event dict.
    """
    event_dict['level'] = method_name.upper()
    return event_dict


def add_service_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add service information to log events.
    """
    event_dict.update({
        'service': 'jda-ai-portal-backend',
        'version': settings.VERSION,
        'environment': settings.ENVIRONMENT,
    })
    return event_dict


def setup_logging() -> None:
    """
    Setup structured logging configuration.
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Configure structlog
    processors = [
        add_service_info,
        add_timestamp,
        add_log_level,
        add_correlation_id,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    # Add appropriate renderer based on environment
    if settings.is_development:
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # JSON output for production
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Suppress noisy loggers in development
    if settings.is_development:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)


class LoggerMixin:
    """
    Mixin class to add structured logging to any class.
    """
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger instance with class context."""
        return structlog.get_logger(self.__class__.__name__)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a logger instance with optional name.
    
    Args:
        name: Logger name (defaults to caller's module name)
    
    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)


def log_function_call(func_name: str, **kwargs) -> None:
    """
    Log function call with parameters.
    
    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    logger = get_logger("function_calls")
    logger.info(
        f"🔧 Function called: {func_name}",
        function=func_name,
        parameters=kwargs,
    )


def log_database_operation(operation: str, table: str, **kwargs) -> None:
    """
    Log database operations.
    
    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table: Database table name
        **kwargs: Additional operation details
    """
    logger = get_logger("database")
    logger.info(
        f"🗄️ Database operation: {operation} on {table}",
        operation=operation,
        table=table,
        **kwargs,
    )


def log_api_request(method: str, endpoint: str, status_code: int, **kwargs) -> None:
    """
    Log API requests.
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        **kwargs: Additional request details
    """
    logger = get_logger("api")
    
    # Choose emoji based on status code
    if 200 <= status_code < 300:
        emoji = "✅"
    elif 400 <= status_code < 500:
        emoji = "⚠️"
    else:
        emoji = "❌"
    
    logger.info(
        f"{emoji} API Request: {method} {endpoint} - {status_code}",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        **kwargs,
    )


def log_ai_interaction(model: str, tokens_used: int, operation: str, **kwargs) -> None:
    """
    Log AI model interactions.
    
    Args:
        model: AI model name
        tokens_used: Number of tokens consumed
        operation: Type of AI operation
        **kwargs: Additional interaction details
    """
    logger = get_logger("ai")
    logger.info(
        f"🤖 AI Interaction: {operation} with {model}",
        model=model,
        tokens_used=tokens_used,
        operation=operation,
        **kwargs,
    )


def log_security_event(event_type: str, user_id: str = None, **kwargs) -> None:
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        user_id: User ID if applicable
        **kwargs: Additional security details
    """
    logger = get_logger("security")
    logger.warning(
        f"🔒 Security Event: {event_type}",
        event_type=event_type,
        user_id=user_id,
        **kwargs,
    )


# Context manager for adding correlation ID to logs
class CorrelationIDContext:
    """
    Context manager for adding correlation ID to all logs within the context.
    """
    
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self._token = None
    
    def __enter__(self):
        self._token = structlog.contextvars.bind_contextvars(
            correlation_id=self.correlation_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            structlog.contextvars.unbind_contextvars("correlation_id") 