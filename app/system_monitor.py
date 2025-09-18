"""
System Health Monitoring for EchoVerse
Monitors system performance, resource usage, and component health
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import psutil
import os
from pathlib import Path

from defensive_system import get_defensive_logger, get_degradation_manager, SeverityLevel
from logging_config import log_performance_metrics


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    component: str
    operation: str
    duration: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """System resource usage snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    name: str
    status: str  # 'healthy', 'degraded', 'failed'
    last_check: datetime
    error_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    last_error: Optional[str] = None


class SystemMonitor:
    """Monitors system health and performance"""
    
    def __init__(self, max_metrics: int = 1000, monitoring_interval: int = 60):
        """
        Initialize system monitor
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
            monitoring_interval: Interval between system checks in seconds
        """
        self.logger = get_defensive_logger("system_monitor")
        self.degradation_manager = get_degradation_manager()
        
        self.max_metrics = max_metrics
        self.monitoring_interval = monitoring_interval
        
        # Performance tracking
        self.performance_metrics = deque(maxlen=max_metrics)
        self.resource_history = deque(maxlen=100)  # Keep last 100 resource snapshots
        
        # Component health tracking
        self.component_health = {}
        self.component_metrics = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Thresholds
        self.cpu_threshold = 80.0  # CPU usage percentage
        self.memory_threshold = 85.0  # Memory usage percentage
        self.disk_threshold = 90.0  # Disk usage percentage
        self.response_time_threshold = 5.0  # Response time in seconds
        
        self.logger.logger.info("System monitor initialized")
    
    def start_monitoring(self):
        """Start background system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop background system monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._check_system_health()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                self.logger.logger.error(f"Monitoring loop error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage for current directory
            disk = psutil.disk_usage('.')
            
            resource_usage = ResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_gb=disk.free / (1024 * 1024 * 1024)
            )
            
            self.resource_history.append(resource_usage)
            
        except Exception as e:
            self.logger.logger.warning(f"Failed to collect system metrics: {e}")
    
    def _check_system_health(self):
        """Check system health against thresholds"""
        if not self.resource_history:
            return
        
        latest = self.resource_history[-1]
        
        # Check CPU usage
        if latest.cpu_percent > self.cpu_threshold:
            self.degradation_manager.register_component_degradation(
                component="system_cpu",
                reason=f"High CPU usage: {latest.cpu_percent:.1f}%",
                impact="System may be slower than usual",
                severity=SeverityLevel.MEDIUM
            )
        
        # Check memory usage
        if latest.memory_percent > self.memory_threshold:
            self.degradation_manager.register_component_degradation(
                component="system_memory",
                reason=f"High memory usage: {latest.memory_percent:.1f}%",
                impact="System may run out of memory",
                severity=SeverityLevel.HIGH if latest.memory_percent > 95 else SeverityLevel.MEDIUM
            )
        
        # Check disk usage
        if latest.disk_usage_percent > self.disk_threshold:
            self.degradation_manager.register_component_degradation(
                component="system_disk",
                reason=f"Low disk space: {latest.disk_free_gb:.1f}GB free",
                impact="May not be able to save files",
                severity=SeverityLevel.HIGH
            )
    
    def record_performance_metric(self, component: str, operation: str, 
                                duration: float, success: bool, 
                                metadata: Dict[str, Any] = None):
        """
        Record a performance metric
        
        Args:
            component: Name of the component
            operation: Operation performed
            duration: Duration in seconds
            success: Whether the operation succeeded
            metadata: Additional metadata
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            component=component,
            operation=operation,
            duration=duration,
            success=success,
            metadata=metadata or {}
        )
        
        self.performance_metrics.append(metric)
        
        # Update component health
        self._update_component_health(component, duration, success, 
                                    None if success else metadata.get('error'))
        
        # Log performance metric
        log_performance_metrics(
            self.logger.logger, 
            f"{component}.{operation}", 
            duration,
            success=success,
            **metadata or {}
        )
        
        # Check for performance issues
        if duration > self.response_time_threshold:
            self.degradation_manager.register_component_degradation(
                component=component,
                reason=f"Slow response time: {duration:.2f}s for {operation}",
                impact="Operations may take longer than expected",
                severity=SeverityLevel.LOW
            )
    
    def _update_component_health(self, component: str, duration: float, 
                               success: bool, error: Optional[str]):
        """Update health status for a component"""
        if component not in self.component_health:
            self.component_health[component] = ComponentHealth(
                name=component,
                status='healthy',
                last_check=datetime.now()
            )
        
        health = self.component_health[component]
        health.last_check = datetime.now()
        
        if success:
            health.success_count += 1
        else:
            health.error_count += 1
            health.last_error = error
        
        # Update average response time
        total_operations = health.success_count + health.error_count
        if total_operations > 0:
            health.avg_response_time = (
                (health.avg_response_time * (total_operations - 1) + duration) / total_operations
            )
        
        # Determine health status
        if total_operations >= 10:  # Need minimum operations for assessment
            error_rate = health.error_count / total_operations
            
            if error_rate > 0.5:  # More than 50% errors
                health.status = 'failed'
            elif error_rate > 0.2 or health.avg_response_time > self.response_time_threshold:
                health.status = 'degraded'
            else:
                health.status = 'healthy'
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'resource_usage': None,
            'component_health': {},
            'performance_summary': {},
            'alerts': []
        }
        
        # Current resource usage
        if self.resource_history:
            latest_resources = self.resource_history[-1]
            report['resource_usage'] = {
                'cpu_percent': latest_resources.cpu_percent,
                'memory_percent': latest_resources.memory_percent,
                'memory_used_mb': latest_resources.memory_used_mb,
                'memory_available_mb': latest_resources.memory_available_mb,
                'disk_usage_percent': latest_resources.disk_usage_percent,
                'disk_free_gb': latest_resources.disk_free_gb
            }
            
            # Check for resource alerts
            if latest_resources.cpu_percent > self.cpu_threshold:
                report['alerts'].append(f"High CPU usage: {latest_resources.cpu_percent:.1f}%")
            if latest_resources.memory_percent > self.memory_threshold:
                report['alerts'].append(f"High memory usage: {latest_resources.memory_percent:.1f}%")
            if latest_resources.disk_usage_percent > self.disk_threshold:
                report['alerts'].append(f"Low disk space: {latest_resources.disk_free_gb:.1f}GB free")
        
        # Component health
        for component, health in self.component_health.items():
            report['component_health'][component] = {
                'status': health.status,
                'last_check': health.last_check.isoformat(),
                'error_count': health.error_count,
                'success_count': health.success_count,
                'avg_response_time': health.avg_response_time,
                'last_error': health.last_error
            }
            
            if health.status != 'healthy':
                report['overall_status'] = 'degraded'
                if health.status == 'failed':
                    report['alerts'].append(f"Component {component} has failed")
        
        # Performance summary
        if self.performance_metrics:
            recent_metrics = [m for m in self.performance_metrics 
                            if m.timestamp > datetime.now() - timedelta(hours=1)]
            
            if recent_metrics:
                total_operations = len(recent_metrics)
                successful_operations = sum(1 for m in recent_metrics if m.success)
                avg_duration = sum(m.duration for m in recent_metrics) / total_operations
                
                report['performance_summary'] = {
                    'total_operations_last_hour': total_operations,
                    'success_rate': successful_operations / total_operations,
                    'avg_response_time': avg_duration,
                    'operations_per_minute': total_operations / 60
                }
        
        return report
    
    def get_performance_metrics(self, component: Optional[str] = None, 
                              hours: int = 24) -> List[PerformanceMetric]:
        """
        Get performance metrics for analysis
        
        Args:
            component: Optional component filter
            hours: Number of hours to look back
            
        Returns:
            List of performance metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        metrics = [m for m in self.performance_metrics if m.timestamp > cutoff_time]
        
        if component:
            metrics = [m for m in metrics if m.component == component]
        
        return metrics
    
    def cleanup_old_metrics(self, days: int = 7):
        """Clean up old metrics to free memory"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # Clean performance metrics
        self.performance_metrics = deque(
            [m for m in self.performance_metrics if m.timestamp > cutoff_time],
            maxlen=self.max_metrics
        )
        
        # Clean resource history
        self.resource_history = deque(
            [r for r in self.resource_history if r.timestamp > cutoff_time],
            maxlen=100
        )
        
        self.logger.logger.info(f"Cleaned up metrics older than {days} days")


# Performance monitoring decorator
def monitor_performance(component: str, operation: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            success = False
            error_info = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_info = str(e)
                raise
            finally:
                duration = time.time() - start_time
                
                # Record metric if monitor is available
                try:
                    monitor = get_system_monitor()
                    monitor.record_performance_metric(
                        component=component,
                        operation=op_name,
                        duration=duration,
                        success=success,
                        metadata={'error': error_info} if error_info else {}
                    )
                except Exception:
                    # Silently fail if monitoring is not available
                    pass
        
        return wrapper
    return decorator


# Global monitor instance
_system_monitor = None


def get_system_monitor() -> SystemMonitor:
    """Get global system monitor instance"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def initialize_system_monitoring():
    """Initialize and start system monitoring"""
    monitor = get_system_monitor()
    monitor.start_monitoring()
    return monitor


def shutdown_system_monitoring():
    """Shutdown system monitoring"""
    global _system_monitor
    if _system_monitor:
        _system_monitor.stop_monitoring()
        _system_monitor = None