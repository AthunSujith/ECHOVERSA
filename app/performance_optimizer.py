"""
Performance optimization system for EchoVerse companion application.
Provides loading indicators, caching, memory optimization, and progress tracking.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import weakref
import gc
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor, Future

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

try:
    from .defensive_system import get_defensive_logger
    from .data_models import User, Interaction
except ImportError:
    from defensive_system import get_defensive_logger
    from data_models import User, Interaction


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_before: Optional[int] = None
    memory_after: Optional[int] = None
    cache_hits: int = 0
    cache_misses: int = 0
    success: bool = True
    error_message: Optional[str] = None


class LoadingIndicator:
    """Context manager for showing loading indicators in Streamlit."""
    
    def __init__(self, message: str = "Loading...", show_spinner: bool = True):
        """
        Initialize loading indicator.
        
        Args:
            message: Loading message to display
            show_spinner: Whether to show spinner animation
        """
        self.message = message
        self.show_spinner = show_spinner
        self.placeholder = None
        self.spinner_context = None
        
    def __enter__(self):
        """Start showing loading indicator."""
        if STREAMLIT_AVAILABLE:
            if self.show_spinner:
                self.spinner_context = st.spinner(self.message)
                self.spinner_context.__enter__()
            else:
                self.placeholder = st.empty()
                self.placeholder.info(f"🔄 {self.message}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop showing loading indicator."""
        if STREAMLIT_AVAILABLE:
            if self.spinner_context:
                self.spinner_context.__exit__(exc_type, exc_val, exc_tb)
            elif self.placeholder:
                self.placeholder.empty()
    
    def update_message(self, new_message: str):
        """Update the loading message."""
        self.message = new_message
        if STREAMLIT_AVAILABLE and self.placeholder:
            self.placeholder.info(f"🔄 {new_message}")


