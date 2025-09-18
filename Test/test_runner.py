#!/usr/bin/env python3
"""
Comprehensive Test Runner for EchoVerse Companion Application
Orchestrates all testing including unit tests, integration tests, and local model validation
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add app directory to path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Test configuration
TEST_CONFIG = {
    "unit_tests": [
        "test_data_models.py",
        "test_auth_manager.py", 
        "test_storage_manager.py",
        "test_input_processor.py",
        "test_content_generator.py",
        "test_audio_processor.py",
        "test_model_management.py",
        "test_defensive_system.py"
    ],
    "integration_tests": [
        "test_integration_pipeline.py",
        "test_content_integration.py",
        "test_history_panel.py",
        "test_multimodal_input.py"
    ],
    "system_tests": [
        "test.py",
        "test_system_validation.py"
    ],
    "api_tests": [
        "gem_api.py"
    ],
    "model_tests": [
        "test_model_downloader.py",
        "test_model_selector.py",
        "test_environment_checker.py"
    ]
}


class TestRunner:
    """Comprehensive test runner for EchoVerse"""
    
    def __init__(self, test_dir: str = None):
        """Initialize test runner"""
        self.test_dir = Path(test_dir) if test_dir else Path(__file__).parent
        self.results = {
            "start_time": datetime.now().isoformat(),
            "test_categories": {},
            "overall_summary": {},
            "environment_info": {}
        }
        
        # Collect environment information
        self._collect_environment_info()
    
    def _collect_environment_info(self):
        """Collect environment information for test context"""
        try:
            import platform
            import psutil
            
            self.results["environment_info"] = {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "disk_free_gb": round(psutil.disk_usage('.').free / (1024**3), 1)
            }
            
            # Check GPU availability
            try:
                import torch
                self.results["environment_info"]["torch_available"] = True
                self.results["environment_info"]["cuda_available"] = torch.cuda.is_available()
                if torch.cuda.is_available():
                    self.results["environment_info"]["gpu_count"] = torch.cuda.device_count()
                    self.results["environment_info"]["gpu_name"] = torch.cuda.get_device_name(0)
            except ImportError:
                self.results["environment_info"]["torch_available"] = False
                self.results["environment_info"]["cuda_available"] = False
            
        except Exception as e:
            self.results["environment_info"]["error"] = str(e)
    
    def run_test_file(self, test_file: str, timeout: int = 300) -> Dict[str, Any]:
        """Run a single test file"""
        test_path = self.test_dir / test_file
        
        if not test_path.exists():
            return {
                "file": test_file,
                "status": "skipped",
                "reason": "File not found",
                "duration": 0
            }
        
        print(f"🧪 Running {test_file}...")
        
        start_time = time.time()
        
        try:
            # Run the test file
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.test_dir.parent)  # Run from project root
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = "passed"
                print(f"  ✅ {test_file} passed ({duration:.1f}s)")
            else:
                status = "failed"
                print(f"  ❌ {test_file} failed ({duration:.1f}s)")
            
            return {
                "file": test_file,
                "status": status,
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"  ⏰ {test_file} timed out ({duration:.1f}s)")
            
            return {
                "file": test_file,
                "status": "timeout",
                "duration": duration,
                "reason": f"Exceeded {timeout}s timeout"
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"  💥 {test_file} error: {e}")
            
            return {
                "file": test_file,
                "status": "error",
                "duration": duration,
                "error": str(e)
            }
    
    def run_test_category(self, category: str, test_files: List[str], 
                         timeout: int = 300) -> Dict[str, Any]:
        """Run all tests in a category"""
        print(f"\n📂 Running {category} tests...")
        print("=" * 50)
        
        category_start_time = time.time()
        test_results = []
        
        for test_file in test_files:
            result = self.run_test_file(test_file, timeout)
            test_results.append(result)
        
        category_duration = time.time() - category_start_time
        
        # Calculate category statistics
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r["status"] == "passed"])
        failed_tests = len([r for r in test_results if r["status"] == "failed"])
        skipped_tests = len([r for r in test_results if r["status"] == "skipped"])
        timeout_tests = len([r for r in test_results if r["status"] == "timeout"])
        error_tests = len([r for r in test_results if r["status"] == "error"])
        
        category_result = {
            "category": category,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "timeouts": timeout_tests,
            "errors": error_tests,
            "duration": category_duration,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "test_results": test_results
        }
        
        print(f"\n📊 {category} Summary:")
        print(f"  Total: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Skipped: {skipped_tests}")
        print(f"  Timeouts: {timeout_tests}")
        print(f"  Errors: {error_tests}")
        print(f"  Success Rate: {category_result['success_rate']:.1%}")
        print(f"  Duration: {category_duration:.1f}s")
        
        return category_result
    
    def run_local_model_tests(self) -> Dict[str, Any]:
        """Run local model-specific tests"""
        print(f"\n🤖 Running local model tests...")
        print("=" * 50)
        
        model_test_start = time.time()
        model_results = []
        
        # Test environment checking
        print("🔧 Testing environment compatibility...")
        try:
            from environment_checker import check_environment
            env_report = check_environment()
            
            env_test_result = {
                "test": "environment_check",
                "status": "passed",
                "has_gpu": env_report.hardware.has_gpu,
                "ram_gb": env_report.hardware.available_ram_gb,
                "vram_gb": env_report.hardware.total_vram_gb,
                "dependencies": len([d for d in env_report.dependencies if d.available])
            }
            
            print(f"  ✅ Environment check passed")
            print(f"    GPU: {env_report.hardware.has_gpu}")
            print(f"    RAM: {env_report.hardware.available_ram_gb:.1f}GB")
            if env_report.hardware.total_vram_gb:
                print(f"    VRAM: {env_report.hardware.total_vram_gb:.1f}GB")
            
        except Exception as e:
            env_test_result = {
                "test": "environment_check",
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Environment check failed: {e}")
        
        model_results.append(env_test_result)
        
        # Test model registry
        print("📚 Testing model registry...")
        try:
            from model_manager import get_model_registry
            registry = get_model_registry()
            all_models = registry.get_all_models()
            cpu_models = registry.get_cpu_compatible_models()
            
            registry_test_result = {
                "test": "model_registry",
                "status": "passed",
                "total_models": len(all_models),
                "cpu_compatible_models": len(cpu_models),
                "model_names": list(all_models.keys())[:5]  # First 5 models
            }
            
            print(f"  ✅ Model registry test passed")
            print(f"    Total models: {len(all_models)}")
            print(f"    CPU compatible: {len(cpu_models)}")
            
        except Exception as e:
            registry_test_result = {
                "test": "model_registry",
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Model registry test failed: {e}")
        
        model_results.append(registry_test_result)
        
        # Test model selection
        print("🎯 Testing model selection...")
        try:
            from model_selector import ModelSelector, ModelSelectionCriteria, SelectionStrategy
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                selector = ModelSelector(
                    cache_dir=temp_dir + "/models",
                    config_dir=temp_dir + "/config"
                )
                
                criteria = ModelSelectionCriteria(
                    strategy=SelectionStrategy.MINIMAL_RESOURCES,
                    max_size_gb=5.0
                )
                
                candidates = selector.get_model_candidates(criteria)
                best_model = selector.select_best_model(criteria)
                
                selection_test_result = {
                    "test": "model_selection",
                    "status": "passed",
                    "candidates_found": len(candidates),
                    "best_model": best_model.model_spec.name if best_model else None,
                    "best_model_size": best_model.model_spec.size_gb if best_model else None
                }
                
                print(f"  ✅ Model selection test passed")
                print(f"    Candidates found: {len(candidates)}")
                if best_model:
                    print(f"    Best model: {best_model.model_spec.name} ({best_model.model_spec.size_gb:.1f}GB)")
                
        except Exception as e:
            selection_test_result = {
                "test": "model_selection",
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Model selection test failed: {e}")
        
        model_results.append(selection_test_result)
        
        # Test model download capabilities (without actually downloading)
        print("📥 Testing model download capabilities...")
        try:
            from model_downloader import ModelDownloader
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                downloader = ModelDownloader(cache_dir=temp_dir)
                
                # Test getting download info
                download_info = downloader.get_download_info("gpt2")
                downloaded_models = downloader.list_downloaded_models()
                
                download_test_result = {
                    "test": "model_download",
                    "status": "passed",
                    "can_get_download_info": download_info is not None,
                    "download_info_keys": list(download_info.keys()) if download_info else [],
                    "initially_downloaded": len(downloaded_models)
                }
                
                print(f"  ✅ Model download test passed")
                print(f"    Can get download info: {download_info is not None}")
                print(f"    Initially downloaded models: {len(downloaded_models)}")
                
        except Exception as e:
            download_test_result = {
                "test": "model_download",
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Model download test failed: {e}")
        
        model_results.append(download_test_result)
        
        model_test_duration = time.time() - model_test_start
        
        # Calculate model test statistics
        passed_model_tests = len([r for r in model_results if r["status"] == "passed"])
        total_model_tests = len(model_results)
        
        model_test_summary = {
            "category": "local_model_tests",
            "total_tests": total_model_tests,
            "passed": passed_model_tests,
            "failed": total_model_tests - passed_model_tests,
            "duration": model_test_duration,
            "success_rate": passed_model_tests / total_model_tests,
            "test_results": model_results
        }
        
        print(f"\n📊 Local Model Tests Summary:")
        print(f"  Total: {total_model_tests}")
        print(f"  Passed: {passed_model_tests}")
        print(f"  Failed: {total_model_tests - passed_model_tests}")
        print(f"  Success Rate: {model_test_summary['success_rate']:.1%}")
        print(f"  Duration: {model_test_duration:.1f}s")
        
        return model_test_summary
    
    def run_all_tests(self, categories: List[str] = None, 
                     include_model_tests: bool = True) -> Dict[str, Any]:
        """Run all test categories"""
        print("🚀 Starting EchoVerse Comprehensive Test Suite")
        print("=" * 80)
        
        overall_start_time = time.time()
        
        # Determine which categories to run
        if categories is None:
            categories = list(TEST_CONFIG.keys())
        
        # Run each test category
        for category in categories:
            if category in TEST_CONFIG:
                category_result = self.run_test_category(
                    category, 
                    TEST_CONFIG[category],
                    timeout=600 if category == "system_tests" else 300
                )
                self.results["test_categories"][category] = category_result
        
        # Run local model tests if requested
        if include_model_tests:
            model_test_result = self.run_local_model_tests()
            self.results["test_categories"]["local_model_tests"] = model_test_result
        
        # Calculate overall statistics
        overall_duration = time.time() - overall_start_time
        
        total_tests = sum(cat["total_tests"] for cat in self.results["test_categories"].values())
        total_passed = sum(cat["passed"] for cat in self.results["test_categories"].values())
        total_failed = sum(cat["failed"] for cat in self.results["test_categories"].values())
        total_skipped = sum(cat.get("skipped", 0) for cat in self.results["test_categories"].values())
        
        self.results["overall_summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "duration": overall_duration,
            "success_rate": total_passed / total_tests if total_tests > 0 else 0,
            "end_time": datetime.now().isoformat()
        }
        
        # Print comprehensive summary
        self._print_final_summary()
        
        return self.results
    
    def _print_final_summary(self):
        """Print final test summary"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        summary = self.results["overall_summary"]
        
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Overall Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Duration: {summary['duration']:.1f}s")
        
        print(f"\n📂 Category Breakdown:")
        for category, result in self.results["test_categories"].items():
            status_icon = "✅" if result["success_rate"] >= 0.8 else "⚠️" if result["success_rate"] >= 0.5 else "❌"
            print(f"  {status_icon} {category}: {result['passed']}/{result['total_tests']} ({result['success_rate']:.1%})")
        
        # Environment info
        if self.results["environment_info"]:
            print(f"\n🖥️ Environment:")
            env = self.results["environment_info"]
            print(f"  Python: {env.get('python_version', 'unknown')}")
            print(f"  Platform: {env.get('platform', 'unknown')}")
            print(f"  CPU Cores: {env.get('cpu_count', 'unknown')}")
            print(f"  Memory: {env.get('memory_gb', 'unknown')}GB")
            if env.get('cuda_available'):
                print(f"  GPU: {env.get('gpu_name', 'unknown')} ({env.get('gpu_count', 1)} device(s))")
            else:
                print(f"  GPU: Not available")
        
        # Overall result
        if summary['success_rate'] >= 0.9:
            print(f"\n🎉 EXCELLENT: Test suite passed with {summary['success_rate']:.1%} success rate!")
        elif summary['success_rate'] >= 0.8:
            print(f"\n✅ GOOD: Test suite mostly passed with {summary['success_rate']:.1%} success rate")
        elif summary['success_rate'] >= 0.6:
            print(f"\n⚠️ FAIR: Test suite had mixed results with {summary['success_rate']:.1%} success rate")
        else:
            print(f"\n❌ POOR: Test suite had significant failures with {summary['success_rate']:.1%} success rate")
    
    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"📄 Test results saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return ""


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="EchoVerse Comprehensive Test Runner")
    parser.add_argument("--categories", nargs="+", 
                       choices=list(TEST_CONFIG.keys()) + ["all"],
                       default=["all"],
                       help="Test categories to run")
    parser.add_argument("--no-model-tests", action="store_true",
                       help="Skip local model tests")
    parser.add_argument("--save-results", action="store_true",
                       help="Save results to JSON file")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick subset of tests")
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = TestRunner()
    
    # Determine categories to run
    if args.quick:
        categories = ["unit_tests", "integration_tests"]
        include_model_tests = False
    elif "all" in args.categories:
        categories = None  # Run all categories
        include_model_tests = not args.no_model_tests
    else:
        categories = args.categories
        include_model_tests = not args.no_model_tests
    
    # Run tests
    results = runner.run_all_tests(
        categories=categories,
        include_model_tests=include_model_tests
    )
    
    # Save results if requested
    if args.save_results:
        runner.save_results()
    
    # Exit with appropriate code
    success_rate = results["overall_summary"]["success_rate"]
    sys.exit(0 if success_rate >= 0.8 else 1)


if __name__ == "__main__":
    main()