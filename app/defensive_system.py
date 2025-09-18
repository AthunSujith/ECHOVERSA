"""
Defensive Programming and Fallback Systems for EchoVerse
Provides centralized error handling, dependency checking, and graceful degradation
"""

import logging
import sys
import traceback
import functools
import warnings
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import importlib
import os


class SeverityLevel(Enum):
    """Severity levels for system issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComponentStatus(Enum):
    """Status of system components"""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class DependencyInfo:
    """Information about a system dependency"""
    name: str
    required: bool
    available: bool
    version: Optional[str] = None
    error_message: Optional[str] = None
    fallback_available: bool = False
    fallback_description: Optional[str] = None


@dataclass
class SystemIssue:
    """Represents a system issue or degradation"""
    component: str
    severity: SeverityLevel
    message: str
    details: Optional[str] = None
    suggested_action: Optional[str] = None
    timestamp: Optional[str] = None


class DefensiveLogger:
    """Enhanced logging system with defensive programming features"""
    
    def __init__(self, name: str = "echoverse", log_level: int = logging.INFO):
        """Initialize defensive logger"""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # File handler (if possible)
            try:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                file_handler = logging.FileHandler(log_dir / "echoverse.log")
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception:
                # Silently fail if we can't create log file
                pass
    
    def log_dependency_issue(self, dependency: str, error: Exception, fallback_available: bool = False):
        """Log dependency-related issues"""
        message = f"Dependency '{dependency}' unavailable: {str(error)}"
        if fallback_available:
            message += " (fallback available)"
        self.logger.warning(message)
    
    def log_api_failure(self, api_name: str, error: Exception, fallback_used: bool = False):
        """Log API failure with fallback information"""
        message = f"API '{api_name}' failed: {str(error)}"
        if fallback_used:
            message += " (using fallback)"
    
    # Convenience methods to match standard logger interface
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)
        self.logger.error(message)
    
    def log_graceful_degradation(self, component: str, reason: str, impact: str):
        """Log graceful degradation events"""
        self.logger.warning(f"Component '{component}' degraded: {reason}. Impact: {impact}")
    
    def log_user_notification(self, message: str, severity: SeverityLevel):
        """Log user notifications"""
        level_map = {
            SeverityLevel.CRITICAL: logging.CRITICAL,
            SeverityLevel.HIGH: logging.ERROR,
            SeverityLevel.MEDIUM: logging.WARNING,
            SeverityLevel.LOW: logging.INFO,
            SeverityLevel.INFO: logging.INFO
        }
        self.logger.log(level_map[severity], f"USER_NOTIFICATION: {message}")


class DependencyChecker:
    """Checks and manages system dependencies with fallback detection"""
    
    def __init__(self):
        """Initialize dependency checker"""
        self.logger = DefensiveLogger("dependency_checker")
        self._dependency_cache = {}
        self._check_results = {}
    
    def check_dependency(self, name: str, required: bool = False, 
                        fallback_available: bool = False, 
                        fallback_description: str = None) -> DependencyInfo:
        """
        Check if a dependency is available
        
        Args:
            name: Name of the dependency/module
            required: Whether this dependency is required for core functionality
            fallback_available: Whether a fallback exists
            fallback_description: Description of the fallback
            
        Returns:
            DependencyInfo object with availability status
        """
        if name in self._dependency_cache:
            return self._dependency_cache[name]
        
        try:
            module = importlib.import_module(name)
            version = getattr(module, '__version__', None)
            
            dep_info = DependencyInfo(
                name=name,
                required=required,
                available=True,
                version=version,
                fallback_available=fallback_available,
                fallback_description=fallback_description
            )
            
        except ImportError as e:
            error_msg = str(e)
            dep_info = DependencyInfo(
                name=name,
                required=required,
                available=False,
                error_message=error_msg,
                fallback_available=fallback_available,
                fallback_description=fallback_description
            )
            
            if required and not fallback_available:
                self.logger.log_dependency_issue(name, e, fallback_available)
        
        self._dependency_cache[name] = dep_info
        return dep_info
    
    def check_multiple_dependencies(self, dependencies: Dict[str, Dict[str, Any]]) -> Dict[str, DependencyInfo]:
        """
        Check multiple dependencies at once
        
        Args:
            dependencies: Dict mapping dependency names to their config
            
        Returns:
            Dict mapping dependency names to DependencyInfo objects
        """
        results = {}
        for name, config in dependencies.items():
            results[name] = self.check_dependency(
                name=name,
                required=config.get('required', False),
                fallback_available=config.get('fallback_available', False),
                fallback_description=config.get('fallback_description')
            )
        return results
    
    def get_system_dependencies_status(self) -> Dict[str, DependencyInfo]:
        """Get status of all EchoVerse system dependencies"""
        dependencies = {
            'streamlit': {
                'required': True,
                'fallback_available': False
            },
            'pyttsx3': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Mock TTS generator'
            },
            'requests': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Local-only mode'
            },
            'pydub': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Numpy-based audio mixing'
            },
            'numpy': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Basic audio operations'
            },
            'google.generativeai': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Mock content generator'
            },
            'streamlit_drawable_canvas': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Text-only input mode'
            },
            'whisper': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Audio upload without transcription'
            },
            'llama_cpp': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Cloud/mock generation only'
            },
            'huggingface_hub': {
                'required': False,
                'fallback_available': True,
                'fallback_description': 'Pre-downloaded models only'
            }
        }
        
        return self.check_multiple_dependencies(dependencies)


class GracefulDegradationManager:
    """Manages graceful degradation of system functionality"""
    
    def __init__(self):
        """Initialize degradation manager"""
        self.logger = DefensiveLogger("degradation_manager")
        self.component_status = {}
        self.active_issues = []
        self.user_notifications = []
    
    def register_component_degradation(self, component: str, reason: str, 
                                     impact: str, severity: SeverityLevel,
                                     suggested_action: str = None) -> SystemIssue:
        """
        Register a component degradation
        
        Args:
            component: Name of the degraded component
            reason: Reason for degradation
            impact: Impact on user experience
            severity: Severity level
            suggested_action: Optional suggested action for user
            
        Returns:
            SystemIssue object
        """
        issue = SystemIssue(
            component=component,
            severity=severity,
            message=f"{component} degraded: {reason}",
            details=f"Impact: {impact}",
            suggested_action=suggested_action,
            timestamp=None  # Could add timestamp if needed
        )
        
        self.active_issues.append(issue)
        self.component_status[component] = ComponentStatus.DEGRADED
        
        self.logger.log_graceful_degradation(component, reason, impact)
        
        return issue
    
    def register_component_failure(self, component: str, error: Exception,
                                 fallback_description: str = None) -> SystemIssue:
        """
        Register a complete component failure
        
        Args:
            component: Name of the failed component
            error: The exception that caused the failure
            fallback_description: Description of fallback behavior
            
        Returns:
            SystemIssue object
        """
        issue = SystemIssue(
            component=component,
            severity=SeverityLevel.HIGH,
            message=f"{component} failed: {str(error)}",
            details=f"Fallback: {fallback_description}" if fallback_description else "No fallback available",
            suggested_action="Check logs for details"
        )
        
        self.active_issues.append(issue)
        self.component_status[component] = ComponentStatus.UNAVAILABLE
        
        return issue
    
    def get_user_notifications(self, severity_threshold: SeverityLevel = SeverityLevel.MEDIUM) -> List[str]:
        """
        Get user-friendly notifications for issues above severity threshold
        
        Args:
            severity_threshold: Minimum severity to include
            
        Returns:
            List of user-friendly notification messages
        """
        severity_order = {
            SeverityLevel.CRITICAL: 5,
            SeverityLevel.HIGH: 4,
            SeverityLevel.MEDIUM: 3,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 1
        }
        
        threshold_value = severity_order[severity_threshold]
        notifications = []
        
        for issue in self.active_issues:
            if severity_order[issue.severity] >= threshold_value:
                message = self._create_user_friendly_message(issue)
                notifications.append(message)
        
        return notifications
    
    def _create_user_friendly_message(self, issue: SystemIssue) -> str:
        """Create user-friendly message from system issue"""
        severity_icons = {
            SeverityLevel.CRITICAL: "🚨",
            SeverityLevel.HIGH: "⚠️",
            SeverityLevel.MEDIUM: "⚠️",
            SeverityLevel.LOW: "ℹ️",
            SeverityLevel.INFO: "ℹ️"
        }
        
        icon = severity_icons.get(issue.severity, "ℹ️")
        
        # Create user-friendly component names
        friendly_names = {
            'gemini_api': 'AI Content Generation',
            'elevenlabs_api': 'Premium Text-to-Speech',
            'pyttsx3': 'Text-to-Speech',
            'pydub': 'Audio Processing',
            'streamlit_drawable_canvas': 'Drawing Canvas',
            'whisper': 'Audio Transcription',
            'local_models': 'Local AI Models'
        }
        
        component_name = friendly_names.get(issue.component, issue.component)
        
        if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            message = f"{icon} **{component_name}** is currently unavailable."
        else:
            message = f"{icon} **{component_name}** is running with limited functionality."
        
        if issue.details and "Fallback:" in issue.details:
            fallback = issue.details.split("Fallback: ")[1]
            message += f" Using {fallback} instead."
        
        if issue.suggested_action:
            message += f" {issue.suggested_action}"
        
        return message


def defensive_wrapper(fallback_value=None, log_errors=True, component_name=None):
    """
    Decorator for defensive programming - wraps functions with error handling
    
    Args:
        fallback_value: Value to return if function fails
        log_errors: Whether to log errors
        component_name: Name of component for logging
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = DefensiveLogger(component_name or func.__name__)
                    logger.logger.error(f"Function {func.__name__} failed: {str(e)}")
                    if hasattr(logger.logger, 'debug'):
                        logger.logger.debug(f"Traceback: {traceback.format_exc()}")
                
                return fallback_value
        return wrapper
    return decorator


