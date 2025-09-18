#!/usr/bin/env python3
"""
EchoVerse Environment Check Script
Standalone script for system capability reporting
"""

import sys
import os
import argparse
import json

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from environment_checker import EnvironmentChecker, check_environment, print_environment_report


def export_report_json(report, filepath):
    """Export environment report to JSON file"""
    export_data = {
        "hardware": {
            "cpu_count": report.hardware.cpu_count,
            "cpu_model": report.hardware.cpu_model,
            "total_ram_gb": report.hardware.total_ram_gb,
            "available_ram_gb": report.hardware.available_ram_gb,
            "has_gpu": report.hardware.has_gpu,
            "gpu_count": report.hardware.gpu_count,
            "gpu_names": report.hardware.gpu_names,
            "total_vram_gb": report.hardware.total_vram_gb,
            "available_vram_gb": report.hardware.available_vram_gb,
            "platform": report.hardware.platform,
            "architecture": report.hardware.architecture
        },
        "dependencies": [
            {
                "name": dep.name,
                "available": dep.available,
                "version": dep.version,
                "import_error": dep.import_error
            }
            for dep in report.dependencies
        ],
        "ffmpeg_available": report.ffmpeg_available,
        "ffmpeg_path": report.ffmpeg_path,
        "python_version": report.python_version,
        "recommendations": report.recommendations,
        "warnings": report.warnings,
        "errors": report.errors
    }
    
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Environment report exported to: {filepath}")


def main():
    """Main entry point for environment checker"""
    parser = argparse.ArgumentParser(
        description="EchoVerse Environment and Hardware Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_env.py                    # Print full report
  python check_env.py --json env.json   # Export to JSON
  python check_env.py --quiet           # Only show errors/warnings
  python check_env.py --hardware-only   # Only hardware info
        """
    )
    
    parser.add_argument(
        '--json', 
        metavar='FILE',
        help='Export report to JSON file'
    )
    
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Only show errors and warnings'
    )
    
    parser.add_argument(
        '--hardware-only', 
        action='store_true',
        help='Only show hardware information'
    )
    
    parser.add_argument(
        '--check-model-compatibility',
        metavar='MODEL_NAME',
        help='Check if system can run specific model'
    )
    
    args = parser.parse_args()
    
    # Generate environment report
    try:
        report = check_environment()
    except Exception as e:
        print(f"Error generating environment report: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Handle JSON export
    if args.json:
        try:
            export_report_json(report, args.json)
        except Exception as e:
            print(f"Error exporting to JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Handle quiet mode
    if args.quiet:
        if report.errors:
            print("ERRORS:")
            for error in report.errors:
                print(f"  • {error}")
        
        if report.warnings:
            print("WARNINGS:")
            for warning in report.warnings:
                print(f"  • {warning}")
        
        if not report.errors and not report.warnings:
            print("✅ No errors or warnings detected")
        
        return
    
    # Handle hardware-only mode
    if args.hardware_only:
        print("HARDWARE INFORMATION")
        print("=" * 40)
        print(f"Platform: {report.hardware.platform} ({report.hardware.architecture})")
        print(f"CPU: {report.hardware.cpu_model}")
        print(f"CPU Cores: {report.hardware.cpu_count}")
        print(f"RAM: {report.hardware.total_ram_gb:.1f}GB total, {report.hardware.available_ram_gb:.1f}GB available")
        
        if report.hardware.has_gpu:
            print(f"GPU Count: {report.hardware.gpu_count}")
            for i, gpu_name in enumerate(report.hardware.gpu_names):
                print(f"GPU {i}: {gpu_name}")
            if report.hardware.total_vram_gb:
                print(f"VRAM: {report.hardware.total_vram_gb:.1f}GB total, {report.hardware.available_vram_gb:.1f}GB available")
        else:
            print("GPU: None detected")
        
        return
    
    # Handle model compatibility check
    if args.check_model_compatibility:
        try:
            from model_manager import get_model_registry
            
            registry = get_model_registry()
            model = registry.get_model(args.check_model_compatibility)
            
            if not model:
                print(f"❌ Model '{args.check_model_compatibility}' not found in registry")
                available_models = list(registry.get_all_models().keys())
                print(f"Available models: {', '.join(available_models)}")
                return
            
            print(f"MODEL COMPATIBILITY CHECK: {model.name}")
            print("=" * 50)
            
            # Check RAM requirement
            ram_ok = report.hardware.total_ram_gb >= model.min_ram_gb
            ram_status = "✅" if ram_ok else "❌"
            print(f"RAM: {ram_status} {report.hardware.total_ram_gb:.1f}GB available, {model.min_ram_gb}GB required")
            
            # Check VRAM requirement (if GPU model)
            if model.requires_gpu:
                if not report.hardware.has_gpu:
                    print(f"GPU: ❌ Model requires GPU but none detected")
                    vram_ok = False
                elif model.min_vram_gb and report.hardware.total_vram_gb:
                    vram_ok = report.hardware.total_vram_gb >= model.min_vram_gb
                    vram_status = "✅" if vram_ok else "❌"
                    print(f"VRAM: {vram_status} {report.hardware.total_vram_gb:.1f}GB available, {model.min_vram_gb}GB required")
                else:
                    print(f"VRAM: ⚠️  Cannot determine VRAM requirements")
                    vram_ok = True  # Assume OK if we can't determine
            else:
                vram_ok = True
                print(f"GPU: ✅ CPU-compatible model")
            
            # Overall compatibility
            compatible = ram_ok and vram_ok
            status = "✅ COMPATIBLE" if compatible else "❌ NOT COMPATIBLE"
            print(f"\nOverall: {status}")
            
            if not compatible:
                print("\nSuggestions:")
                if not ram_ok:
                    print(f"  • Increase system RAM to at least {model.min_ram_gb}GB")
                if not vram_ok:
                    print(f"  • Use a GPU with at least {model.min_vram_gb}GB VRAM")
                    print(f"  • Consider CPU-compatible quantized variants")
        
        except ImportError as e:
            print(f"Error importing model registry: {e}")
            sys.exit(1)
        
        return
    
    # Default: print full report
    checker = EnvironmentChecker()
    checker.print_report(report)
    
    # Exit with error code if there are errors
    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()