class ProgressTracker:
    """Progress tracking for long-running operations."""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps in the operation
            description: Description of the operation
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
        self.progress_bar = None
        self.status_text = None
        
        if STREAMLIT_AVAILABLE:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            self._update_display()
    
    def update(self, step: int = None, message: str = None):
        """
        Update progress.
        
        Args:
            step: Current step number (if None, increments by 1)
            message: Optional status message
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        if message:
            self.description = message
        
        self._update_display()
    
    def _update_display(self):
        """Update the progress display."""
        if not STREAMLIT_AVAILABLE:
            return
        
        progress = min(self.current_step / self.total_steps, 1.0)
        elapsed = time.time() - self.start_time
        
        if self.progress_bar:
            self.progress_bar.progress(progress)
        
        if self.status_text:
            eta_text = ""
            if progress > 0 and progress < 1:
                eta = (elapsed / progress) * (1 - progress)
                eta_text = f" (ETA: {eta:.1f}s)"
            
            status_msg = f"{self.description} - {self.current_step}/{self.total_steps}{eta_text}"
            self.status_text.text(status_msg)
    
    def complete(self, message: str = "Complete"):
        """Mark operation as complete."""
        self.current_step = self.total_steps
        self.description = message
        self._update_display()
        
        # Clear after a short delay
        if STREAMLIT_AVAILABLE:
            time.sleep(0.5)
            if self.progress_bar:
                self.progress_bar.empty()
            if self.status_text:
                self.status_text.empty()


class MemoryOptimizer:
    """Memory usage optimization and monitoring."""
    
    def __init__(self):
        """Initialize memory optimizer."""
        self.logger = get_defensive_logger("memory_optimizer")
        self.weak_refs: List[weakref.ref] = []
        self.cache_size_limit = 50 * 1024 * 1024  # 50MB
        self.cleanup_threshold = 0.8  # Cleanup when 80% of limit reached
        
    def get_memory_usage(self) -> Dict[str, int]:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory usage information
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss": memory_info.rss,  # Resident Set Size
                "vms": memory_info.vms,  # Virtual Memory Size
                "percent": process.memory_percent(),
                "available": psutil.virtual_memory().available
            }
        except ImportError:
            # Fallback without psutil
            import sys
            return {
                "objects": len(gc.get_objects()),
                "sys_size": sys.getsizeof(gc.get_objects())
            }
    
    def optimize_memory(self, force_gc: bool = False) -> Dict[str, Any]:
        """
        Perform memory optimization.
        
        Args:
            force_gc: Force garbage collection
            
        Returns:
            Dictionary with optimization results
        """
        start_memory = self.get_memory_usage()
        
        # Clean up weak references
        self.weak_refs = [ref for ref in self.weak_refs if ref() is not None]
        
        # Force garbage collection if requested
        if force_gc:
            collected = gc.collect()
        else:
            collected = 0
        
        end_memory = self.get_memory_usage()
        
        result = {
            "memory_before": start_memory,
            "memory_after": end_memory,
            "objects_collected": collected,
            "weak_refs_cleaned": len([ref for ref in self.weak_refs if ref() is None])
        }
        
        self.logger.logger.info(f"Memory optimization completed: {collected} objects collected")
        
        return result
    
    def register_for_cleanup(self, obj: Any):
        """Register an object for automatic cleanup."""
        self.weak_refs.append(weakref.ref(obj))
    
    def should_cleanup(self) -> bool:
        """Check if memory cleanup should be performed."""
        try:
            memory_info = self.get_memory_usage()
            if "rss" in memory_info:
                return memory_info["rss"] > self.cache_size_limit * self.cleanup_threshold
            return len(gc.get_objects()) > 10000  # Fallback threshold
        except Exception:
            return False


class SmartCache:
    """Intelligent caching system with automatic cleanup and optimization."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize smart cache.
        
        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.hit_count = 0
        self.miss_count = 0
        self.logger = get_defensive_logger("smart_cache")
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.miss_count += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            self.miss_count += 1
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        self.hit_count += 1
        
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl_override: Optional[int] = None):
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_override: Override default TTL for this item
        """
        # Clean up if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        ttl = ttl_override or self.ttl_seconds
        
        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
            "access_count": 1
        }
        self.access_times[key] = time.time()
    
    def invalidate(self, key: str):
        """Remove item from cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
        self.hit_count = 0
        self.miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds
        }
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.invalidate(lru_key)
    
    def _periodic_cleanup(self):
        """Periodic cleanup of expired entries."""
        while True:
            try:
                time.sleep(60)  # Cleanup every minute
                current_time = time.time()
                expired_keys = []
                
                for key, entry in self.cache.items():
                    if current_time - entry["timestamp"] > entry["ttl"]:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    self.invalidate(key)
                
                if expired_keys:
                    self.logger.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                self.logger.logger.error(f"Cache cleanup error: {e}")


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        """Initialize performance optimizer."""
        self.logger = get_defensive_logger("performance_optimizer")
        self.memory_optimizer = MemoryOptimizer()
        self.cache = SmartCache(max_size=200, ttl_seconds=600)  # 10 minutes
        self.metrics: List[PerformanceMetrics] = []
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="perf_opt")
        
        # File I/O optimization
        self.file_cache = SmartCache(max_size=50, ttl_seconds=300)  # 5 minutes
        self.batch_operations: List[Callable] = []
        self.batch_timer = None
        
    def with_loading_indicator(self, message: str = "Loading...", show_spinner: bool = True):
        """
        Decorator to add loading indicator to functions.
        
        Args:
            message: Loading message
            show_spinner: Whether to show spinner
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with LoadingIndicator(message, show_spinner):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def with_progress_tracking(self, total_steps: int, description: str = "Processing"):
        """
        Decorator to add progress tracking to functions.
        
        Args:
            total_steps: Total number of steps
            description: Operation description
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                progress = ProgressTracker(total_steps, description)
                try:
                    result = func(progress, *args, **kwargs)
                    progress.complete("Complete")
                    return result
                except Exception as e:
                    progress.complete(f"Error: {str(e)}")
                    raise
            return wrapper
        return decorator
    
    def with_performance_monitoring(self, operation_name: str):
        """
        Decorator to monitor function performance.
        
        Args:
            operation_name: Name of the operation being monitored
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.monitor_operation(operation_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def monitor_operation(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Monitor the performance of an operation.
        
        Args:
            operation_name: Name of the operation
            func: Function to monitor
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
        """
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            memory_before=self.memory_optimizer.get_memory_usage().get("rss", 0)
        )
        
        try:
            result = func(*args, **kwargs)
            metrics.success = True
            return result
            
        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            raise
            
        finally:
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.memory_after = self.memory_optimizer.get_memory_usage().get("rss", 0)
            
            self.metrics.append(metrics)
            
            # Log performance info
            self.logger.logger.info(
                f"Operation '{operation_name}' completed in {metrics.duration:.3f}s "
                f"(success: {metrics.success})"
            )
            
            # Trigger cleanup if needed
            if self.memory_optimizer.should_cleanup():
                self.memory_optimizer.optimize_memory()
    
    def cache_function_result(self, cache_key: str, ttl: Optional[int] = None):
        """
        Decorator to cache function results.
        
        Args:
            cache_key: Key for caching (can include {args} placeholder)
            ttl: Time-to-live override
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = cache_key.format(args=str(args), kwargs=str(kwargs))
                
                # Try to get from cache
                cached_result = self.cache.get(key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.cache.set(key, result, ttl_override=ttl)
                
                return result
            return wrapper
        return decorator
    
    def optimize_file_operations(self, file_path: str, operation: str = "read") -> Any:
        """
        Optimize file I/O operations with caching.
        
        Args:
            file_path: Path to file
            operation: Type of operation ("read", "write", "stat")
            
        Returns:
            File operation result
        """
        cache_key = f"file_{operation}_{file_path}"
        
        if operation == "read":
            # Check cache first
            cached_content = self.file_cache.get(cache_key)
            if cached_content is not None:
                return cached_content
            
            # Read file and cache
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.file_cache.set(cache_key, content)
                return content
            except Exception as e:
                self.logger.logger.error(f"File read error for {file_path}: {e}")
                return None
        
        elif operation == "stat":
            cached_stat = self.file_cache.get(cache_key)
            if cached_stat is not None:
                return cached_stat
            
            try:
                stat_info = Path(file_path).stat()
                stat_dict = {
                    "size": stat_info.st_size,
                    "mtime": stat_info.st_mtime,
                    "exists": True
                }
                self.file_cache.set(cache_key, stat_dict, ttl_override=60)  # Short TTL for stat
                return stat_dict
            except Exception:
                return {"exists": False}
    
    def batch_file_operations(self, operations: List[Callable], delay: float = 0.1):
        """
        Batch multiple file operations for better performance.
        
        Args:
            operations: List of file operations to batch
            delay: Delay before executing batch
        """
        self.batch_operations.extend(operations)
        
        # Cancel existing timer
        if self.batch_timer:
            self.batch_timer.cancel()
        
        # Set new timer
        self.batch_timer = threading.Timer(delay, self._execute_batch_operations)
        self.batch_timer.start()
    
    def _execute_batch_operations(self):
        """Execute batched file operations."""
        if not self.batch_operations:
            return
        
        operations = self.batch_operations.copy()
        self.batch_operations.clear()
        
        with LoadingIndicator(f"Processing {len(operations)} operations..."):
            for operation in operations:
                try:
                    operation()
                except Exception as e:
                    self.logger.logger.error(f"Batch operation failed: {e}")
    
    def preload_user_data(self, user: User, background: bool = True) -> Optional[Future]:
        """
        Preload user data for better performance.
        
        Args:
            user: User object
            background: Whether to run in background
            
        Returns:
            Future object if background=True, None otherwise
        """
        def _preload():
            try:
                # Cache user profile
                profile_key = f"user_profile_{user.nickname}"
                self.cache.set(profile_key, user, ttl_override=1800)  # 30 minutes
                
                # Preload common file paths
                user_dir = Path("users") / user.nickname
                if user_dir.exists():
                    for file_path in user_dir.rglob("*.json"):
                        self.optimize_file_operations(str(file_path), "stat")
                
                self.logger.logger.info(f"User data preloaded for {user.nickname}")
                
            except Exception as e:
                self.logger.logger.error(f"Failed to preload user data: {e}")
        
        if background:
            return self.thread_pool.submit(_preload)
        else:
            _preload()
            return None
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Returns:
            Dictionary containing performance statistics
        """
        # Calculate operation statistics
        if self.metrics:
            durations = [m.duration for m in self.metrics if m.duration is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            success_rate = sum(1 for m in self.metrics if m.success) / len(self.metrics)
        else:
            avg_duration = max_duration = success_rate = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "operations": {
                "total_operations": len(self.metrics),
                "avg_duration": avg_duration,
                "max_duration": max_duration,
                "success_rate": success_rate
            },
            "cache": {
                "main_cache": self.cache.get_stats(),
                "file_cache": self.file_cache.get_stats()
            },
            "memory": self.memory_optimizer.get_memory_usage(),
            "thread_pool": {
                "active_threads": self.thread_pool._threads,
                "pending_tasks": self.thread_pool._work_queue.qsize()
            }
        }
    
    def cleanup_resources(self):
        """Clean up performance optimizer resources."""
        try:
            # Cancel batch timer
            if self.batch_timer:
                self.batch_timer.cancel()
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            # Clear caches
            self.cache.clear()
            self.file_cache.clear()
            
            # Force memory cleanup
            self.memory_optimizer.optimize_memory(force_gc=True)
            
            self.logger.logger.info("Performance optimizer resources cleaned up")
            
        except Exception as e:
            self.logger.logger.error(f"Error during cleanup: {e}")


# Global performance optimizer instance
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


# Convenience decorators using global instance
def with_loading(message: str = "Loading...", show_spinner: bool = True):
    """Convenience decorator for loading indicators."""
    return get_performance_optimizer().with_loading_indicator(message, show_spinner)


def with_progress(total_steps: int, description: str = "Processing"):
    """Convenience decorator for progress tracking."""
    return get_performance_optimizer().with_progress_tracking(total_steps, description)


def monitor_performance(operation_name: str):
    """Convenience decorator for performance monitoring."""
    return get_performance_optimizer().with_performance_monitoring(operation_name)


def cache_result(cache_key: str, ttl: Optional[int] = None):
    """Convenience decorator for result caching."""
    return get_performance_optimizer().cache_function_result(cache_key, ttl)