def safe_api_call(api_name: str, api_function: Callable, fallback_function: Callable = None,
                 max_retries: int = 3, timeout: float = 30.0) -> Tuple[Any, bool]:
    """
    Safely call an API with automatic fallback and retry logic
    
    Args:
        api_name: Name of the API for logging
        api_function: Function to call the API
        fallback_function: Fallback function if API fails
        max_retries: Maximum number of retries
        timeout: Timeout for API calls
        
    Returns:
        Tuple of (result, success_flag)
    """
    logger = DefensiveLogger("api_caller")
    
    for attempt in range(max_retries):
        try:
            # Add timeout handling if the function supports it
            result = api_function()
            return result, True
            
        except Exception as e:
            logger.log_api_failure(api_name, e, fallback_function is not None)
            
            if attempt == max_retries - 1:
                # Final attempt failed, use fallback
                if fallback_function:
                    try:
                        fallback_result = fallback_function()
                        return fallback_result, False
                    except Exception as fallback_error:
                        logger.logger.error(f"Fallback for {api_name} also failed: {fallback_error}")
                        return None, False
                else:
                    return None, False
    
    return None, False


class UserNotificationManager:
    """Manages user notifications for degraded functionality"""
    
    def __init__(self):
        """Initialize notification manager"""
        self.logger = DefensiveLogger("notification_manager")
        self.shown_notifications = set()
        self.notification_history = []
    
    def notify_degraded_functionality(self, component: str, impact: str, 
                                    workaround: str = None, show_once: bool = True) -> str:
        """
        Create user notification for degraded functionality
        
        Args:
            component: Name of the affected component
            impact: Description of the impact
            workaround: Optional workaround description
            show_once: Whether to show this notification only once
            
        Returns:
            Formatted notification message
        """
        notification_key = f"{component}_{impact}"
        
        if show_once and notification_key in self.shown_notifications:
            return ""
        
        message = f"⚠️ **{component}** is currently limited: {impact}"
        
        if workaround:
            message += f" **Workaround:** {workaround}"
        
        self.shown_notifications.add(notification_key)
        self.notification_history.append(message)
        
        self.logger.log_user_notification(message, SeverityLevel.MEDIUM)
        
        return message
    
    def notify_feature_unavailable(self, feature: str, reason: str, 
                                 alternative: str = None) -> str:
        """
        Create user notification for unavailable features
        
        Args:
            feature: Name of the unavailable feature
            reason: Reason why it's unavailable
            alternative: Optional alternative suggestion
            
        Returns:
            Formatted notification message
        """
        message = f"ℹ️ **{feature}** is not available: {reason}"
        
        if alternative:
            message += f" You can try: {alternative}"
        
        self.notification_history.append(message)
        self.logger.log_user_notification(message, SeverityLevel.LOW)
        
        return message
    
    def get_active_notifications(self) -> List[str]:
        """Get list of active notifications"""
        return self.notification_history.copy()
    
    def clear_notifications(self):
        """Clear all notifications"""
        self.shown_notifications.clear()
        self.notification_history.clear()


