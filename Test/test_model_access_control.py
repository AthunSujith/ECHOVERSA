"""
Tests for the Model Access Control module
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.model_access_control import (
    AccessControlManager, LicenseManager, LicenseType, LicenseInfo, 
    AccessStatus, create_access_manager
)


class TestLicenseManager(unittest.TestCase):
    """Test LicenseManager functionality"""
    
    def setUp(self):
        self.license_manager = LicenseManager()
    
    def test_initialization(self):
        """Test LicenseManager initialization"""
        self.assertIsInstance(self.license_manager, LicenseManager)
        self.assertGreater(len(self.license_manager.license_db), 0)
    
    def test_get_license_info_apache(self):
        """Test getting Apache 2.0 license info"""
        license_info = self.license_manager.get_license_info("Apache-2.0")
        
        self.assertEqual(license_info.license_type, LicenseType.APACHE_2_0)
        self.assertTrue(license_info.commercial_use)
        self.assertTrue(license_info.modification_allowed)
        self.assertTrue(license_info.distribution_allowed)
        self.assertTrue(license_info.attribution_required)
        self.assertFalse(license_info.share_alike_required)
    
    def test_get_license_info_mit(self):
        """Test getting MIT license info"""
        license_info = self.license_manager.get_license_info("MIT")
        
        self.assertEqual(license_info.license_type, LicenseType.MIT)
        self.assertTrue(license_info.commercial_use)
        self.assertTrue(license_info.modification_allowed)
    
    def test_get_license_info_unknown(self):
        """Test getting unknown license info"""
        license_info = self.license_manager.get_license_info("SomeUnknownLicense")
        
        self.assertEqual(license_info.license_type, LicenseType.UNKNOWN)
        self.assertFalse(license_info.commercial_use)
        self.assertFalse(license_info.modification_allowed)
        self.assertGreater(len(license_info.restrictions), 0)
    
    def test_get_license_info_llama(self):
        """Test getting Llama license info"""
        license_info = self.license_manager.get_license_info("llama-2")
        
        self.assertEqual(license_info.license_type, LicenseType.LLAMA_2)
        self.assertTrue(license_info.commercial_use)  # With restrictions
        self.assertGreater(len(license_info.restrictions), 0)
    
    def test_check_license_compatibility_research(self):
        """Test license compatibility for research use"""
        license_info = self.license_manager.get_license_info("MIT")
        compatible, issues = self.license_manager.check_license_compatibility(license_info, "research")
        
        self.assertTrue(compatible)
        self.assertEqual(len(issues), 0)
    
    def test_check_license_compatibility_commercial(self):
        """Test license compatibility for commercial use"""
        # Test with commercial-friendly license
        mit_license = self.license_manager.get_license_info("MIT")
        compatible, issues = self.license_manager.check_license_compatibility(mit_license, "commercial")
        self.assertTrue(compatible)
        
        # Test with research-only license
        research_license = self.license_manager.get_license_info("research-only")
        compatible, issues = self.license_manager.check_license_compatibility(research_license, "commercial")
        self.assertFalse(compatible)
        self.assertGreater(len(issues), 0)


class TestAccessControlManager(unittest.TestCase):
    """Test AccessControlManager functionality"""
    
    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.access_manager = AccessControlManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test AccessControlManager initialization"""
        self.assertIsInstance(self.access_manager, AccessControlManager)
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertIsInstance(self.access_manager.access_cache, dict)
        self.assertIsInstance(self.access_manager.license_acceptances, dict)
        self.assertIsInstance(self.access_manager.auth_tokens, dict)
    
    def test_auth_token_management(self):
        """Test authentication token management"""
        # Set token
        self.access_manager.set_auth_token("huggingface", "test_token_123")
        self.assertEqual(self.access_manager.auth_tokens["huggingface"], "test_token_123")
        
        # Remove token
        self.access_manager.remove_auth_token("huggingface")
        self.assertNotIn("huggingface", self.access_manager.auth_tokens)
    
    def test_license_acceptance(self):
        """Test license acceptance functionality"""
        # Mock model in registry
        with patch.object(self.access_manager.registry, 'get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.license = "MIT"
            mock_get_model.return_value = mock_model
            
            # Accept license
            result = self.access_manager.accept_license("test-model", "MIT License text")
            self.assertTrue(result)
            
            # Check acceptance
            accepted = self.access_manager.check_license_acceptance("test-model")
            self.assertTrue(accepted)
            
            # Verify stored data
            self.assertIn("test-model", self.access_manager.license_acceptances)
            acceptance_data = self.access_manager.license_acceptances["test-model"]
            self.assertEqual(acceptance_data["model_name"], "test-model")
            self.assertEqual(acceptance_data["license_text"], "MIT License text")
    
    def test_license_acceptance_nonexistent_model(self):
        """Test license acceptance for non-existent model"""
        with patch.object(self.access_manager.registry, 'get_model', return_value=None):
            result = self.access_manager.accept_license("nonexistent-model")
            self.assertFalse(result)
    
    @patch('requests.get')
    def test_check_repository_access_public(self, mock_get):
        """Test checking access to public repository"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Mock model in registry
        with patch.object(self.access_manager.registry, 'get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.repo_id = "test/model"
            mock_get_model.return_value = mock_model
            
            status = self.access_manager.check_repository_access("test-model")
            
            self.assertIsInstance(status, AccessStatus)
            self.assertEqual(status.model_name, "test-model")
            self.assertEqual(status.repo_id, "test/model")
            self.assertFalse(status.is_gated)
            self.assertTrue(status.has_access)
            self.assertFalse(status.requires_auth)
    
    @patch('requests.get')
    def test_check_repository_access_gated(self, mock_get):
        """Test checking access to gated repository"""
        # Mock 403 response (gated)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        # Mock model in registry
        with patch.object(self.access_manager.registry, 'get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_model.name = "test-gated-model"
            mock_model.repo_id = "test/gated-model"
            mock_get_model.return_value = mock_model
            
            status = self.access_manager.check_repository_access("test-gated-model")
            
            self.assertTrue(status.is_gated)
            self.assertFalse(status.has_access)
            self.assertTrue(status.requires_auth)
            self.assertIsNotNone(status.access_error)
    
    @patch('requests.get')
    def test_check_repository_access_with_auth(self, mock_get):
        """Test checking access to gated repository with authentication"""
        # Mock responses: first 403, then 200 with auth
        mock_response_403 = MagicMock()
        mock_response_403.status_code = 403
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_get.side_effect = [mock_response_403, mock_response_200]
        
        # Set auth token
        self.access_manager.set_auth_token("huggingface", "test_token")
        
        # Mock model in registry
        with patch.object(self.access_manager.registry, 'get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_model.name = "test-gated-model"
            mock_model.repo_id = "test/gated-model"
            mock_get_model.return_value = mock_model
            
            status = self.access_manager.check_repository_access("test-gated-model")
            
            self.assertTrue(status.is_gated)
            self.assertTrue(status.has_access)
            self.assertTrue(status.requires_auth)
    
    def test_check_repository_access_nonexistent_model(self):
        """Test checking access for non-existent model"""
        with patch.object(self.access_manager.registry, 'get_model', return_value=None):
            status = self.access_manager.check_repository_access("nonexistent-model")
            
            self.assertEqual(status.model_name, "nonexistent-model")
            self.assertEqual(status.repo_id, "unknown")
            self.assertFalse(status.has_access)
            self.assertIsNotNone(status.access_error)
    
    def test_get_license_guidance(self):
        """Test getting license guidance"""
        # Mock model in registry
        with patch.object(self.access_manager.registry, 'get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.repo_id = "test/model"
            mock_model.license = "MIT"
            mock_model.gated = False
            mock_get_model.return_value = mock_model
            
            # Mock access check
            with patch.object(self.access_manager, 'check_repository_access') as mock_check_access:
                mock_status = AccessStatus(
                    model_name="test-model",
                    repo_id="test/model",
                    is_gated=False,
                    has_access=True,
                    requires_auth=False
                )
                mock_check_access.return_value = mock_status
                
                guidance = self.access_manager.get_license_guidance("test-model")
                
                self.assertIsInstance(guidance, dict)
                self.assertEqual(guidance["model_name"], "test-model")
                self.assertEqual(guidance["repo_id"], "test/model")
                self.assertFalse(guidance["is_gated"])
                self.assertTrue(guidance["has_access"])
    
    def test_get_license_guidance_nonexistent_model(self):
        """Test getting license guidance for non-existent model"""
        with patch.object(self.access_manager.registry, 'get_model', return_value=None):
            guidance = self.access_manager.get_license_guidance("nonexistent-model")
            
            self.assertIn("error", guidance)
            self.assertEqual(guidance["error"], "Model not found")
    
    def test_generate_access_report(self):
        """Test generating access report"""
        # Mock registry with test models
        mock_models = {
            "model1": MagicMock(name="model1", license="MIT", gated=False),
            "model2": MagicMock(name="model2", license="Apache-2.0", gated=True)
        }
        
        with patch.object(self.access_manager.registry, 'get_all_models', return_value=mock_models):
            # Mock access checks
            with patch.object(self.access_manager, 'check_repository_access') as mock_check_access:
                mock_check_access.side_effect = [
                    AccessStatus("model1", "test/model1", False, True, False),
                    AccessStatus("model2", "test/model2", True, False, True, access_error="Gated")
                ]
                
                report = self.access_manager.generate_access_report()
                
                self.assertIsInstance(report, dict)
                self.assertEqual(report["total_models"], 2)
                self.assertEqual(report["accessible_models"], 1)
                self.assertEqual(report["gated_models"], 1)
                self.assertIn("model_status", report)
                self.assertIn("access_issues", report)
    
    def test_cache_persistence(self):
        """Test that cache data persists across instances"""
        # Create access status and save
        test_status = AccessStatus(
            model_name="test-model",
            repo_id="test/model",
            is_gated=False,
            has_access=True,
            requires_auth=False,
            last_checked=datetime.now()
        )
        
        self.access_manager.access_cache["test-model"] = test_status
        self.access_manager._save_access_cache()
        
        # Create new instance and check if data is loaded
        new_manager = AccessControlManager(config_dir=self.temp_dir)
        
        self.assertIn("test-model", new_manager.access_cache)
        loaded_status = new_manager.access_cache["test-model"]
        self.assertEqual(loaded_status.model_name, "test-model")
        self.assertEqual(loaded_status.repo_id, "test/model")
    
    def test_create_access_manager_factory(self):
        """Test factory function"""
        manager = create_access_manager(self.temp_dir)
        self.assertIsInstance(manager, AccessControlManager)


class TestAccessStatus(unittest.TestCase):
    """Test AccessStatus dataclass"""
    
    def test_access_status_creation(self):
        """Test AccessStatus creation"""
        status = AccessStatus(
            model_name="test-model",
            repo_id="test/repo",
            is_gated=True,
            has_access=False,
            requires_auth=True,
            access_error="Authentication required"
        )
        
        self.assertEqual(status.model_name, "test-model")
        self.assertEqual(status.repo_id, "test/repo")
        self.assertTrue(status.is_gated)
        self.assertFalse(status.has_access)
        self.assertTrue(status.requires_auth)
        self.assertEqual(status.access_error, "Authentication required")


class TestLicenseInfo(unittest.TestCase):
    """Test LicenseInfo dataclass"""
    
    def test_license_info_creation(self):
        """Test LicenseInfo creation"""
        license_info = LicenseInfo(
            license_type=LicenseType.MIT,
            commercial_use=True,
            modification_allowed=True,
            distribution_allowed=True,
            attribution_required=True,
            share_alike_required=False,
            restrictions=[],
            license_url="https://opensource.org/licenses/MIT"
        )
        
        self.assertEqual(license_info.license_type, LicenseType.MIT)
        self.assertTrue(license_info.commercial_use)
        self.assertTrue(license_info.modification_allowed)
        self.assertEqual(license_info.license_url, "https://opensource.org/licenses/MIT")


if __name__ == '__main__':
    unittest.main()