"""
Tests for the Model Selector module
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.model_selector import (
    ModelSelector, ModelSelectionCriteria, SelectionStrategy, 
    ModelCandidate, create_model_selector
)


class TestModelSelector(unittest.TestCase):
    """Test ModelSelector functionality"""
    
    def setUp(self):
        # Create temporary directories for testing
        self.temp_cache_dir = tempfile.mkdtemp()
        self.temp_config_dir = tempfile.mkdtemp()
        
        # Mock environment report
        self.mock_env_report = MagicMock()
        self.mock_env_report.hardware.available_ram_gb = 16.0
        self.mock_env_report.hardware.has_gpu = False
        self.mock_env_report.hardware.total_vram_gb = None
        self.mock_env_report.dependencies = []
        
        with patch('app.model_selector.check_environment', return_value=self.mock_env_report):
            self.selector = ModelSelector(
                cache_dir=self.temp_cache_dir,
                config_dir=self.temp_config_dir
            )
    
    def tearDown(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        shutil.rmtree(self.temp_config_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ModelSelector initialization"""
        self.assertIsInstance(self.selector, ModelSelector)
        self.assertTrue(Path(self.temp_config_dir).exists())
        self.assertIsInstance(self.selector.user_preferences, dict)
        self.assertIsInstance(self.selector.selection_history, list)
    
    def test_selection_criteria_creation(self):
        """Test ModelSelectionCriteria creation"""
        criteria = ModelSelectionCriteria(
            strategy=SelectionStrategy.QUALITY_FIRST,
            max_size_gb=10.0,
            prefer_quantized=True
        )
        
        self.assertEqual(criteria.strategy, SelectionStrategy.QUALITY_FIRST)
        self.assertEqual(criteria.max_size_gb, 10.0)
        self.assertTrue(criteria.prefer_quantized)
    
    @patch('app.model_selector.check_environment')
    def test_calculate_compatibility_score(self, mock_check_env):
        """Test compatibility score calculation"""
        mock_check_env.return_value = self.mock_env_report
        
        # Mock a test model
        mock_model = MagicMock()
        mock_model.min_ram_gb = 8
        mock_model.requires_gpu = False
        mock_model.min_vram_gb = None
        mock_model.size_gb = 5.0
        
        score, issues = self.selector._calculate_compatibility_score(mock_model)
        
        self.assertIsInstance(score, float)
        self.assertIsInstance(issues, list)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
    
    def test_get_fallback_hierarchy(self):
        """Test fallback hierarchy generation"""
        hierarchy = self.selector.get_fallback_hierarchy()
        
        self.assertIsInstance(hierarchy, list)
        self.assertGreater(len(hierarchy), 0)
        self.assertEqual(hierarchy[-1], "mock")  # Should end with mock fallback
    
    def test_update_preferences(self):
        """Test updating user preferences"""
        original_strategy = self.selector.user_preferences.get("strategy")
        
        self.selector.update_preferences(strategy="quality_first", max_size_gb=15.0)
        
        self.assertEqual(self.selector.user_preferences["strategy"], "quality_first")
        self.assertEqual(self.selector.user_preferences["max_size_gb"], 15.0)
    
    @patch('app.model_selector.check_environment')
    def test_get_model_candidates(self, mock_check_env):
        """Test getting model candidates"""
        mock_check_env.return_value = self.mock_env_report
        
        criteria = ModelSelectionCriteria(strategy=SelectionStrategy.BALANCED)
        
        # Mock the registry to return some test models
        with patch.object(self.selector.registry, 'get_all_models') as mock_get_models:
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.min_ram_gb = 4
            mock_model.requires_gpu = False
            mock_model.is_cpu_compatible = True
            mock_model.size_gb = 2.0
            mock_model.quality_score = 7
            mock_model.speed_score = 8
            mock_model.min_vram_gb = None
            
            mock_get_models.return_value = {"test-model": mock_model}
            
            # Mock downloader
            with patch.object(self.selector.downloader, 'list_downloaded_models', return_value=[]):
                candidates = self.selector.get_model_candidates(criteria)
                
                self.assertIsInstance(candidates, list)
                if candidates:  # If we got candidates
                    self.assertIsInstance(candidates[0], ModelCandidate)
    
    def test_create_model_selector_factory(self):
        """Test factory function"""
        with patch('app.model_selector.check_environment', return_value=self.mock_env_report):
            selector = create_model_selector(self.temp_cache_dir, self.temp_config_dir)
            self.assertIsInstance(selector, ModelSelector)


class TestSelectionStrategy(unittest.TestCase):
    """Test SelectionStrategy enum"""
    
    def test_selection_strategy_values(self):
        """Test SelectionStrategy enum values"""
        self.assertEqual(SelectionStrategy.QUALITY_FIRST.value, "quality_first")
        self.assertEqual(SelectionStrategy.SPEED_FIRST.value, "speed_first")
        self.assertEqual(SelectionStrategy.BALANCED.value, "balanced")
        self.assertEqual(SelectionStrategy.MINIMAL_RESOURCES.value, "minimal_resources")


class TestModelCandidate(unittest.TestCase):
    """Test ModelCandidate dataclass"""
    
    def test_model_candidate_creation(self):
        """Test ModelCandidate creation"""
        mock_model_spec = MagicMock()
        
        candidate = ModelCandidate(
            model_spec=mock_model_spec,
            compatibility_score=85.0,
            selection_score=92.0,
            is_downloaded=True,
            download_size_gb=0.0,
            estimated_load_time=30.0,
            hardware_match="CPU",
            issues=[]
        )
        
        self.assertEqual(candidate.compatibility_score, 85.0)
        self.assertEqual(candidate.selection_score, 92.0)
        self.assertTrue(candidate.is_downloaded)
        self.assertEqual(candidate.hardware_match, "CPU")


if __name__ == '__main__':
    unittest.main()