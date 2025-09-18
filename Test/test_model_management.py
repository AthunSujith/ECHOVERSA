"""
Comprehensive unit tests for local model management system.
Tests model registry, selector, downloader, and access control.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from model_manager import (
        ModelRegistry, ModelSpec, ModelType, QuantizationType, 
        HardwareRequirement, get_model_registry, get_model_spec
    )
    from model_selector import (
        ModelSelector, ModelSelectionCriteria, SelectionStrategy, ModelCandidate
    )
    from model_downloader import ModelDownloader
    from model_access_control import AccessControlManager
    from environment_checker import EnvironmentChecker, HardwareInfo, check_environment
    MODEL_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Model management modules not available: {e}")
    MODEL_MODULES_AVAILABLE = False


@unittest.skipUnless(MODEL_MODULES_AVAILABLE, "Model management modules not available")
class TestModelRegistry(unittest.TestCase):
    """Test cases for ModelRegistry"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = ModelRegistry()
    
    def test_initialization(self):
        """Test registry initialization"""
        self.assertIsNotNone(self.registry)
        models = self.registry.get_all_models()
        self.assertIsInstance(models, dict)
        self.assertGreater(len(models), 0, "Registry should contain models")
    
    def test_get_model(self):
        """Test getting specific model"""
        # Test existing model
        gpt2_model = self.registry.get_model("gpt2")
        self.assertIsNotNone(gpt2_model)
        self.assertIsInstance(gpt2_model, ModelSpec)
        self.assertEqual(gpt2_model.name, "gpt2")
        self.assertEqual(gpt2_model.model_type, ModelType.GPT2)
        
        # Test non-existing model
        nonexistent = self.registry.get_model("nonexistent-model")
        self.assertIsNone(nonexistent)
    
    def test_get_models_by_type(self):
        """Test filtering models by type"""
        gpt2_models = self.registry.get_models_by_type(ModelType.GPT2)
        self.assertIsInstance(gpt2_models, dict)
        
        for model_spec in gpt2_models.values():
            self.assertEqual(model_spec.model_type, ModelType.GPT2)
        
        # Test with type that might not exist
        nonexistent_type_models = self.registry.get_models_by_type(ModelType.LLAMA)
        self.assertIsInstance(nonexistent_type_models, dict)
    
    def test_get_cpu_compatible_models(self):
        """Test getting CPU-compatible models"""
        cpu_models = self.registry.get_cpu_compatible_models()
        self.assertIsInstance(cpu_models, dict)
        self.assertGreater(len(cpu_models), 0, "Should have CPU-compatible models")
        
        for model_spec in cpu_models.values():
            self.assertTrue(model_spec.is_cpu_compatible, 
                          f"Model {model_spec.name} should be CPU compatible")
    
    def test_get_models_by_size_range(self):
        """Test filtering models by size"""
        # Test small models (under 2GB)
        small_models = self.registry.get_models_by_size_range(0, 2.0)
        self.assertIsInstance(small_models, dict)
        
        for model_spec in small_models.values():
            self.assertLessEqual(model_spec.size_gb, 2.0)
        
        # Test large models (over 10GB)
        large_models = self.registry.get_models_by_size_range(10.0, float('inf'))
        self.assertIsInstance(large_models, dict)
        
        for model_spec in large_models.values():
            self.assertGreaterEqual(model_spec.size_gb, 10.0)
    
    def test_get_recommended_models_for_hardware(self):
        """Test hardware-based model recommendations"""
        # Test high-end GPU system
        gpu_recommendations = self.registry.get_recommended_models_for_hardware(
            has_gpu=True, vram_gb=24, ram_gb=32
        )
        self.assertIsInstance(gpu_recommendations, list)
        
        # Test CPU-only system
        cpu_recommendations = self.registry.get_recommended_models_for_hardware(
            has_gpu=False, vram_gb=None, ram_gb=16
        )
        self.assertIsInstance(cpu_recommendations, list)
        
        # Verify CPU recommendations are CPU-compatible
        for model_spec in cpu_recommendations:
            self.assertTrue(model_spec.is_cpu_compatible or not model_spec.requires_gpu)
        
        # Test low-resource system
        low_resource_recommendations = self.registry.get_recommended_models_for_hardware(
            has_gpu=False, vram_gb=None, ram_gb=4
        )
        self.assertIsInstance(low_resource_recommendations, list)
        
        # Should recommend smaller models for low-resource systems
        for model_spec in low_resource_recommendations:
            self.assertLessEqual(model_spec.min_ram_gb, 4)
    
    def test_model_spec_properties(self):
        """Test ModelSpec properties and validation"""
        gpt2_model = self.registry.get_model("gpt2")
        self.assertIsNotNone(gpt2_model)
        
        # Test basic properties
        self.assertIsInstance(gpt2_model.name, str)
        self.assertIsInstance(gpt2_model.size_gb, (int, float))
        self.assertIsInstance(gpt2_model.min_ram_gb, int)
        self.assertIsInstance(gpt2_model.quality_score, int)
        self.assertIsInstance(gpt2_model.speed_score, int)
        
        # Test score ranges
        self.assertGreaterEqual(gpt2_model.quality_score, 1)
        self.assertLessEqual(gpt2_model.quality_score, 10)
        self.assertGreaterEqual(gpt2_model.speed_score, 1)
        self.assertLessEqual(gpt2_model.speed_score, 10)
        
        # Test CPU compatibility logic
        if gpt2_model.hardware_req == HardwareRequirement.CPU_ONLY:
            self.assertTrue(gpt2_model.is_cpu_compatible)
            self.assertFalse(gpt2_model.requires_gpu)


