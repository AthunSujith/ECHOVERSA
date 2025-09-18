"""
Comprehensive error handling utilities for EchoVerse
Provides specialized error handlers for different types of failures
"""

import functools
import traceback
import time
from typing import Any, Callable, Dict, Optional, Tuple, Union
from enum import Enum
import logging

from defensive_system import (
    get_defensive_logger, get_degradation_manager, 
    get_notification_manager, SeverityLevel
)


class ErrorCategory(Enum):
    """Categories of errors for specialized handling"""
    NETWORK = "network"
    API = "api"
    FILE_SYSTEM = "file_system"
    DEPENDENCY = "dependency"
    USER_INPUT = "user_input"
    PROCESSING = "processing"
    AUTHENTICATION = "authentication"
    STORAGE = "storage"
    AUDIO = "audio"
    CONTENT_GENERATION = "content_generation"


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@functools.lru_cache(maxsize=128)
def get_user_friendly_message(error_category: ErrorCategory, error_type: str) -> str:
    """Get user-friendly error messages based on error category and type"""
    
    messages = {
        ErrorCategory.NETWORK: {
            'timeout': "Connection timed out. Please check your internet connection and try again.",
            'connection_error': "Unable to connect to the service. Please check your internet connection.",
            'dns_error': "Unable to resolve server address. Please check your internet connection.",
            'default': "Network error occurred. Please check your connection and try again."
        },
        ErrorCategory.API: {
            'rate_limit': "Service is temporarily busy. Please wait a moment and try again.",
            'authentication': "Authentication failed. Please check your API credentials.",
            'quota_exceeded': "Service quota exceeded. Please try again later or upgrade your plan.",
            'service_unavailable': "Service is temporarily unavailable. Using fallback instead.",
            'default': "External service error. Using alternative method."
        },
        ErrorCategory.FILE_SYSTEM: {
            'permission_denied': "Permission denied. Please check file permissions.",
            'disk_full': "Not enough disk space. Please free up some space and try again.",
            'file_not_found': "Required file not found. Please check the file path.",
            'default': "File system error occurred. Please check file permissions and disk space."
        },
        ErrorCategory.DEPENDENCY: {
            'import_error': "Required component not available. Using alternative method.",
            'version_mismatch': "Component version incompatible. Some features may be limited.",
            'default': "Optional component unavailable. Core functionality will continue to work."
        },
        ErrorCategory.USER_INPUT: {
            'invalid_format': "Invalid input format. Please check your input and try again.",
            'empty_input': "Input cannot be empty. Please provide some content.",
            'too_large': "Input is too large. Please try with smaller content.",
            'default': "Invalid input. Please check your input and try again."
        },
        ErrorCategory.PROCESSING: {
            'timeout': "Processing took too long. Please try with simpler input.",
            'memory_error': "Not enough memory to process. Please try with smaller input.",
            'default': "Processing error occurred. Please try again."
        },
        ErrorCategory.AUTHENTICATION: {
            'invalid_credentials': "Invalid username or password. Please try again.",
            'session_expired': "Your session has expired. Please log in again.",
            'account_locked': "Account temporarily locked. Please try again later.",
            'default': "Authentication error. Please log in again."
        },
        ErrorCategory.STORAGE: {
            'save_failed': "Failed to save data. Your work is preserved in this session.",
            'load_failed': "Failed to load data. Please try refreshing the page.",
            'corruption': "Data corruption detected. Using backup if available.",
            'default': "Storage error occurred. Your current work is preserved."
        },
        ErrorCategory.AUDIO: {
            'tts_failed': "Text-to-speech conversion failed. Text content is still available.",
            'audio_processing_failed': "Audio processing failed. Using simplified audio.",
            'codec_error': "Audio format not supported. Please try a different format.",
            'default': "Audio processing error. Text content remains available."
        },
        ErrorCategory.CONTENT_GENERATION: {
            'api_failed': "AI service unavailable. Using alternative content generation.",
            'quota_exceeded': "AI service quota exceeded. Using fallback generation.",
            'content_filter': "Content was filtered. Please try rephrasing your input.",
            'default': "Content generation error. Using alternative method."
        }
    }
    
    category_messages = messages.get(error_category, {})
    return category_messages.get(error_type, category_messages.get('default', 
        "An error occurred. The application will continue with available features."))


