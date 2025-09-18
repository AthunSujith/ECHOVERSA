"""
Environment and Hardware Detection for EchoVerse
Checks system capabilities, dependencies, and hardware resources
"""

import os
import sys
import platform
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import importlib.util

# Handle optional psutil import
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class HardwareInfo:
    """System hardware information"""
    cpu_count: int
    cpu_model: str
    total_ram_gb: float
    available_ram_gb: float
    has_gpu: bool
    gpu_count: int
    gpu_names: List[str]
    total_vram_gb: Optional[float]
    available_vram_gb: Optional[float]
    platform: str
    architecture: str


@dataclass
class DependencyInfo:
    """Dependency availability information"""
    name: str
    available: bool
    version: Optional[str]
    import_error: Optional[str]


@dataclass
class EnvironmentReport:
    """Complete environment assessment report"""
    hardware: HardwareInfo
    dependencies: List[DependencyInfo]
    ffmpeg_available: bool
    ffmpeg_path: Optional[str]
    python_version: str
    recommendations: List[str]
    warnings: List[str]
    errors: List[str]


class EnvironmentChecker:
    """Comprehensive environment and hardware checker"""
    
    REQUIRED_DEPENDENCIES = [
        "torch",
        "transformers", 
        "accelerate",
        "huggingface_hub"
    ]
    
    OPTIONAL_DEPENDENCIES = [
        "bitsandbytes",
        "peft",
        "optimum",
        "auto-gptq",
        "llama-cpp-python"
    ]
    
    def __init__(self):
        self.hardware_info = None
        self.dependency_info = []
    
    def check_hardware(self) -> HardwareInfo:
        """Detect and analyze hardware capabilities"""
        # CPU information
        if PSUTIL_AVAILABLE:
            cpu_count = psutil.cpu_count(logical=True)
            cpu_model = platform.processor() or "Unknown CPU"
            
            # Memory information
            memory = psutil.virtual_memory()
            total_ram_gb = memory.total / (1024**3)
            available_ram_gb = memory.available / (1024**3)
        else:
            # Fallback without psutil
            cpu_count = os.cpu_count() or 1
            cpu_model = platform.processor() or "Unknown CPU"
            
            # Rough memory estimation (not accurate without psutil)
            total_ram_gb = 8.0  # Default assumption
            available_ram_gb = 6.0  # Conservative estimate
        
        # GPU detection
        has_gpu, gpu_count, gpu_names, total_vram_gb, available_vram_gb = self._detect_gpu()
        
        # Platform information
        platform_name = platform.system()
        architecture = platform.machine()
        
        self.hardware_info = HardwareInfo(
            cpu_count=cpu_count,
            cpu_model=cpu_model,
            total_ram_gb=total_ram_gb,
            available_ram_gb=available_ram_gb,
            has_gpu=has_gpu,
            gpu_count=gpu_count,
            gpu_names=gpu_names,
            total_vram_gb=total_vram_gb,
            available_vram_gb=available_vram_gb,
            platform=platform_name,
            architecture=architecture
        )
        
        return self.hardware_info
    
    def _detect_gpu(self) -> Tuple[bool, int, List[str], Optional[float], Optional[float]]:
        """Detect GPU availability and VRAM"""
        has_gpu = False
        gpu_count = 0
        gpu_names = []
        total_vram_gb = None
        available_vram_gb = None
        
        try:
            import torch
            if torch.cuda.is_available():
                has_gpu = True
                gpu_count = torch.cuda.device_count()
                
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_names.append(gpu_name)
                
                # Get VRAM info for primary GPU
                if gpu_count > 0:
                    total_vram_bytes = torch.cuda.get_device_properties(0).total_memory
                    total_vram_gb = total_vram_bytes / (1024**3)
                    
                    # Get available VRAM
                    torch.cuda.empty_cache()
                    available_vram_bytes = total_vram_bytes - torch.cuda.memory_allocated(0)
                    available_vram_gb = available_vram_bytes / (1024**3)
        
        except ImportError:
            # PyTorch not available, try alternative detection
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    has_gpu = True
                    gpu_count = len(gpus)
                    gpu_names = [gpu.name for gpu in gpus]
                    if gpus:
                        total_vram_gb = gpus[0].memoryTotal / 1024  # MB to GB
                        available_vram_gb = gpus[0].memoryFree / 1024
            except ImportError:
                pass
        
        return has_gpu, gpu_count, gpu_names, total_vram_gb, available_vram_gb
    
    def check_dependencies(self) -> List[DependencyInfo]:
        """Check availability of required and optional dependencies"""
        self.dependency_info = []
        
        # Check required dependencies
        for dep in self.REQUIRED_DEPENDENCIES:
            info = self._check_single_dependency(dep)
            self.dependency_info.append(info)
        
        # Check optional dependencies
        for dep in self.OPTIONAL_DEPENDENCIES:
            info = self._check_single_dependency(dep)
            self.dependency_info.append(info)
        
        return self.dependency_info
    
    def _check_single_dependency(self, package_name: str) -> DependencyInfo:
        """Check if a single dependency is available"""
        try:
            spec = importlib.util.find_spec(package_name)
            if spec is None:
                return DependencyInfo(
                    name=package_name,
                    available=False,
                    version=None,
                    import_error="Package not found"
                )
            
            # Try to import and get version
            module = importlib.import_module(package_name)
            version = getattr(module, '__version__', 'Unknown')
            
            return DependencyInfo(
                name=package_name,
                available=True,
                version=version,
                import_error=None
            )
        
        except ImportError as e:
            return DependencyInfo(
                name=package_name,
                available=False,
                version=None,
                import_error=str(e)
            )
        except Exception as e:
            return DependencyInfo(
                name=package_name,
                available=False,
                version=None,
                import_error=f"Unexpected error: {str(e)}"
            )
    
    def check_ffmpeg(self) -> Tuple[bool, Optional[str]]:
        """Check if ffmpeg is available in PATH"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                # Try to find ffmpeg path
                try:
                    path_result = subprocess.run(
                        ['where', 'ffmpeg'] if platform.system() == 'Windows' else ['which', 'ffmpeg'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    ffmpeg_path = path_result.stdout.strip().split('\n')[0] if path_result.returncode == 0 else None
                except:
                    ffmpeg_path = None
                
                return True, ffmpeg_path
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False, None
    
    def generate_report(self) -> EnvironmentReport:
        """Generate comprehensive environment report"""
        # Collect all information
        hardware = self.check_hardware()
        dependencies = self.check_dependencies()
        ffmpeg_available, ffmpeg_path = self.check_ffmpeg()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # Generate recommendations, warnings, and errors
        recommendations = []
        warnings = []
        errors = []
        
        # Hardware recommendations
        if hardware.total_ram_gb < 8:
            warnings.append(f"Low RAM detected ({hardware.total_ram_gb:.1f}GB). Recommend at least 8GB for model inference.")
        
        if not hardware.has_gpu:
            recommendations.append("No GPU detected. Consider using CPU-optimized quantized models (GGUF format).")
        elif hardware.total_vram_gb and hardware.total_vram_gb < 8:
            recommendations.append(f"Limited VRAM ({hardware.total_vram_gb:.1f}GB). Consider 4-bit quantized models.")
        elif hardware.total_vram_gb and hardware.total_vram_gb >= 16:
            recommendations.append("Sufficient VRAM for full-precision 7B models.")
        
        # Dependency analysis
        missing_required = [dep for dep in dependencies 
                          if dep.name in self.REQUIRED_DEPENDENCIES and not dep.available]
        
        if missing_required:
            errors.extend([f"Missing required dependency: {dep.name}" for dep in missing_required])
        
        missing_optional = [dep for dep in dependencies 
                          if dep.name in self.OPTIONAL_DEPENDENCIES and not dep.available]
        
        if missing_optional:
            warnings.extend([f"Missing optional dependency: {dep.name} - {dep.import_error}" 
                           for dep in missing_optional])
        
        # PyTorch GPU support check
        torch_dep = next((dep for dep in dependencies if dep.name == "torch"), None)
        if torch_dep and torch_dep.available and hardware.has_gpu:
            try:
                import torch
                if not torch.cuda.is_available():
                    warnings.append("PyTorch installed but CUDA support not available. GPU acceleration disabled.")
            except:
                pass
        
        # FFmpeg check
        if not ffmpeg_available:
            warnings.append("FFmpeg not found in PATH. Audio processing may be limited.")
        
        # Platform-specific recommendations
        if hardware.platform == "Darwin" and hardware.architecture == "arm64":
            recommendations.append("Apple Silicon detected. Consider using Metal Performance Shaders (MPS) backend.")
        
        return EnvironmentReport(
            hardware=hardware,
            dependencies=dependencies,
            ffmpeg_available=ffmpeg_available,
            ffmpeg_path=ffmpeg_path,
            python_version=python_version,
            recommendations=recommendations,
            warnings=warnings,
            errors=errors
        )
    
    def print_report(self, report: Optional[EnvironmentReport] = None) -> None:
        """Print formatted environment report"""
        if report is None:
            report = self.generate_report()
        
        print("=" * 60)
        print("ECHOVERSE ENVIRONMENT REPORT")
        print("=" * 60)
        
        # System Information
        print(f"\n🖥️  SYSTEM INFORMATION")
        print(f"Platform: {report.hardware.platform} ({report.hardware.architecture})")
        print(f"Python: {report.python_version}")
        print(f"CPU: {report.hardware.cpu_model}")
        print(f"CPU Cores: {report.hardware.cpu_count}")
        print(f"RAM: {report.hardware.total_ram_gb:.1f}GB total, {report.hardware.available_ram_gb:.1f}GB available")
        
        # GPU Information
        print(f"\n🎮 GPU INFORMATION")
        if report.hardware.has_gpu:
            print(f"GPU Count: {report.hardware.gpu_count}")
            for i, gpu_name in enumerate(report.hardware.gpu_names):
                print(f"GPU {i}: {gpu_name}")
            if report.hardware.total_vram_gb:
                print(f"VRAM: {report.hardware.total_vram_gb:.1f}GB total, {report.hardware.available_vram_gb:.1f}GB available")
        else:
            print("No GPU detected")
        
        # Dependencies
        print(f"\n📦 DEPENDENCIES")
        required_deps = [dep for dep in report.dependencies if dep.name in self.REQUIRED_DEPENDENCIES]
        optional_deps = [dep for dep in report.dependencies if dep.name in self.OPTIONAL_DEPENDENCIES]
        
        print("Required:")
        for dep in required_deps:
            status = "✅" if dep.available else "❌"
            version = f" (v{dep.version})" if dep.version else ""
            print(f"  {status} {dep.name}{version}")
        
        print("Optional:")
        for dep in optional_deps:
            status = "✅" if dep.available else "⚠️"
            version = f" (v{dep.version})" if dep.version else ""
            print(f"  {status} {dep.name}{version}")
        
        # FFmpeg
        print(f"\n🎵 AUDIO PROCESSING")
        ffmpeg_status = "✅" if report.ffmpeg_available else "❌"
        ffmpeg_info = f" ({report.ffmpeg_path})" if report.ffmpeg_path else ""
        print(f"FFmpeg: {ffmpeg_status}{ffmpeg_info}")
        
        # Errors
        if report.errors:
            print(f"\n❌ ERRORS")
            for error in report.errors:
                print(f"  • {error}")
        
        # Warnings
        if report.warnings:
            print(f"\n⚠️  WARNINGS")
            for warning in report.warnings:
                print(f"  • {warning}")
        
        # Recommendations
        if report.recommendations:
            print(f"\n💡 RECOMMENDATIONS")
            for rec in report.recommendations:
                print(f"  • {rec}")
        
        print("\n" + "=" * 60)


def check_environment() -> EnvironmentReport:
    """Convenience function to check environment"""
    checker = EnvironmentChecker()
    return checker.generate_report()


def print_environment_report() -> None:
    """Convenience function to print environment report"""
    checker = EnvironmentChecker()
    checker.print_report()


if __name__ == "__main__":
    print_environment_report()