@unittest.skipUnless(MODEL_MODULES_AVAILABLE, "Model management modules not available")
class TestModelSelector(unittest.TestCase):
    """Test cases for ModelSelector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "models")
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.selector = ModelSelector(
            cache_dir=self.cache_dir,
            config_dir=self.config_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ModelSelector initialization"""
        self.assertIsNotNone(self.selector)
        self.assertIsNotNone(self.selector.registry)
        self.assertIsNotNone(self.selector.user_preferences)
        self.assertIsInstance(self.selector.selection_history, list)
    
    def test_preferences_management(self):
        """Test user preferences loading and saving"""
        # Test default preferences
        self.assertIn("strategy", self.selector.user_preferences)
        self.assertIn("prefer_quantized", self.selector.user_preferences)
        
        # Test updating preferences
        self.selector.update_preferences(
            strategy="quality_first",
            max_size_gb=5.0,
            prefer_quantized=False
        )
        
        self.assertEqual(self.selector.user_preferences["strategy"], "quality_first")
        self.assertEqual(self.selector.user_preferences["max_size_gb"], 5.0)
        self.assertFalse(self.selector.user_preferences["prefer_quantized"])
    
    @patch('model_selector.check_environment')
    def test_get_model_candidates(self, mock_check_env):
        """Test getting model candidates"""
        # Mock environment
        mock_env = Mock()
        mock_env.hardware = Mock()
        mock_env.hardware.has_gpu = True
        mock_env.hardware.total_vram_gb = 8.0
        mock_env.hardware.available_ram_gb = 16.0
        mock_env.dependencies = [
            Mock(name="torch", available=True),
            Mock(name="transformers", available=True),
            Mock(name="accelerate", available=True)
        ]
        mock_check_env.return_value = mock_env
        
        # Test with basic criteria
        criteria = ModelSelectionCriteria(
            strategy=SelectionStrategy.BALANCED,
            max_size_gb=10.0
        )
        
        candidates = self.selector.get_model_candidates(criteria)
        
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0, "Should have model candidates")
        
        # Verify candidate structure
        for candidate in candidates:
            self.assertIsInstance(candidate, ModelCandidate)
            self.assertIsInstance(candidate.model_spec, ModelSpec)
            self.assertIsInstance(candidate.compatibility_score, (int, float))
            self.assertIsInstance(candidate.selection_score, (int, float))
            self.assertIsInstance(candidate.is_downloaded, bool)
            
            # Verify size constraint
            self.assertLessEqual(candidate.model_spec.size_gb, 10.0)
        
        # Verify candidates are sorted by selection score
        scores = [c.selection_score for c in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    @patch('model_selector.check_environment')
    def test_select_best_model(self, mock_check_env):
        """Test selecting the best model"""
        # Mock environment
        mock_env = Mock()
        mock_env.hardware = Mock()
        mock_env.hardware.has_gpu = False
        mock_env.hardware.total_vram_gb = None
        mock_env.hardware.available_ram_gb = 8.0
        mock_env.dependencies = [
            Mock(name="torch", available=True),
            Mock(name="transformers", available=True)
        ]
        mock_check_env.return_value = mock_env
        
        # Test selection
        criteria = ModelSelectionCriteria(
            strategy=SelectionStrategy.MINIMAL_RESOURCES,
            max_size_gb=5.0
        )
        
        best_candidate = self.selector.select_best_model(criteria)
        
        if best_candidate:  # May be None if no suitable models
            self.assertIsInstance(best_candidate, ModelCandidate)
            self.assertLessEqual(best_candidate.model_spec.size_gb, 5.0)
            
            # Should prefer CPU-compatible models for CPU-only system
            self.assertTrue(best_candidate.model_spec.is_cpu_compatible or 
                          not best_candidate.model_spec.requires_gpu)
            
            # Verify selection was recorded
            self.assertGreater(len(self.selector.selection_history), 0)
            last_selection = self.selector.selection_history[-1]
            self.assertEqual(last_selection["model_name"], best_candidate.model_spec.name)
    
    def test_get_fallback_hierarchy(self):
        """Test fallback hierarchy generation"""
        hierarchy = self.selector.get_fallback_hierarchy()
        
        self.assertIsInstance(hierarchy, list)
        self.assertGreater(len(hierarchy), 0, "Should have fallback models")
        
        # Should end with mock generator
        self.assertEqual(hierarchy[-1], "mock")
        
        # Should contain GPT-2 as a fallback
        self.assertIn("gpt2", hierarchy)
    
    def test_get_model_recommendations(self):
        """Test getting model recommendations with explanations"""
        recommendations = self.selector.get_model_recommendations(count=3)
        
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 3)
        
        for candidate, explanation in recommendations:
            self.assertIsInstance(candidate, ModelCandidate)
            self.assertIsInstance(explanation, str)
            self.assertGreater(len(explanation), 0)
            
            # Explanation should contain useful information
            self.assertTrue(any(keyword in explanation.lower() 
                              for keyword in ["quality", "speed", "hardware", "download"]))