class ErrorHandler:
    """Comprehensive error handler with context awareness"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = get_defensive_logger(component_name)
        self.degradation_manager = get_degradation_manager()
        self.notification_manager = get_notification_manager()
        self.error_counts = {}
        self.last_error_times = {}
    
    def handle_error(self, 
                    error: Exception, 
                    category: ErrorCategory,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Dict[str, Any] = None,
                    user_message: str = None,
                    fallback_description: str = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and user notification
        
        Args:
            error: The exception that occurred
            category: Category of the error
            severity: Severity level
            context: Additional context information
            user_message: Custom user-friendly message
            fallback_description: Description of fallback behavior
            
        Returns:
            Dictionary with error handling results
        """
        error_type = type(error).__name__.lower()
        context = context or {}
        
        # Track error frequency
        error_key = f"{category.value}_{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_times[error_key] = time.time()
        
        # Log the error with context
        self._log_error(error, category, severity, context)
        
        # Register with degradation manager
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            self.degradation_manager.register_component_failure(
                component=self.component_name,
                error=error,
                fallback_description=fallback_description
            )
        else:
            self.degradation_manager.register_component_degradation(
                component=self.component_name,
                reason=str(error),
                impact=fallback_description or "Reduced functionality",
                severity=SeverityLevel(severity.value)
            )
        
        # Generate user-friendly message
        if not user_message:
            user_message = get_user_friendly_message(category, error_type)
        
        # Create notification if needed
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH, ErrorSeverity.MEDIUM]:
            self.notification_manager.notify_degraded_functionality(
                component=self.component_name,
                impact=user_message,
                workaround=fallback_description
            )
        
        return {
            'handled': True,
            'category': category.value,
            'severity': severity.value,
            'user_message': user_message,
            'error_count': self.error_counts[error_key],
            'fallback_available': bool(fallback_description),
            'context': context
        }
    
    def _log_error(self, error: Exception, category: ErrorCategory, 
                  severity: ErrorSeverity, context: Dict[str, Any]):
        """Log error with appropriate level and context"""
        
        log_message = f"[{category.value.upper()}] {str(error)}"
        
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            log_message += f" | Context: {context_str}"
        
        # Add stack trace for debugging
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            log_message += f"\nStacktrace: {traceback.format_exc()}"
        
        # Log at appropriate level
        if severity == ErrorSeverity.CRITICAL:
            self.logger.logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.logger.warning(log_message)
        else:
            self.logger.logger.info(log_message)
    
    def is_error_frequent(self, category: ErrorCategory, error_type: str, 
                         threshold: int = 5, time_window: int = 300) -> bool:
        """Check if an error is occurring frequently"""
        error_key = f"{category.value}_{error_type}"
        
        if error_key not in self.error_counts:
            return False
        
        count = self.error_counts[error_key]
        last_time = self.last_error_times.get(error_key, 0)
        
        return count >= threshold and (time.time() - last_time) < time_window


def network_error_handler(component_name: str):
    """Decorator for handling network-related errors"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(component_name)
            try:
                return func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                handler.handle_error(
                    error=e,
                    category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.MEDIUM,
                    fallback_description="Using offline mode"
                )
                return None
            except Exception as e:
                if "timeout" in str(e).lower():
                    handler.handle_error(
                        error=e,
                        category=ErrorCategory.NETWORK,
                        severity=ErrorSeverity.MEDIUM,
                        fallback_description="Using offline mode"
                    )
                else:
                    handler.handle_error(
                        error=e,
                        category=ErrorCategory.PROCESSING,
                        severity=ErrorSeverity.HIGH
                    )
                return None
        return wrapper
    return decorator


def api_error_handler(api_name: str, fallback_function: Callable = None):
    """Decorator for handling API-related errors"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(f"{api_name}_api")
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_type = "default"
                severity = ErrorSeverity.MEDIUM
                
                # Classify API errors
                error_str = str(e).lower()
                if "rate limit" in error_str or "429" in error_str:
                    error_type = "rate_limit"
                elif "quota" in error_str or "billing" in error_str:
                    error_type = "quota_exceeded"
                elif "401" in error_str or "403" in error_str:
                    error_type = "authentication"
                    severity = ErrorSeverity.HIGH
                elif "503" in error_str or "502" in error_str:
                    error_type = "service_unavailable"
                
                handler.handle_error(
                    error=e,
                    category=ErrorCategory.API,
                    severity=severity,
                    context={'api_name': api_name, 'error_type': error_type},
                    fallback_description=f"Using fallback for {api_name}"
                )
                
                # Try fallback if available
                if fallback_function:
                    try:
                        return fallback_function(*args, **kwargs)
                    except Exception as fallback_error:
                        handler.handle_error(
                            error=fallback_error,
                            category=ErrorCategory.PROCESSING,
                            severity=ErrorSeverity.HIGH,
                            context={'fallback_for': api_name}
                        )
                
                return None
        return wrapper
    return decorator


