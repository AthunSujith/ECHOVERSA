"""
Tests for the Environment Checker module
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from app.environment_checker import (
    EnvironmentChecker, HardwareInfo, DependencyInfo, 
    EnvironmentReport, check_environment
)


class TestEnvironmentChecker(unittest.TestCase):
    """Test EnvironmentChecker functionality"""
    
    def setUp(self):
        self.checker = EnvironmentChecker()
    
    def test_hardware_detection(self):
        """Test hardware detection functionality"""
        hardware = self.checker.check_hardware()
        
        self.assertIsInstance(hardware, HardwareInfo)
        self.assertGreater(hardware.cpu_count, 0)
        self.assertGreater(hardware.total_ram_gb, 0)
        self.assertGreater(hardware.available_ram_gb, 0)
        self.assertIsInstance(hardware.has_gpu, bool)
        self.assertIsInstance(hardware.gpu_count, int)
        self.assertIsInstance(hardware.gpu_names, list)
        self.assertIsNotNone(hardware.platform)
        self.assertIsNotNone(hardware.architecture)
    
    @patch('importlib.import_module')
    @patch('importlib.util.find_spec')
    def test_dependency_checking(self, mock_find_spec, mock_import):
        """Test dependency checking with mocked imports"""
        # Mock successful import
        mock_find_spec.return_value = MagicMock()
        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0"
        mock_import.return_value = mock_module
        
        dependencies = self.checker.check_dependencies()
        
        self.assertIsInstance(dependencies, list)
        self.assertGreater(len(dependencies), 0)
        
        # Check that all expected dependencies are checked
        dep_names = [dep.name for dep in dependencies]
        for required_dep in self.checker.REQUIRED_DEPENDENCIES:
            self.assertIn(required_dep, dep_names)
    
    @patch('importlib.util.find_spec')
    def test_missing_dependency(self, mock_find_spec):
        """Test handling of missing dependencies"""
        mock_find_spec.return_value = None
        
        dep_info = self.checker._check_single_dependency("nonexistent_package")
        
        self.assertIsInstance(dep_info, DependencyInfo)
        self.assertEqual(dep_info.name, "nonexistent_package")
        self.assertFalse(dep_info.available)
        self.assertIsNone(dep_info.version)
        self.assertIsNotNone(dep_info.import_error)
    
    @patch('subprocess.run')
    def test_ffmpeg_detection_available(self, mock_run):
        """Test FFmpeg detection when available"""
        # Mock successful ffmpeg call
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.0"
        mock_run.return_value = mock_result
        
        available, path = self.checker.check_ffmpeg()
        
        self.assertTrue(available)
        # Path detection might fail in test environment, so we don't assert on it
    
    @patch('subprocess.run')
    def test_ffmpeg_detection_unavailable(self, mock_run):
        """Test FFmpeg detection when unavailable"""
        # Mock failed ffmpeg call
        mock_run.side_effect = FileNotFoundError()
        
        available, path = self.checker.check_ffmpeg()
        
        self.assertFalse(available)
        self.assertIsNone(path)
    
    def test_report_generation(self):
        """Test complete environment report generation"""
        report = self.checker.generate_report()
        
        self.assertIsInstance(report, EnvironmentReport)
        self.assertIsInstance(report.hardware, HardwareInfo)
        self.assertIsInstance(report.dependencies, list)
        self.assertIsInstance(report.ffmpeg_available, bool)
        self.assertIsInstance(report.python_version, str)
        self.assertIsInstance(report.recommendations, list)
        self.assertIsInstance(report.warnings, list)
        self.assertIsInstance(report.errors, list)
    
    def test_gpu_detection_with_torch(self):
        """Test GPU detection with PyTorch available"""
        with patch('app.environment_checker.importlib.import_module') as mock_import:
            # Mock PyTorch module
            mock_torch = MagicMock()
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.device_count.return_value = 1
            mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 3080"
            
            # Mock device properties
            mock_props = MagicMock()
            mock_props.total_memory = 10 * 1024**3  # 10GB
            mock_torch.cuda.get_device_properties.return_value = mock_props
            mock_torch.cuda.memory_allocated.return_value = 1 * 1024**3  # 1GB allocated
            mock_torch.cuda.empty_cache = MagicMock()
            
            mock_import.return_value = mock_torch
            
            has_gpu, gpu_count, gpu_names, total_vram_gb, available_vram_gb = self.checker._detect_gpu()
            
            self.assertTrue(has_gpu)
            self.assertEqual(gpu_count, 1)
            self.assertEqual(gpu_names, ["NVIDIA GeForce RTX 3080"])
            self.assertAlmostEqual(total_vram_gb, 10.0, places=1)
            self.assertAlmostEqual(available_vram_gb, 9.0, places=1)
    
    def test_gpu_detection_no_torch(self):
        """Test GPU detection without PyTorch"""
        with patch('importlib.import_module', side_effect=ImportError("No module named 'torch'")):
            has_gpu, gpu_count, gpu_names, total_vram_gb, available_vram_gb = self.checker._detect_gpu()
            
            # Without PyTorch, should fall back to no GPU detection
            # (unless GPUtil is available, but we're not mocking that here)
            self.assertIsInstance(has_gpu, bool)
            self.assertIsInstance(gpu_count, int)
            self.assertIsInstance(gpu_names, list)
    
    def test_print_report(self):
        """Test report printing (basic functionality)"""
        # This test mainly ensures the method doesn't crash
        # Actual output testing would require capturing stdout
        report = self.checker.generate_report()
        
        try:
            self.checker.print_report(report)
        except Exception as e:
            self.fail(f"print_report raised an exception: {e}")
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # Test check_environment function
        report = check_environment()
        self.assertIsInstance(report, EnvironmentReport)


class TestHardwareInfo(unittest.TestCase):
    """Test HardwareInfo dataclass"""
    
    def test_hardware_info_creation(self):
        """Test HardwareInfo dataclass creation"""
        hardware = HardwareInfo(
            cpu_count=8,
            cpu_model="Test CPU",
            total_ram_gb=16.0,
            available_ram_gb=12.0,
            has_gpu=True,
            gpu_count=1,
            gpu_names=["Test GPU"],
            total_vram_gb=8.0,
            available_vram_gb=6.0,
            platform="Linux",
            architecture="x86_64"
        )
        
        self.assertEqual(hardware.cpu_count, 8)
        self.assertEqual(hardware.cpu_model, "Test CPU")
        self.assertEqual(hardware.total_ram_gb, 16.0)
        self.assertTrue(hardware.has_gpu)


class TestDependencyInfo(unittest.TestCase):
    """Test DependencyInfo dataclass"""
    
    def test_dependency_info_creation(self):
        """Test DependencyInfo dataclass creation"""
        dep = DependencyInfo(
            name="test_package",
            available=True,
            version="1.0.0",
            import_error=None
        )
        
        self.assertEqual(dep.name, "test_package")
        self.assertTrue(dep.available)
        self.assertEqual(dep.version, "1.0.0")
        self.assertIsNone(dep.import_error)


if __name__ == '__main__':
    unittest.main()