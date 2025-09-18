"""
Comprehensive unit tests for defensive programming system.
Tests graceful degradation, error handling, and fallback mechanisms.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from defensive_system import (
        DefensiveSystem, DependencyChecker, GracefulDegradation,
        ErrorHandler, FallbackManager
    )
    from error_handlers import (
        handle_api_failure, handle_missing_dependency, handle_storage_error,
        log_error, create_error_context
    )
    from logging_config import setup_logging, get_logger
    DEFENSIVE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Defensive system modules not available: {e}")
    DEFENSIVE_MODULES_AVAILABLE = False


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestDefensiveSystem(unittest.TestCase):
    """Test cases for DefensiveSystem main class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.defensive_system = DefensiveSystem()
    
    def test_initialization(self):
        """Test DefensiveSystem initialization"""
        self.assertIsNotNone(self.defensive_system)
        self.assertIsNotNone(self.defensive_system.dependency_checker)
        self.assertIsNotNone(self.defensive_system.graceful_degradation)
        self.assertIsNotNone(self.defensive_system.error_handler)
        self.assertIsNotNone(self.defensive_system.fallback_manager)
    
    def test_check_dependencies(self):
        """Test dependency checking"""
        deps = self.defensive_system.check_dependencies()
        
        self.assertIsInstance(deps, dict)
        
        # Should check core dependencies
        expected_deps = [
            "streamlit", "torch", "transformers", "numpy", 
            "pyttsx3", "requests", "pydub", "whisper"
        ]
        
        for dep in expected_deps:
            self.assertIn(dep, deps)
            self.assertIsInstance(deps[dep], dict)
            self.assertIn("available", deps[dep])
            self.assertIn("version", deps[dep])
            self.assertIsInstance(deps[dep]["available"], bool)
    
    def test_get_degradation_status(self):
        """Test getting degradation status"""
        status = self.defensive_system.get_degradation_status()
        
        self.assertIsInstance(status, dict)
        
        # Should have status for major features
        expected_features = [
            "content_generation", "audio_processing", "speech_synthesis",
            "audio_transcription", "model_management"
        ]
        
        for feature in expected_features:
            if feature in status:
                self.assertIsInstance(status[feature], dict)
                self.assertIn("available", status[feature])
                self.assertIn("fallback_active", status[feature])
    
    def test_enable_graceful_mode(self):
        """Test enabling graceful degradation mode"""
        # Test enabling graceful mode
        self.defensive_system.enable_graceful_mode()
        
        status = self.defensive_system.get_degradation_status()
        self.assertTrue(status.get("graceful_mode_enabled", False))
        
        # Test disabling graceful mode
        self.defensive_system.disable_graceful_mode()
        
        status = self.defensive_system.get_degradation_status()
        self.assertFalse(status.get("graceful_mode_enabled", False))
    
    def test_get_system_health(self):
        """Test system health reporting"""
        health = self.defensive_system.get_system_health()
        
        self.assertIsInstance(health, dict)
        self.assertIn("overall_status", health)
        self.assertIn("critical_failures", health)
        self.assertIn("warnings", health)
        self.assertIn("available_features", health)
        
        # Overall status should be a string
        self.assertIsInstance(health["overall_status"], str)
        self.assertIn(health["overall_status"], ["healthy", "degraded", "critical"])
        
        # Lists should be lists
        self.assertIsInstance(health["critical_failures"], list)
        self.assertIsInstance(health["warnings"], list)
        self.assertIsInstance(health["available_features"], list)


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestDependencyChecker(unittest.TestCase):
    """Test cases for DependencyChecker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.dependency_checker = DependencyChecker()
    
    def test_check_dependency_available(self):
        """Test checking if dependency is available"""
        # Test with known available dependency
        numpy_available = self.dependency_checker.is_dependency_available("numpy")
        self.assertIsInstance(numpy_available, bool)
        
        # Test with known unavailable dependency
        fake_available = self.dependency_checker.is_dependency_available("fake_nonexistent_package")
        self.assertFalse(fake_available)
    
    def test_get_dependency_version(self):
        """Test getting dependency version"""
        # Test with numpy (should be available)
        numpy_version = self.dependency_checker.get_dependency_version("numpy")
        if numpy_version:
            self.assertIsInstance(numpy_version, str)
            self.assertGreater(len(numpy_version), 0)
        
        # Test with nonexistent package
        fake_version = self.dependency_checker.get_dependency_version("fake_nonexistent_package")
        self.assertIsNone(fake_version)
    
    def test_check_all_dependencies(self):
        """Test checking all dependencies"""
        all_deps = self.dependency_checker.check_all_dependencies()
        
        self.assertIsInstance(all_deps, dict)
        self.assertGreater(len(all_deps), 0)
        
        # Each dependency should have proper structure
        for dep_name, dep_info in all_deps.items():
            self.assertIsInstance(dep_name, str)
            self.assertIsInstance(dep_info, dict)
            self.assertIn("available", dep_info)
            self.assertIn("version", dep_info)
            self.assertIn("critical", dep_info)
    
    def test_get_missing_critical_dependencies(self):
        """Test getting missing critical dependencies"""
        missing = self.dependency_checker.get_missing_critical_dependencies()
        
        self.assertIsInstance(missing, list)
        
        # Each missing dependency should be a string
        for dep in missing:
            self.assertIsInstance(dep, str)
    
    def test_get_dependency_alternatives(self):
        """Test getting dependency alternatives"""
        # Test with a dependency that has alternatives
        alternatives = self.dependency_checker.get_dependency_alternatives("pydub")
        
        if alternatives:
            self.assertIsInstance(alternatives, list)
            for alt in alternatives:
                self.assertIsInstance(alt, str)


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestGracefulDegradation(unittest.TestCase):
    """Test cases for GracefulDegradation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.graceful_degradation = GracefulDegradation()
    
    def test_register_fallback(self):
        """Test registering fallback functions"""
        def mock_primary():
            return "primary"
        
        def mock_fallback():
            return "fallback"
        
        # Register fallback
        self.graceful_degradation.register_fallback("test_feature", mock_primary, mock_fallback)
        
        # Verify registration
        self.assertIn("test_feature", self.graceful_degradation.fallbacks)
        
        fallback_info = self.graceful_degradation.fallbacks["test_feature"]
        self.assertEqual(fallback_info["primary"], mock_primary)
        self.assertEqual(fallback_info["fallback"], mock_fallback)
    
    def test_execute_with_fallback(self):
        """Test executing function with fallback"""
        def working_function():
            return "success"
        
        def failing_function():
            raise Exception("Primary function failed")
        
        def fallback_function():
            return "fallback_success"
        
        # Test successful execution
        result = self.graceful_degradation.execute_with_fallback(
            "test_success", working_function, fallback_function
        )
        self.assertEqual(result, "success")
        
        # Test fallback execution
        result = self.graceful_degradation.execute_with_fallback(
            "test_fallback", failing_function, fallback_function
        )
        self.assertEqual(result, "fallback_success")
    
    def test_is_feature_degraded(self):
        """Test checking if feature is degraded"""
        def failing_function():
            raise Exception("Always fails")
        
        def fallback_function():
            return "fallback"
        
        # Execute with fallback to trigger degradation
        self.graceful_degradation.execute_with_fallback(
            "test_degraded", failing_function, fallback_function
        )
        
        # Check if feature is marked as degraded
        is_degraded = self.graceful_degradation.is_feature_degraded("test_degraded")
        self.assertTrue(is_degraded)
        
        # Check non-existent feature
        is_degraded = self.graceful_degradation.is_feature_degraded("nonexistent")
        self.assertFalse(is_degraded)
    
    def test_get_degradation_report(self):
        """Test getting degradation report"""
        report = self.graceful_degradation.get_degradation_report()
        
        self.assertIsInstance(report, dict)
        self.assertIn("degraded_features", report)
        self.assertIn("total_features", report)
        self.assertIn("degradation_rate", report)
        
        self.assertIsInstance(report["degraded_features"], list)
        self.assertIsInstance(report["total_features"], int)
        self.assertIsInstance(report["degradation_rate"], float)


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_handle_error(self):
        """Test error handling"""
        test_error = Exception("Test error")
        context = {"operation": "test", "user": "testuser"}
        
        # Handle error
        result = self.error_handler.handle_error(test_error, context)
        
        self.assertIsInstance(result, dict)
        self.assertIn("error_id", result)
        self.assertIn("handled", result)
        self.assertIn("recovery_action", result)
        
        self.assertTrue(result["handled"])
        self.assertIsInstance(result["error_id"], str)
    
    def test_get_error_statistics(self):
        """Test getting error statistics"""
        # Generate some test errors
        for i in range(3):
            test_error = Exception(f"Test error {i}")
            self.error_handler.handle_error(test_error, {"test": i})
        
        stats = self.error_handler.get_error_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn("total_errors", stats)
        self.assertIn("error_types", stats)
        self.assertIn("recent_errors", stats)
        
        self.assertGreaterEqual(stats["total_errors"], 3)
        self.assertIsInstance(stats["error_types"], dict)
        self.assertIsInstance(stats["recent_errors"], list)
    
    def test_clear_error_history(self):
        """Test clearing error history"""
        # Generate test error
        test_error = Exception("Test error")
        self.error_handler.handle_error(test_error, {})
        
        # Verify error was recorded
        stats_before = self.error_handler.get_error_statistics()
        self.assertGreater(stats_before["total_errors"], 0)
        
        # Clear history
        self.error_handler.clear_error_history()
        
        # Verify history was cleared
        stats_after = self.error_handler.get_error_statistics()
        self.assertEqual(stats_after["total_errors"], 0)


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestFallbackManager(unittest.TestCase):
    """Test cases for FallbackManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fallback_manager = FallbackManager()
    
    def test_register_service_fallback(self):
        """Test registering service fallbacks"""
        def primary_service():
            return "primary"
        
        def fallback_service():
            return "fallback"
        
        # Register fallback
        self.fallback_manager.register_service_fallback(
            "test_service", primary_service, fallback_service
        )
        
        # Verify registration
        self.assertIn("test_service", self.fallback_manager.services)
    
    def test_get_service(self):
        """Test getting service with fallback"""
        def working_service():
            return "working"
        
        def failing_service():
            raise Exception("Service failed")
        
        def fallback_service():
            return "fallback"
        
        # Register working service
        self.fallback_manager.register_service_fallback(
            "working_service", working_service, fallback_service
        )
        
        # Register failing service
        self.fallback_manager.register_service_fallback(
            "failing_service", failing_service, fallback_service
        )
        
        # Test working service
        result = self.fallback_manager.get_service("working_service")()
        self.assertEqual(result, "working")
        
        # Test failing service (should use fallback)
        result = self.fallback_manager.get_service("failing_service")()
        self.assertEqual(result, "fallback")
    
    def test_get_service_status(self):
        """Test getting service status"""
        def working_service():
            return "working"
        
        def fallback_service():
            return "fallback"
        
        # Register service
        self.fallback_manager.register_service_fallback(
            "test_service", working_service, fallback_service
        )
        
        # Get service to establish status
        self.fallback_manager.get_service("test_service")()
        
        # Check status
        status = self.fallback_manager.get_service_status("test_service")
        
        self.assertIsInstance(status, dict)
        self.assertIn("available", status)
        self.assertIn("using_fallback", status)
        self.assertIn("last_error", status)


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestErrorHandlers(unittest.TestCase):
    """Test cases for error handling functions"""
    
    def test_handle_api_failure(self):
        """Test API failure handling"""
        def failing_api():
            raise Exception("API Error")
        
        def fallback_api():
            return "fallback_result"
        
        result = handle_api_failure("test_api", failing_api, fallback_api)
        self.assertEqual(result, "fallback_result")
    
    def test_handle_missing_dependency(self):
        """Test missing dependency handling"""
        result = handle_missing_dependency("fake_package")
        
        self.assertIsInstance(result, dict)
        self.assertIn("handled", result)
        self.assertIn("feature_disabled", result)
        self.assertIn("message", result)
        
        self.assertTrue(result["handled"])
        self.assertTrue(result["feature_disabled"])
    
    def test_handle_storage_error(self):
        """Test storage error handling"""
        def failing_storage():
            raise PermissionError("Cannot write to disk")
        
        result = handle_storage_error("save_file", failing_storage)
        
        self.assertIsInstance(result, dict)
        self.assertIn("handled", result)
        self.assertIn("fallback_used", result)
        self.assertIn("error_type", result)
    
    def test_create_error_context(self):
        """Test error context creation"""
        context = create_error_context(
            operation="test_operation",
            user="testuser",
            additional_data={"key": "value"}
        )
        
        self.assertIsInstance(context, dict)
        self.assertIn("operation", context)
        self.assertIn("user", context)
        self.assertIn("timestamp", context)
        self.assertIn("key", context)
        
        self.assertEqual(context["operation"], "test_operation")
        self.assertEqual(context["user"], "testuser")
        self.assertEqual(context["key"], "value")


@unittest.skipUnless(DEFENSIVE_MODULES_AVAILABLE, "Defensive system modules not available")
class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_logging(self):
        """Test logging setup"""
        logger = setup_logging(
            log_level="INFO",
            log_file=self.log_file,
            console_output=True
        )
        
        self.assertIsNotNone(logger)
        
        # Test logging
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Verify log file was created
        self.assertTrue(os.path.exists(self.log_file))
        
        # Verify log content
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Test info message", log_content)
        self.assertIn("Test warning message", log_content)
        self.assertIn("Test error message", log_content)
    
    def test_get_logger(self):
        """Test getting logger instance"""
        # Setup logging first
        setup_logging(log_file=self.log_file)
        
        # Get logger
        logger = get_logger("test_module")
        
        self.assertIsNotNone(logger)
        
        # Test logging with module name
        logger.info("Test message from module")
        
        # Verify log content includes module name
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("test_module", log_content)
        self.assertIn("Test message from module", log_content)


class TestDefensiveSystemIntegration(unittest.TestCase):
    """Integration tests for defensive system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        if not DEFENSIVE_MODULES_AVAILABLE:
            self.skipTest("Defensive system modules not available")
        
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "integration_test.log")
        
        # Setup logging for integration tests
        setup_logging(log_file=self.log_file, log_level="DEBUG")
        
        self.defensive_system = DefensiveSystem()
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_defensive_workflow(self):
        """Test complete defensive system workflow"""
        # 1. Check system health
        health = self.defensive_system.get_system_health()
        self.assertIsInstance(health, dict)
        
        # 2. Check dependencies
        deps = self.defensive_system.check_dependencies()
        self.assertIsInstance(deps, dict)
        
        # 3. Enable graceful mode
        self.defensive_system.enable_graceful_mode()
        
        # 4. Test fallback execution
        def failing_function():
            raise Exception("Intentional failure for testing")
        
        def fallback_function():
            return "fallback_executed"
        
        result = self.defensive_system.graceful_degradation.execute_with_fallback(
            "integration_test", failing_function, fallback_function
        )
        
        self.assertEqual(result, "fallback_executed")
        
        # 5. Check degradation status
        status = self.defensive_system.get_degradation_status()
        self.assertTrue(status.get("graceful_mode_enabled", False))
        
        # 6. Verify error was logged
        self.assertTrue(os.path.exists(self.log_file))
        
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("integration_test", log_content)
    
    def test_error_recovery_workflow(self):
        """Test error recovery workflow"""
        # Simulate various error conditions
        error_scenarios = [
            (ImportError("Missing dependency"), "dependency_error"),
            (ConnectionError("API unavailable"), "api_error"),
            (PermissionError("Storage access denied"), "storage_error"),
            (MemoryError("Out of memory"), "memory_error")
        ]
        
        for error, error_type in error_scenarios:
            context = create_error_context(
                operation=f"test_{error_type}",
                error_type=error_type
            )
            
            result = self.defensive_system.error_handler.handle_error(error, context)
            
            self.assertIsInstance(result, dict)
            self.assertTrue(result.get("handled", False))
            self.assertIn("recovery_action", result)
        
        # Check error statistics
        stats = self.defensive_system.error_handler.get_error_statistics()
        self.assertGreaterEqual(stats["total_errors"], len(error_scenarios))
    
    def test_service_fallback_workflow(self):
        """Test service fallback workflow"""
        # Register multiple services with fallbacks
        services = {
            "content_generation": {
                "primary": lambda: "gemini_content",
                "fallback": lambda: "mock_content"
            },
            "audio_synthesis": {
                "primary": lambda: "elevenlabs_audio",
                "fallback": lambda: "pyttsx3_audio"
            },
            "model_loading": {
                "primary": lambda: "gpu_model",
                "fallback": lambda: "cpu_model"
            }
        }
        
        # Register all services
        for service_name, service_funcs in services.items():
            self.defensive_system.fallback_manager.register_service_fallback(
                service_name, service_funcs["primary"], service_funcs["fallback"]
            )
        
        # Test each service
        for service_name in services.keys():
            service_func = self.defensive_system.fallback_manager.get_service(service_name)
            result = service_func()
            
            self.assertIsNotNone(result)
            self.assertIsInstance(result, str)
            
            # Check service status
            status = self.defensive_system.fallback_manager.get_service_status(service_name)
            self.assertIsInstance(status, dict)
            self.assertIn("available", status)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)