def file_system_error_handler(component_name: str):
    """Decorator for handling file system errors"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(component_name)
            try:
                return func(*args, **kwargs)
            except PermissionError as e:
                handler.handle_error(
                    error=e,
                    category=ErrorCategory.FILE_SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    fallback_description="Using temporary storage"
                )
                return None
            except FileNotFoundError as e:
                handler.handle_error(
                    error=e,
                    category=ErrorCategory.FILE_SYSTEM,
                    severity=ErrorSeverity.MEDIUM,
                    fallback_description="Creating new file"
                )
                return None
            except OSError as e:
                if "No space left" in str(e):
                    error_type = "disk_full"
                    severity = ErrorSeverity.HIGH
                else:
                    error_type = "default"
                    severity = ErrorSeverity.MEDIUM
                
                handler.handle_error(
                    error=e,
                    category=ErrorCategory.FILE_SYSTEM,
                    severity=severity,
                    fallback_description="Using memory storage"
                )
                return None
        return wrapper
    return decorator


def safe_execute(func: Callable, 
                fallback_value: Any = None,
                error_category: ErrorCategory = ErrorCategory.PROCESSING,
                component_name: str = "unknown",
                max_retries: int = 0,
                retry_delay: float = 1.0) -> Tuple[Any, bool]:
    """
    Safely execute a function with error handling and optional retries
    
    Args:
        func: Function to execute
        fallback_value: Value to return if function fails
        error_category: Category of potential errors
        component_name: Name of component for logging
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of (result, success_flag)
    """
    handler = ErrorHandler(component_name)
    
    for attempt in range(max_retries + 1):
        try:
            result = func()
            return result, True
        except Exception as e:
            if attempt == max_retries:
                # Final attempt failed
                handler.handle_error(
                    error=e,
                    category=error_category,
                    severity=ErrorSeverity.MEDIUM if max_retries > 0 else ErrorSeverity.LOW,
                    context={'attempt': attempt + 1, 'max_retries': max_retries}
                )
                return fallback_value, False
            else:
                # Retry after delay
                time.sleep(retry_delay)
    
    return fallback_value, False


def create_error_boundary(component_name: str, 
                         fallback_value: Any = None,
                         error_categories: list = None):
    """
    Create an error boundary decorator for a component
    
    Args:
        component_name: Name of the component
        fallback_value: Default fallback value
        error_categories: List of error categories to handle
        
    Returns:
        Decorator function
    """
    error_categories = error_categories or [ErrorCategory.PROCESSING]
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(component_name)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Determine error category
                category = ErrorCategory.PROCESSING
                for cat in error_categories:
                    if cat == ErrorCategory.NETWORK and isinstance(e, (ConnectionError, TimeoutError)):
                        category = ErrorCategory.NETWORK
                        break
                    elif cat == ErrorCategory.FILE_SYSTEM and isinstance(e, (FileNotFoundError, PermissionError, OSError)):
                        category = ErrorCategory.FILE_SYSTEM
                        break
                    elif cat == ErrorCategory.USER_INPUT and isinstance(e, (ValueError, TypeError)):
                        category = ErrorCategory.USER_INPUT
                        break
                
                handler.handle_error(
                    error=e,
                    category=category,
                    severity=ErrorSeverity.MEDIUM,
                    context={'function': func.__name__}
                )
                
                return fallback_value
        return wrapper
    return decorator


# Global error handlers for common patterns
network_safe = lambda component: network_error_handler(component)
api_safe = lambda api_name, fallback=None: api_error_handler(api_name, fallback)
file_safe = lambda component: file_system_error_handler(component)
error_boundary = lambda component, fallback_value=None: create_error_boundary(component, fallback_value)