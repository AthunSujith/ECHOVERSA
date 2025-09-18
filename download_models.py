#!/usr/bin/env python3
"""
EchoVerse Model Download and Management Script
Comprehensive script for downloading, managing, and selecting models
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.model_manager import get_model_registry
from app.model_downloader import ModelDownloader, DownloadProgress
from app.model_selector import ModelSelector, ModelSelectionCriteria, SelectionStrategy
from app.model_access_control import AccessControlManager
from app.environment_checker import check_environment


def print_progress(progress: DownloadProgress):
    """Print download progress"""
    if progress.status == 'downloading':
        percent = (progress.downloaded / progress.total_size * 100) if progress.total_size > 0 else 0
        speed_mb = progress.speed_mbps
        eta_str = f"{progress.eta_seconds}s" if progress.eta_seconds else "unknown"
        
        print(f"\rDownloading: {percent:.1f}% | {speed_mb:.1f} MB/s | ETA: {eta_str}", end='', flush=True)
    elif progress.status == 'completed':
        print(f"\n✅ Download completed: {progress.model_name}")
    elif progress.status == 'failed':
        print(f"\n❌ Download failed: {progress.error}")
    elif progress.status == 'verifying':
        print(f"\n🔍 Verifying model integrity...")


def list_models(args):
    """List available models"""
    registry = get_model_registry()
    downloader = ModelDownloader()
    
    all_models = registry.get_all_models()
    downloaded_models = set(downloader.list_downloaded_models())
    
    print("AVAILABLE MODELS")
    print("=" * 80)
    
    for name, model in all_models.items():
        status = "✅ Downloaded" if name in downloaded_models else "⬇️  Available"
        gpu_req = "GPU" if model.requires_gpu else "CPU"
        
        print(f"{status} | {name}")
        print(f"    Size: {model.size_gb:.1f}GB | Quality: {model.quality_score}/10 | Speed: {model.speed_score}/10")
        print(f"    Hardware: {gpu_req} | RAM: {model.min_ram_gb}GB | VRAM: {model.min_vram_gb or 'N/A'}GB")
        print(f"    Repository: {model.repo_id}")
        print(f"    License: {model.license}")
        print()


def download_model(args):
    """Download a specific model"""
    downloader = ModelDownloader()
    downloader.set_progress_callback(print_progress)
    
    print(f"Downloading model: {args.model}")
    success = downloader.download_model(args.model, force_redownload=args.force)
    
    if success:
        print(f"✅ Successfully downloaded {args.model}")
        
        # Show model path
        model_path = downloader.get_model_path(args.model)
        if model_path:
            print(f"📁 Model location: {model_path}")
    else:
        print(f"❌ Failed to download {args.model}")
        sys.exit(1)


def recommend_models(args):
    """Get model recommendations"""
    selector = ModelSelector()
    
    print("MODEL RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = selector.get_model_recommendations(count=args.count or 5)
    
    for i, (candidate, explanation) in enumerate(recommendations, 1):
        print(f"{i}. {candidate.model_spec.name}")
        print(f"   {explanation}")
        print(f"   Compatibility: {candidate.compatibility_score:.1f}/100")
        print(f"   Selection Score: {candidate.selection_score:.1f}/100")
        if candidate.issues:
            print(f"   ⚠️  Issues: {'; '.join(candidate.issues[:2])}")
        print()


def select_best_model(args):
    """Select and optionally download the best model"""
    selector = ModelSelector()
    
    # Create selection criteria
    criteria = ModelSelectionCriteria(
        strategy=SelectionStrategy(args.strategy) if args.strategy else SelectionStrategy.BALANCED,
        max_size_gb=args.max_size,
        prefer_quantized=args.prefer_quantized,
        allow_download=not args.no_download,
        min_quality_score=args.min_quality or 5
    )
    
    print("Analyzing system and selecting best model...")
    best_candidate = selector.select_best_model(criteria)
    
    if not best_candidate:
        print("❌ No suitable models found for your system")
        sys.exit(1)
    
    selector.print_selection_report(best_candidate)
    
    # Download if requested and not already downloaded
    if args.download and not best_candidate.is_downloaded:
        print(f"\nDownloading selected model: {best_candidate.model_spec.name}")
        downloader = ModelDownloader()
        downloader.set_progress_callback(print_progress)
        
        success = downloader.download_model(best_candidate.model_spec.name)
        if not success:
            print("❌ Download failed")
            sys.exit(1)


def check_access(args):
    """Check access to gated models"""
    access_manager = AccessControlManager()
    
    if args.model:
        # Check specific model
        status = access_manager.check_repository_access(args.model, force_refresh=True)
        
        print(f"ACCESS STATUS: {args.model}")
        print("=" * 40)
        print(f"Repository: {status.repo_id}")
        print(f"Gated: {'Yes' if status.is_gated else 'No'}")
        print(f"Has Access: {'Yes' if status.has_access else 'No'}")
        print(f"Requires Auth: {'Yes' if status.requires_auth else 'No'}")
        
        if status.access_error:
            print(f"Error: {status.access_error}")
        
        if status.is_gated and not status.has_access:
            print("\nGuidance:")
            guidance = access_manager.get_license_guidance(args.model)
            for step in guidance.get("steps", []):
                print(f"  {step}")
    else:
        # Generate access report
        report = access_manager.generate_access_report()
        
        print("ACCESS REPORT")
        print("=" * 40)
        print(f"Total Models: {report['total_models']}")
        print(f"Accessible: {report['accessible_models']}")
        print(f"Gated: {report['gated_models']}")
        print(f"License Accepted: {report['license_accepted']}")
        
        if report['access_issues']:
            print("\nAccess Issues:")
            for issue in report['access_issues']:
                print(f"  • {issue['model']}: {issue['error']}")


def manage_models(args):
    """Manage downloaded models"""
    downloader = ModelDownloader()
    
    if args.action == 'list':
        downloaded = downloader.list_downloaded_models()
        size_info = downloader.get_download_size_info()
        
        print("DOWNLOADED MODELS")
        print("=" * 40)
        
        total_size = 0
        for model_name in downloaded:
            size_gb = size_info.get(model_name, 0)
            total_size += size_gb
            print(f"📦 {model_name} ({size_gb:.1f}GB)")
        
        print(f"\nTotal Size: {total_size:.1f}GB")
    
    elif args.action == 'delete':
        if not args.model:
            print("Error: --model required for delete action")
            sys.exit(1)
        
        print(f"Deleting model: {args.model}")
        success = downloader.delete_model(args.model)
        
        if not success:
            sys.exit(1)
    
    elif args.action == 'info':
        if not args.model:
            print("Error: --model required for info action")
            sys.exit(1)
        
        registry = get_model_registry()
        model_spec = registry.get_model(args.model)
        
        if not model_spec:
            print(f"Model {args.model} not found")
            sys.exit(1)
        
        model_path = downloader.get_model_path(args.model)
        
        print(f"MODEL INFO: {args.model}")
        print("=" * 40)
        print(f"Repository: {model_spec.repo_id}")
        print(f"Size: {model_spec.size_gb:.1f}GB")
        print(f"Type: {model_spec.model_type.value}")
        print(f"Quantization: {model_spec.quantization.value}")
        print(f"Quality Score: {model_spec.quality_score}/10")
        print(f"Speed Score: {model_spec.speed_score}/10")
        print(f"License: {model_spec.license}")
        print(f"Downloaded: {'Yes' if model_path else 'No'}")
        
        if model_path:
            print(f"Path: {model_path}")


def setup_wizard(args):
    """Interactive setup wizard"""
    print("🚀 EchoVerse Model Setup Wizard")
    print("=" * 40)
    
    # Check environment
    print("1. Checking system environment...")
    env_report = check_environment()
    
    print(f"   CPU: {env_report.hardware.cpu_count} cores")
    print(f"   RAM: {env_report.hardware.total_ram_gb:.1f}GB")
    print(f"   GPU: {'Yes' if env_report.hardware.has_gpu else 'No'}")
    
    if env_report.errors:
        print("   ❌ Critical errors found:")
        for error in env_report.errors:
            print(f"      • {error}")
        print("   Please resolve these issues before continuing.")
        return
    
    # Select model
    print("\n2. Selecting optimal model...")
    selector = ModelSelector()
    
    # Ask user for preferences
    print("\nPreferences:")
    strategy_input = input("   Strategy (quality/speed/balanced/minimal) [balanced]: ").strip().lower()
    strategy_map = {
        'quality': SelectionStrategy.QUALITY_FIRST,
        'speed': SelectionStrategy.SPEED_FIRST,
        'balanced': SelectionStrategy.BALANCED,
        'minimal': SelectionStrategy.MINIMAL_RESOURCES
    }
    strategy = strategy_map.get(strategy_input, SelectionStrategy.BALANCED)
    
    max_size_input = input("   Maximum model size in GB [no limit]: ").strip()
    max_size = float(max_size_input) if max_size_input else None
    
    criteria = ModelSelectionCriteria(
        strategy=strategy,
        max_size_gb=max_size,
        prefer_quantized=True,
        allow_download=True
    )
    
    best_candidate = selector.select_best_model(criteria)
    
    if not best_candidate:
        print("   ❌ No suitable models found")
        return
    
    print(f"\n   Recommended: {best_candidate.model_spec.name}")
    print(f"   Size: {best_candidate.model_spec.size_gb:.1f}GB")
    print(f"   Quality: {best_candidate.model_spec.quality_score}/10")
    print(f"   Compatibility: {best_candidate.compatibility_score:.1f}/100")
    
    # Download if needed
    if not best_candidate.is_downloaded:
        download_confirm = input(f"\n   Download {best_candidate.model_spec.name}? (y/N): ").strip().lower()
        
        if download_confirm == 'y':
            print("\n3. Downloading model...")
            downloader = ModelDownloader()
            downloader.set_progress_callback(print_progress)
            
            success = downloader.download_model(best_candidate.model_spec.name)
            
            if success:
                print("\n✅ Setup complete! Your model is ready to use.")
            else:
                print("\n❌ Download failed. Please try again.")
        else:
            print("\n⏭️  Setup complete. You can download the model later with:")
            print(f"   python download_models.py download {best_candidate.model_spec.name}")
    else:
        print("\n✅ Setup complete! Your model is already downloaded and ready.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EchoVerse Model Download and Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_models.py list                    # List all available models
  python download_models.py download gpt2           # Download specific model
  python download_models.py recommend               # Get model recommendations
  python download_models.py select --download       # Select and download best model
  python download_models.py access --model llama-2  # Check access to gated model
  python download_models.py manage list             # List downloaded models
  python download_models.py setup                   # Run interactive setup wizard
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available models')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a specific model')
    download_parser.add_argument('model', help='Model name to download')
    download_parser.add_argument('--force', action='store_true', help='Force re-download')
    
    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Get model recommendations')
    recommend_parser.add_argument('--count', type=int, default=5, help='Number of recommendations')
    
    # Select command
    select_parser = subparsers.add_parser('select', help='Select best model for system')
    select_parser.add_argument('--strategy', choices=['quality', 'speed', 'balanced', 'minimal'],
                              help='Selection strategy')
    select_parser.add_argument('--max-size', type=float, help='Maximum model size in GB')
    select_parser.add_argument('--min-quality', type=int, help='Minimum quality score')
    select_parser.add_argument('--prefer-quantized', action='store_true', help='Prefer quantized models')
    select_parser.add_argument('--no-download', action='store_true', help='Don\'t allow downloads')
    select_parser.add_argument('--download', action='store_true', help='Download selected model')
    
    # Access command
    access_parser = subparsers.add_parser('access', help='Check model access status')
    access_parser.add_argument('--model', help='Specific model to check')
    
    # Manage command
    manage_parser = subparsers.add_parser('manage', help='Manage downloaded models')
    manage_parser.add_argument('action', choices=['list', 'delete', 'info'], help='Management action')
    manage_parser.add_argument('--model', help='Model name for delete/info actions')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Interactive setup wizard')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            list_models(args)
        elif args.command == 'download':
            download_model(args)
        elif args.command == 'recommend':
            recommend_models(args)
        elif args.command == 'select':
            select_best_model(args)
        elif args.command == 'access':
            check_access(args)
        elif args.command == 'manage':
            manage_models(args)
        elif args.command == 'setup':
            setup_wizard(args)
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()