"""
Tests for the Model Downloader module
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from app.model_downloader import ModelDownloader, DownloadProgress, create_downloader
from app.model_manager import ModelSpec, ModelType, QuantizationType, HardwareRequirement


class TestModelDownloader(unittest.TestCase):
    """Test ModelDownloader functionality"""
    
    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = ModelDownloader(cache_dir=self.temp_dir)
        
        # Create a test model spec
        self.test_model = ModelSpec(
            name="test-model",
            model_type=ModelType.GPT2,
            size_gb=1.0,
            min_vram_gb=None,
            min_ram_gb=4,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="test/test-model",
            quality_score=5,
            speed_score=8,
            description="Test model",
            license="MIT"
        )
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ModelDownloader initialization"""
        self.assertIsInstance(self.downloader, ModelDownloader)
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertIsNone(self.downloader.progress_callback)
    
    def test_safe_model_name(self):
        """Test model name sanitization"""
        unsafe_name = "test/model:with spaces"
        safe_name = self.downloader._safe_model_name(unsafe_name)
        self.assertEqual(safe_name, "test_model_with_spaces")
    
    def test_get_model_cache_dir(self):
        """Test model cache directory generation"""
        cache_dir = self.downloader._get_model_cache_dir("test-model")
        expected_path = Path(self.temp_dir) / "test-model"
        self.assertEqual(cache_dir, expected_path)
    
    def test_progress_callback(self):
        """Test progress callback functionality"""
        callback_called = False
        received_progress = None
        
        def test_callback(progress: DownloadProgress):
            nonlocal callback_called, received_progress
            callback_called = True
            received_progress = progress
        
        self.downloader.set_progress_callback(test_callback)
        
        # Create test progress
        test_progress = DownloadProgress(
            model_name="test",
            total_size=1000,
            downloaded=500,
            speed_mbps=10.0,
            eta_seconds=50,
            status="downloading"
        )
        
        self.downloader._update_progress(test_progress)
        
        self.assertTrue(callback_called)
        self.assertEqual(received_progress.model_name, "test")
        self.assertEqual(received_progress.downloaded, 500)
    
    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        # Create a temporary file with known content
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_content = b"Hello, World!"
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate hash
        hash_value = self.downloader._calculate_file_hash(test_file)
        
        # Verify it's a valid SHA256 hash
        self.assertEqual(len(hash_value), 64)  # SHA256 is 64 hex characters
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))
    
    @patch('requests.get')
    def test_download_file_with_progress_success(self, mock_get):
        """Test successful file download with progress"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b'x' * 500, b'y' * 500]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Track progress updates
        progress_updates = []
        def track_progress(progress):
            progress_updates.append(progress)
        
        self.downloader.set_progress_callback(track_progress)
        
        # Test download
        test_file = Path(self.temp_dir) / "test_download.bin"
        success = self.downloader._download_file_with_progress(
            "http://example.com/file", test_file, "test-model"
        )
        
        self.assertTrue(success)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.stat().st_size, 1000)
        self.assertGreater(len(progress_updates), 0)
        self.assertEqual(progress_updates[-1].status, 'completed')
    
    @patch('requests.get')
    def test_download_file_with_progress_failure(self, mock_get):
        """Test failed file download"""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        # Track progress updates
        progress_updates = []
        def track_progress(progress):
            progress_updates.append(progress)
        
        self.downloader.set_progress_callback(track_progress)
        
        # Test download
        test_file = Path(self.temp_dir) / "test_download.bin"
        success = self.downloader._download_file_with_progress(
            "http://example.com/file", test_file, "test-model"
        )
        
        self.assertFalse(success)
        self.assertFalse(test_file.exists())
        self.assertGreater(len(progress_updates), 0)
        self.assertEqual(progress_updates[-1].status, 'failed')
        self.assertIsNotNone(progress_updates[-1].error)
    
    def test_verify_model_integrity_no_model(self):
        """Test model verification when model doesn't exist"""
        result = self.downloader.verify_model_integrity("nonexistent-model")
        self.assertFalse(result)
    
    def test_verify_model_integrity_with_files(self):
        """Test model verification with existing files"""
        # Create model directory with files
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        # Create some test files
        (model_dir / "model.bin").write_bytes(b'x' * (200 * 1024 * 1024))  # 200MB file
        (model_dir / "config.json").write_text('{"test": true}')
        
        result = self.downloader.verify_model_integrity("test-model")
        self.assertTrue(result)
    
    def test_verify_model_integrity_too_small(self):
        """Test model verification with suspiciously small files"""
        # Create model directory with tiny files
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        (model_dir / "tiny.bin").write_bytes(b'x' * 1000)  # 1KB file
        
        # Should still pass but with warning
        result = self.downloader.verify_model_integrity("test-model")
        self.assertTrue(result)  # Basic verification passes, just warns about size
    
    def test_save_and_load_model_metadata(self):
        """Test saving and loading model metadata"""
        # Create model directory
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        # Save metadata
        self.downloader._save_model_metadata("test-model", self.test_model)
        
        # Check metadata file exists
        metadata_file = model_dir / "model_metadata.json"
        self.assertTrue(metadata_file.exists())
        
        # Load and verify metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['name'], self.test_model.name)
        self.assertEqual(metadata['repo_id'], self.test_model.repo_id)
        self.assertEqual(metadata['size_gb'], self.test_model.size_gb)
    
    def test_list_downloaded_models_empty(self):
        """Test listing downloaded models when none exist"""
        models = self.downloader.list_downloaded_models()
        self.assertEqual(models, [])
    
    def test_list_downloaded_models_with_metadata(self):
        """Test listing downloaded models with metadata"""
        # Create model directory with metadata
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        self.downloader._save_model_metadata("test-model", self.test_model)
        
        models = self.downloader.list_downloaded_models()
        self.assertEqual(models, ["test-model"])
    
    def test_list_downloaded_models_without_metadata(self):
        """Test listing downloaded models without metadata"""
        # Create model directory without metadata
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        models = self.downloader.list_downloaded_models()
        self.assertEqual(models, ["test-model"])
    
    def test_get_model_path_nonexistent(self):
        """Test getting path for non-existent model"""
        path = self.downloader.get_model_path("nonexistent-model")
        self.assertIsNone(path)
    
    def test_get_model_path_gguf(self):
        """Test getting path for GGUF model"""
        # Create model directory with GGUF file
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        gguf_file = model_dir / "model.gguf"
        gguf_file.write_bytes(b'test gguf content')
        
        path = self.downloader.get_model_path("test-model")
        self.assertEqual(path, gguf_file)
    
    def test_get_model_path_regular(self):
        """Test getting path for regular model"""
        # Create model directory without GGUF file
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        
        (model_dir / "model.bin").write_bytes(b'test content')
        
        path = self.downloader.get_model_path("test-model")
        self.assertEqual(path, model_dir)
    
    def test_delete_model_success(self):
        """Test successful model deletion"""
        # Create model directory
        model_dir = Path(self.temp_dir) / "test-model"
        model_dir.mkdir()
        (model_dir / "test_file.bin").write_bytes(b'test')
        
        self.assertTrue(model_dir.exists())
        
        result = self.downloader.delete_model("test-model")
        
        self.assertTrue(result)
        self.assertFalse(model_dir.exists())
    
    def test_delete_model_nonexistent(self):
        """Test deleting non-existent model"""
        result = self.downloader.delete_model("nonexistent-model")
        self.assertFalse(result)
    
    def test_get_download_size_info(self):
        """Test getting download size information"""
        # Create model directories with files
        model1_dir = Path(self.temp_dir) / "model1"
        model1_dir.mkdir()
        (model1_dir / "file1.bin").write_bytes(b'x' * (100 * 1024 * 1024))  # 100MB
        
        model2_dir = Path(self.temp_dir) / "model2"
        model2_dir.mkdir()
        (model2_dir / "file2.bin").write_bytes(b'y' * (200 * 1024 * 1024))  # 200MB
        
        size_info = self.downloader.get_download_size_info()
        
        self.assertIn("model1", size_info)
        self.assertIn("model2", size_info)
        self.assertAlmostEqual(size_info["model1"], 0.1, places=2)  # ~0.1GB
        self.assertAlmostEqual(size_info["model2"], 0.2, places=2)  # ~0.2GB
    
    @patch('app.model_downloader.get_model_registry')
    def test_download_model_not_found(self, mock_registry):
        """Test downloading non-existent model"""
        mock_registry.return_value.get_model.return_value = None
        
        result = self.downloader.download_model("nonexistent-model")
        self.assertFalse(result)
    
    def test_create_downloader_factory(self):
        """Test factory function"""
        downloader = create_downloader(self.temp_dir)
        self.assertIsInstance(downloader, ModelDownloader)


class TestDownloadProgress(unittest.TestCase):
    """Test DownloadProgress dataclass"""
    
    def test_download_progress_creation(self):
        """Test DownloadProgress creation"""
        progress = DownloadProgress(
            model_name="test-model",
            total_size=1000,
            downloaded=500,
            speed_mbps=10.5,
            eta_seconds=50,
            status="downloading"
        )
        
        self.assertEqual(progress.model_name, "test-model")
        self.assertEqual(progress.total_size, 1000)
        self.assertEqual(progress.downloaded, 500)
        self.assertEqual(progress.speed_mbps, 10.5)
        self.assertEqual(progress.eta_seconds, 50)
        self.assertEqual(progress.status, "downloading")
        self.assertIsNone(progress.error)


if __name__ == '__main__':
    unittest.main()