"""
Model Downloader for EchoVerse
Handles downloading models from Hugging Face Hub and direct GGUF sources
"""

import os
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse
import tempfile
import shutil

# Handle optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

try:
    from .model_manager import ModelSpec, get_model_registry
except ImportError:
    from model_manager import ModelSpec, get_model_registry


@dataclass
class DownloadProgress:
    """Progress information for model downloads"""
    model_name: str
    total_size: int
    downloaded: int
    speed_mbps: float
    eta_seconds: Optional[int]
    status: str  # 'downloading', 'completed', 'failed', 'verifying'
    error: Optional[str] = None


class ModelDownloader:
    """Handles model downloading with progress tracking and verification"""
    
    def __init__(self, cache_dir: str = "download/models"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.registry = get_model_registry()
        
        # Progress callback
        self.progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        
        # Known GGUF mirror URLs (TheBloke repositories)
        self.gguf_mirrors = {
            "mpt-7b-instruct-gguf-q4": "https://huggingface.co/TheBloke/mpt-7B-instruct-GGUF/resolve/main/mpt-7b-instruct.Q4_K_M.gguf",
            "falcon-7b-instruct-gguf-q4": "https://huggingface.co/TheBloke/falcon-7b-instruct-GGUF/resolve/main/falcon-7b-instruct.Q4_K_M.gguf",
            "phi-2-gguf-q4": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
            "tinyllama-1.1b-chat-gguf-q4": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            "stablelm-2-zephyr-1.6b-gguf-q4": "https://huggingface.co/TheBloke/stablelm-2-zephyr-1_6b-GGUF/resolve/main/stablelm-2-zephyr-1_6b.Q4_K_M.gguf"
        }
    
    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Set callback function for progress updates"""
        self.progress_callback = callback
    
    def _safe_model_name(self, model_name: str) -> str:
        """Convert model name to safe directory name"""
        return model_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    
    def _get_model_cache_dir(self, model_name: str) -> Path:
        """Get cache directory for specific model"""
        safe_name = self._safe_model_name(model_name)
        return self.cache_dir / safe_name
    
    def _update_progress(self, progress: DownloadProgress) -> None:
        """Update progress via callback if set"""
        if self.progress_callback:
            self.progress_callback(progress)
    
    def _calculate_file_hash(self, filepath: Path, algorithm: str = "sha256") -> str:
        """Calculate hash of file for integrity verification"""
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def _download_file_with_progress(self, url: str, filepath: Path, 
                                   model_name: str, expected_size: Optional[int] = None) -> bool:
        """Download file with progress tracking"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            if expected_size and total_size != expected_size:
                print(f"Warning: Expected size {expected_size}, got {total_size}")
            
            downloaded = 0
            start_time = time.time()
            
            # Create temporary file first
            temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
            
            with open(temp_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                            eta = (total_size - downloaded) / (downloaded / elapsed) if downloaded > 0 else None
                        else:
                            speed_mbps = 0
                            eta = None
                        
                        progress = DownloadProgress(
                            model_name=model_name,
                            total_size=total_size,
                            downloaded=downloaded,
                            speed_mbps=speed_mbps,
                            eta_seconds=int(eta) if eta else None,
                            status='downloading'
                        )
                        self._update_progress(progress)
            
            # Move temp file to final location
            temp_filepath.rename(filepath)
            
            # Final progress update
            progress = DownloadProgress(
                model_name=model_name,
                total_size=total_size,
                downloaded=downloaded,
                speed_mbps=speed_mbps,
                eta_seconds=0,
                status='completed'
            )
            self._update_progress(progress)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
            if temp_filepath.exists():
                temp_filepath.unlink()
            
            progress = DownloadProgress(
                model_name=model_name,
                total_size=0,
                downloaded=0,
                speed_mbps=0,
                eta_seconds=None,
                status='failed',
                error=str(e)
            )
            self._update_progress(progress)
            return False
    
    def _download_huggingface_model(self, model_spec: ModelSpec) -> bool:
        """Download model using huggingface_hub"""
        try:
            # Try to import huggingface_hub
            from huggingface_hub import snapshot_download, hf_hub_download
            from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError
            
            model_cache_dir = self._get_model_cache_dir(model_spec.name)
            
            # Check if model is gated
            if model_spec.gated:
                print(f"Warning: {model_spec.name} is a gated model. You may need to authenticate.")
            
            try:
                # For single file models (like GGUF), download specific file
                if model_spec.name.endswith('-gguf-q4') or model_spec.name.endswith('-gguf-q8'):
                    # Try to determine the specific file to download
                    if model_spec.name in self.gguf_mirrors:
                        # Use direct download for known GGUF files
                        return self._download_gguf_direct(model_spec)
                    else:
                        # Fallback to snapshot download
                        snapshot_download(
                            repo_id=model_spec.repo_id,
                            cache_dir=str(model_cache_dir),
                            local_dir=str(model_cache_dir),
                            local_dir_use_symlinks=False
                        )
                else:
                    # Full model download
                    snapshot_download(
                        repo_id=model_spec.repo_id,
                        cache_dir=str(model_cache_dir),
                        local_dir=str(model_cache_dir),
                        local_dir_use_symlinks=False
                    )
                
                return True
                
            except GatedRepoError:
                print(f"Error: {model_spec.name} requires authentication. Please login with 'huggingface-cli login'")
                return False
            except RepositoryNotFoundError:
                print(f"Error: Repository {model_spec.repo_id} not found")
                return False
                
        except ImportError:
            print("Error: huggingface_hub not available. Please install it with: pip install huggingface_hub")
            return False
        except Exception as e:
            print(f"Error downloading {model_spec.name}: {e}")
            return False
    
    def _download_gguf_direct(self, model_spec: ModelSpec) -> bool:
        """Download GGUF files directly from known mirrors"""
        if model_spec.name not in self.gguf_mirrors:
            return False
        
        url = self.gguf_mirrors[model_spec.name]
        model_cache_dir = self._get_model_cache_dir(model_spec.name)
        model_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract filename from URL
        filename = Path(urlparse(url).path).name
        filepath = model_cache_dir / filename
        
        print(f"Downloading {model_spec.name} from {url}")
        return self._download_file_with_progress(url, filepath, model_spec.name)
    
    def verify_model_integrity(self, model_name: str, 
                             expected_checksums: Optional[Dict[str, str]] = None) -> bool:
        """Verify downloaded model integrity"""
        model_cache_dir = self._get_model_cache_dir(model_name)
        
        if not model_cache_dir.exists():
            return False
        
        # Update progress
        progress = DownloadProgress(
            model_name=model_name,
            total_size=0,
            downloaded=0,
            speed_mbps=0,
            eta_seconds=None,
            status='verifying'
        )
        self._update_progress(progress)
        
        # Basic verification: check if files exist and have reasonable sizes
        model_files = list(model_cache_dir.rglob("*"))
        model_files = [f for f in model_files if f.is_file()]
        
        if not model_files:
            return False
        
        # Check file sizes (basic sanity check)
        total_size = sum(f.stat().st_size for f in model_files)
        if total_size < 100 * 1024 * 1024:  # Less than 100MB seems suspicious
            print(f"Warning: Model {model_name} total size is only {total_size / (1024*1024):.1f}MB")
        
        # If checksums provided, verify them
        if expected_checksums:
            for filepath, expected_hash in expected_checksums.items():
                full_path = model_cache_dir / filepath
                if full_path.exists():
                    actual_hash = self._calculate_file_hash(full_path)
                    if actual_hash != expected_hash:
                        print(f"Checksum mismatch for {filepath}: expected {expected_hash}, got {actual_hash}")
                        return False
        
        return True
    
    def download_model(self, model_name: str, force_redownload: bool = False) -> bool:
        """Download a model by name"""
        model_spec = self.registry.get_model(model_name)
        if not model_spec:
            print(f"Error: Model {model_name} not found in registry")
            return False
        
        model_cache_dir = self._get_model_cache_dir(model_name)
        
        # Check if already downloaded
        if model_cache_dir.exists() and not force_redownload:
            if self.verify_model_integrity(model_name):
                print(f"Model {model_name} already downloaded and verified")
                return True
            else:
                print(f"Model {model_name} exists but failed verification, re-downloading...")
                shutil.rmtree(model_cache_dir)
        
        print(f"Downloading model: {model_name}")
        print(f"Repository: {model_spec.repo_id}")
        print(f"Size: ~{model_spec.size_gb:.1f}GB")
        print(f"Cache directory: {model_cache_dir}")
        
        # Try different download methods
        success = False
        
        # Method 1: Direct GGUF download
        if model_name in self.gguf_mirrors:
            print("Attempting direct GGUF download...")
            success = self._download_gguf_direct(model_spec)
        
        # Method 2: Hugging Face Hub download
        if not success:
            print("Attempting Hugging Face Hub download...")
            success = self._download_huggingface_model(model_spec)
        
        if success:
            # Verify download
            if self.verify_model_integrity(model_name):
                print(f"Successfully downloaded and verified {model_name}")
                self._save_model_metadata(model_name, model_spec)
                return True
            else:
                print(f"Download completed but verification failed for {model_name}")
                return False
        else:
            print(f"Failed to download {model_name}")
            return False
    
    def _save_model_metadata(self, model_name: str, model_spec: ModelSpec) -> None:
        """Save model metadata to cache directory"""
        model_cache_dir = self._get_model_cache_dir(model_name)
        metadata_file = model_cache_dir / "model_metadata.json"
        
        metadata = {
            "name": model_spec.name,
            "model_type": model_spec.model_type.value,
            "size_gb": model_spec.size_gb,
            "repo_id": model_spec.repo_id,
            "quantization": model_spec.quantization.value,
            "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "hardware_req": model_spec.hardware_req.value,
            "quality_score": model_spec.quality_score,
            "speed_score": model_spec.speed_score
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def list_downloaded_models(self) -> List[str]:
        """List all downloaded models"""
        downloaded = []
        
        if not self.cache_dir.exists():
            return downloaded
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir():
                metadata_file = model_dir / "model_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        downloaded.append(metadata['name'])
                    except:
                        # Fallback to directory name
                        downloaded.append(model_dir.name)
                else:
                    downloaded.append(model_dir.name)
        
        return downloaded
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get the local path to a downloaded model"""
        model_cache_dir = self._get_model_cache_dir(model_name)
        
        if not model_cache_dir.exists():
            return None
        
        # For GGUF models, return the .gguf file
        gguf_files = list(model_cache_dir.glob("*.gguf"))
        if gguf_files:
            return gguf_files[0]
        
        # For regular models, return the directory
        return model_cache_dir
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model"""
        model_cache_dir = self._get_model_cache_dir(model_name)
        
        if model_cache_dir.exists():
            try:
                shutil.rmtree(model_cache_dir)
                print(f"Deleted model: {model_name}")
                return True
            except Exception as e:
                print(f"Error deleting model {model_name}: {e}")
                return False
        else:
            print(f"Model {model_name} not found")
            return False
    
    def get_download_size_info(self) -> Dict[str, float]:
        """Get disk usage information for downloaded models"""
        info = {}
        
        if not self.cache_dir.exists():
            return info
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir():
                total_size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
                info[model_dir.name] = total_size / (1024**3)  # Convert to GB
        
        return info


def create_downloader(cache_dir: str = "download/models") -> ModelDownloader:
    """Factory function to create a ModelDownloader instance"""
    return ModelDownloader(cache_dir)