@unittest.skipUnless(MODEL_MODULES_AVAILABLE, "Model management modules not available")
class TestModelDownloader(unittest.TestCase):
    """Test cases for ModelDownloader"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "models")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.downloader = ModelDownloader(cache_dir=self.cache_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ModelDownloader initialization"""
        self.assertIsNotNone(self.downloader)
        self.assertEqual(self.downloader.cache_dir, self.cache_dir)
        self.assertTrue(os.path.exists(self.cache_dir))
    
    def test_list_downloaded_models(self):
        """Test listing downloaded models"""
        # Initially should be empty
        downloaded = self.downloader.list_downloaded_models()
        self.assertIsInstance(downloaded, list)
        self.assertEqual(len(downloaded), 0)
        
        # Create fake model directory
        fake_model_dir = os.path.join(self.cache_dir, "fake-model")
        os.makedirs(fake_model_dir)
        
        # Create some fake model files
        with open(os.path.join(fake_model_dir, "config.json"), 'w') as f:
            json.dump({"model_type": "test"}, f)
        
        with open(os.path.join(fake_model_dir, "pytorch_model.bin"), 'w') as f:
            f.write("fake model data")
        
        # Should now detect the fake model
        downloaded = self.downloader.list_downloaded_models()
        self.assertIn("fake-model", downloaded)
    
    def test_get_model_path(self):
        """Test getting model path"""
        model_name = "test-model"
        expected_path = os.path.join(self.cache_dir, "test-model")
        
        actual_path = self.downloader.get_model_path(model_name)
        self.assertEqual(actual_path, expected_path)
    
    def test_is_model_downloaded(self):
        """Test checking if model is downloaded"""
        model_name = "test-model"
        
        # Initially should not be downloaded
        self.assertFalse(self.downloader.is_model_downloaded(model_name))
        
        # Create model directory
        model_dir = self.downloader.get_model_path(model_name)
        os.makedirs(model_dir)
        
        # Still not downloaded without proper files
        self.assertFalse(self.downloader.is_model_downloaded(model_name))
        
        # Add config file
        with open(os.path.join(model_dir, "config.json"), 'w') as f:
            json.dump({"model_type": "test"}, f)
        
        # Should now be considered downloaded
        self.assertTrue(self.downloader.is_model_downloaded(model_name))
    
    def test_get_download_info(self):
        """Test getting download information"""
        # Test with known model
        info = self.downloader.get_download_info("gpt2")
        
        if info:  # May be None if model not in registry
            self.assertIsInstance(info, dict)
            self.assertIn("name", info)
            self.assertIn("repo_id", info)
            self.assertIn("size_gb", info)
        
        # Test with unknown model
        unknown_info = self.downloader.get_download_info("unknown-model")
        self.assertIsNone(unknown_info)


