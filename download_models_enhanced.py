#!/usr/bin/env python3
"""
Enhanced Model Downloader and Compatibility Checker for EchoVerse
Downloads and tests all supported models for compatibility with the current system.
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Add app directory to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from model_manager import get_model_registry, ModelSpec, HardwareRequirement
    from model_downloader import ModelDownloader
    from environment_checker import EnvironmentChecker
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're running from the project root directory.")
    sys.exit(1)