"""
Logging configuration for EchoVerse application
Provides structured logging with defensive programming support
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import traceback
from datetime import datetime


class DefensiveFormatter(logging.Formatter):
    """Custom formatter that handles errors gracefully"""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
    
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            # Fallback formatting if main formatter fails
            return f"{record.levelname}: {record.getMessage()}"


class SafeFileHandler(logging.FileHandler):
    """File handler that gracefully handles file system errors"""
    
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        try:
            # Ensure directory exists
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            super().__init__(filename, mode, encoding, delay)
        except Exception:
            # If file handler fails, create a null handler
            super(logging.Handler, self).__init__()
            self.setLevel(logging.CRITICAL + 1)  # Effectively disable
    
    def emit(self, record):
        try:
            super().emit(record)
        except Exception:
            # Silently fail if we can't write to file
            pass


def setup_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up comprehensive logging with defensive error handling
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional log file path
        console_output: Whether to output to console
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create main logger
    logger = logging.getLogger("echoverse")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = DefensiveFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            logger.addHandler(console_handler)
        except Exception:
            # If console handler fails, continue without it
            pass
    
    # File handler with rotation
    if log_file:
        try:
            # Use rotating file handler to prevent huge log files
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
        except Exception:
            # If file handler fails, try simple file handler
            try:
                simple_handler = SafeFileHandler(log_file, encoding='utf-8')
                simple_handler.setFormatter(formatter)
                simple_handler.setLevel(log_level)
                logger.addHandler(simple_handler)
            except Exception:
                # If all file handlers fail, continue without file logging
                pass
    
    # Add error handler for uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception
    
    return logger


def log_system_info(logger: logging.Logger):
    """Log system information for debugging"""
    try:
        import platform
        import sys
        
        logger.info(f"System: {platform.system()} {platform.release()}")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Platform: {platform.platform()}")
        
        # Log memory usage if psutil is available
        try:
            import psutil
            memory = psutil.virtual_memory()
            logger.info(f"Memory: {memory.total // (1024**3)}GB total, {memory.available // (1024**3)}GB available")
        except ImportError:
            pass
            
    except Exception as e:
        logger.warning(f"Could not log system info: {e}")


def create_component_logger(component_name: str, parent_logger: Optional[logging.Logger] = None) -> logging.Logger:
    """
    Create a logger for a specific component
    
    Args:
        component_name: Name of the component
        parent_logger: Optional parent logger
        
    Returns:
        Component-specific logger
    """
    if parent_logger:
        logger_name = f"{parent_logger.name}.{component_name}"
    else:
        logger_name = f"echoverse.{component_name}"
    
    return logging.getLogger(logger_name)


class ContextualLogger:
    """Logger that adds contextual information to log messages"""
    
    def __init__(self, logger: logging.Logger, context: dict = None):
        self.logger = logger
        self.context = context or {}
    
    def _format_message(self, message: str) -> str:
        """Add context to log message"""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"[{context_str}] {message}"
        return message
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(self._format_message(message), **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(self._format_message(message), **kwargs)
    
    def exception(self, message: str, **kwargs):
        self.logger.exception(self._format_message(message), **kwargs)


def setup_application_logging() -> logging.Logger:
    """Set up logging for the entire EchoVerse application"""
    
    # Determine log file path
    log_dir = Path("logs")
    log_file = log_dir / "echoverse.log"
    
    # Set up main logger
    logger = setup_logging(
        log_level=logging.INFO,
        log_file=str(log_file),
        console_output=True,
        max_file_size=10 * 1024 * 1024,  # 10MB
        backup_count=5
    )
    
    # Log startup information
    logger.info("=" * 50)
    logger.info("EchoVerse Application Starting")
    logger.info("=" * 50)
    
    log_system_info(logger)
    
    # Set up component loggers
    component_loggers = [
        "auth_manager",
        "content_generator", 
        "audio_processor",
        "storage_manager",
        "input_processor",
        "streamlit_app",
        "defensive_system"
    ]
    
    for component in component_loggers:
        create_component_logger(component, logger)
    
    return logger


def log_performance_metrics(logger: logging.Logger, operation: str, duration: float, **metrics):
    """Log performance metrics for operations"""
    try:
        metrics_str = " | ".join(f"{k}={v}" for k, v in metrics.items())
        logger.info(f"PERFORMANCE: {operation} completed in {duration:.3f}s | {metrics_str}")
    except Exception:
        # Fallback if metrics logging fails
        logger.info(f"PERFORMANCE: {operation} completed in {duration:.3f}s")


def log_user_action(logger: logging.Logger, user_id: str, action: str, details: dict = None):
    """Log user actions for audit trail"""
    try:
        details_str = ""
        if details:
            details_str = " | " + " | ".join(f"{k}={v}" for k, v in details.items())
        
        logger.info(f"USER_ACTION: {user_id} - {action}{details_str}")
    except Exception:
        # Fallback if user action logging fails
        logger.info(f"USER_ACTION: {user_id} - {action}")


def log_api_call(logger: logging.Logger, api_name: str, success: bool, duration: float, error: str = None):
    """Log API calls for monitoring"""
    try:
        status = "SUCCESS" if success else "FAILED"
        message = f"API_CALL: {api_name} - {status} in {duration:.3f}s"
        
        if error:
            message += f" | Error: {error}"
        
        if success:
            logger.info(message)
        else:
            logger.error(message)
    except Exception:
        # Fallback if API logging fails
        logger.info(f"API_CALL: {api_name} - {'SUCCESS' if success else 'FAILED'}")


# Global logger instance
_application_logger = None


def get_application_logger() -> logging.Logger:
    """Get the global application logger"""
    global _application_logger
    if _application_logger is None:
        _application_logger = setup_application_logging()
    return _application_logger


def shutdown_logging():
    """Properly shutdown logging system"""
    try:
        logger = get_application_logger()
        logger.info("=" * 50)
        logger.info("EchoVerse Application Shutting Down")
        logger.info("=" * 50)
        
        # Close all handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
            
    except Exception:
        # Silently fail if shutdown logging fails
        pass