@unittest.skipUnless(MODEL_MODULES_AVAILABLE, "Model management modules not available")
class TestEnvironmentChecker(unittest.TestCase):
    """Test cases for EnvironmentChecker"""
    
    def test_check_environment(self):
        """Test environment checking"""
        env_report = check_environment()
        
        self.assertIsNotNone(env_report)
        self.assertIsNotNone(env_report.hardware)
        self.assertIsNotNone(env_report.dependencies)
        
        # Test hardware info
        hardware = env_report.hardware
        self.assertIsInstance(hardware.has_gpu, bool)
        self.assertIsInstance(hardware.available_ram_gb, (int, float))
        self.assertGreaterEqual(hardware.available_ram_gb, 0)
        
        if hardware.has_gpu:
            self.assertIsInstance(hardware.total_vram_gb, (int, float, type(None)))
            if hardware.total_vram_gb is not None:
                self.assertGreaterEqual(hardware.total_vram_gb, 0)
        
        # Test dependencies
        self.assertIsInstance(env_report.dependencies, list)
        
        # Should check for common ML dependencies
        dep_names = [dep.name for dep in env_report.dependencies]
        expected_deps = ["torch", "transformers", "numpy"]
        
        for expected_dep in expected_deps:
            self.assertIn(expected_dep, dep_names)
    
    def test_hardware_info_creation(self):
        """Test HardwareInfo creation"""
        hardware = HardwareInfo(
            has_gpu=True,
            gpu_names=["NVIDIA RTX 3080"],
            total_vram_gb=10.0,
            available_ram_gb=16.0,
            cpu_cores=8
        )
        
        self.assertTrue(hardware.has_gpu)
        self.assertEqual(hardware.gpu_names, ["NVIDIA RTX 3080"])
        self.assertEqual(hardware.total_vram_gb, 10.0)
        self.assertEqual(hardware.available_ram_gb, 16.0)
        self.assertEqual(hardware.cpu_cores, 8)