# Global instances
_dependency_checker = None
_degradation_manager = None
_notification_manager = None
_defensive_logger = None


def get_dependency_checker() -> DependencyChecker:
    """Get global dependency checker instance"""
    global _dependency_checker
    if _dependency_checker is None:
        _dependency_checker = DependencyChecker()
    return _dependency_checker


def get_degradation_manager() -> GracefulDegradationManager:
    """Get global degradation manager instance"""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    return _degradation_manager


def get_notification_manager() -> UserNotificationManager:
    """Get global notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = UserNotificationManager()
    return _notification_manager


def get_defensive_logger(name: str = "echoverse") -> DefensiveLogger:
    """Get defensive logger instance"""
    global _defensive_logger
    if _defensive_logger is None:
        _defensive_logger = DefensiveLogger(name)
    return _defensive_logger


def initialize_defensive_systems() -> Dict[str, Any]:
    """
    Initialize all defensive systems and return system status
    
    Returns:
        Dictionary with system status information
    """
    logger = get_defensive_logger()
    dependency_checker = get_dependency_checker()
    degradation_manager = get_degradation_manager()
    notification_manager = get_notification_manager()
    
    logger.logger.info("Initializing defensive systems...")
    
    # Check all system dependencies
    dependencies_status = dependency_checker.get_system_dependencies_status()
    
    # Register degradations for missing dependencies
    for name, dep_info in dependencies_status.items():
        if not dep_info.available and dep_info.required:
            degradation_manager.register_component_failure(
                component=name,
                error=Exception(dep_info.error_message or "Dependency not available"),
                fallback_description=dep_info.fallback_description
            )
        elif not dep_info.available and dep_info.fallback_available:
            degradation_manager.register_component_degradation(
                component=name,
                reason=dep_info.error_message or "Dependency not available",
                impact=f"Using fallback: {dep_info.fallback_description}",
                severity=SeverityLevel.LOW
            )
    
    # Create system status report
    status_report = {
        'dependencies': dependencies_status,
        'active_issues': degradation_manager.active_issues,
        'component_status': degradation_manager.component_status,
        'user_notifications': degradation_manager.get_user_notifications(),
        'system_health': 'healthy' if not degradation_manager.active_issues else 'degraded'
    }
    
    logger.logger.info(f"Defensive systems initialized. System health: {status_report['system_health']}")
    
    return status_report


# Utility functions for common defensive patterns

def safe_import(module_name: str, fallback_value=None):
    """Safely import a module with fallback"""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        logger = get_defensive_logger()
        logger.log_dependency_issue(module_name, ImportError(f"Module {module_name} not available"), fallback_value is not None)
        return fallback_value


def suppress_warnings():
    """Suppress common warnings that don't affect functionality"""
    warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
    warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydub")


def create_fallback_response(component: str, operation: str, fallback_data: Any = None) -> Dict[str, Any]:
    """Create a standardized fallback response"""
    return {
        'success': False,
        'component': component,
        'operation': operation,
        'fallback_used': True,
        'data': fallback_data,
        'message': f"{component} unavailable, using fallback for {operation}"
    }