@unittest.skipUnless(MODEL_MODULES_AVAILABLE, "Model management modules not available")
class TestModelAccessControl(unittest.TestCase):
    """Test cases for AccessControlManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.access_manager = AccessControlManager()
        except Exception:
            self.access_manager = None
    
    def test_initialization(self):
        """Test AccessControlManager initialization"""
        if self.access_manager:
            self.assertIsNotNone(self.access_manager)
    
    def test_check_model_access(self):
        """Test checking model access permissions"""
        if not self.access_manager:
            self.skipTest("AccessControlManager not available")
        
        # Test with public model (should be accessible)
        public_access = self.access_manager.check_model_access("gpt2")
        self.assertIsInstance(public_access, dict)
        
        # Should have access information
        self.assertIn("accessible", public_access)
        self.assertIsInstance(public_access["accessible"], bool)


class TestModelManagementIntegration(unittest.TestCase):
    """Integration tests for model management system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        if not MODEL_MODULES_AVAILABLE:
            self.skipTest("Model management modules not available")
        
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, "models")
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('model_selector.check_environment')
    def test_full_model_selection_workflow(self, mock_check_env):
        """Test complete model selection workflow"""
        # Mock environment for consistent testing
        mock_env = Mock()
        mock_env.hardware = Mock()
        mock_env.hardware.has_gpu = False
        mock_env.hardware.total_vram_gb = None
        mock_env.hardware.available_ram_gb = 8.0
        mock_env.dependencies = [
            Mock(name="torch", available=True),
            Mock(name="transformers", available=True),
            Mock(name="accelerate", available=False)
        ]
        mock_check_env.return_value = mock_env
        
        # Initialize components
        registry = get_model_registry()
        selector = ModelSelector(
            cache_dir=self.cache_dir,
            config_dir=self.config_dir
        )
        downloader = ModelDownloader(cache_dir=self.cache_dir)
        
        # Test workflow
        # 1. Get model recommendations
        recommendations = selector.get_model_recommendations(count=3)
        self.assertIsInstance(recommendations, list)
        
        # 2. Select best model
        criteria = ModelSelectionCriteria(
            strategy=SelectionStrategy.MINIMAL_RESOURCES,
            max_size_gb=2.0,
            prefer_quantized=True
        )
        
        best_candidate = selector.select_best_model(criteria)
        
        if best_candidate:
            # 3. Check if model needs download
            model_name = best_candidate.model_spec.name
            is_downloaded = downloader.is_model_downloaded(model_name)
            
            # 4. Get download info
            download_info = downloader.get_download_info(model_name)
            
            if download_info:
                self.assertIsInstance(download_info, dict)
                self.assertEqual(download_info["name"], model_name)
            
            # 5. Verify model spec consistency
            registry_spec = registry.get_model(model_name)
            self.assertEqual(registry_spec.name, best_candidate.model_spec.name)
            self.assertEqual(registry_spec.size_gb, best_candidate.model_spec.size_gb)
    
    def test_model_validation_workflow(self):
        """Test model validation and compatibility checking"""
        from model_manager import validate_model_compatibility
        
        # Test with different hardware configurations
        test_configs = [
            {"has_gpu": True, "vram_gb": 24, "ram_gb": 32},
            {"has_gpu": True, "vram_gb": 8, "ram_gb": 16},
            {"has_gpu": False, "vram_gb": None, "ram_gb": 8},
            {"has_gpu": False, "vram_gb": None, "ram_gb": 4}
        ]
        
        registry = get_model_registry()
        all_models = registry.get_all_models()
        
        for config in test_configs:
            for model_name in list(all_models.keys())[:3]:  # Test first 3 models
                is_compatible, reason = validate_model_compatibility(
                    model_name, 
                    config["has_gpu"], 
                    config["vram_gb"], 
                    config["ram_gb"]
                )
                
                self.assertIsInstance(is_compatible, bool)
                self.assertIsInstance(reason, str)
                self.assertGreater(len(reason), 0)
                
                if not is_compatible:
                    # Reason should explain why it's not compatible
                    self.assertTrue(any(keyword in reason.lower() 
                                      for keyword in ["ram", "vram", "gpu", "insufficient"]))


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)