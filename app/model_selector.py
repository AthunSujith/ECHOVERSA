"""
Runtime Model Selection Logic for EchoVerse
Automatically selects the best available model based on hardware and preferences
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

try:
    from .model_manager import ModelSpec, get_model_registry, HardwareRequirement
    from .environment_checker import EnvironmentChecker, check_environment
    from .model_downloader import ModelDownloader
    from .model_access_control import AccessControlManager
except ImportError:
    from model_manager import ModelSpec, get_model_registry, HardwareRequirement
    from environment_checker import EnvironmentChecker, check_environment
    from model_downloader import ModelDownloader
    from model_access_control import AccessControlManager


class SelectionStrategy(Enum):
    """Model selection strategies"""
    QUALITY_FIRST = "quality_first"
    SPEED_FIRST = "speed_first"
    BALANCED = "balanced"
    MINIMAL_RESOURCES = "minimal_resources"


@dataclass
class ModelSelectionCriteria:
    """Criteria for model selection"""
    strategy: SelectionStrategy = SelectionStrategy.BALANCED
    max_size_gb: Optional[float] = None
    require_local: bool = False
    allow_download: bool = True
    prefer_quantized: bool = False
    min_quality_score: int = 5
    max_load_time_seconds: Optional[float] = None


@dataclass
class ModelCandidate:
    """A candidate model with selection metadata"""
    model_spec: ModelSpec
    compatibility_score: float
    selection_score: float
    is_downloaded: bool
    download_size_gb: float
    estimated_load_time: float
    hardware_match: str
    issues: List[str]


class ModelSelector:
    """Intelligent model selection based on hardware and preferences"""
    
    def __init__(self, cache_dir: str = "download/models", config_dir: str = ".kiro/model_selection"):
        self.registry = get_model_registry()
        self.downloader = ModelDownloader(cache_dir)
        self.access_manager = AccessControlManager()
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.preferences_file = self.config_dir / "preferences.json"
        self.selection_history_file = self.config_dir / "selection_history.json"
        
        # Load user preferences and history
        self.user_preferences = self._load_preferences()
        self.selection_history = self._load_selection_history()
        
        # Cache environment info
        self._env_report = None
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load user preferences for model selection"""
        if not self.preferences_file.exists():
            return {
                "strategy": SelectionStrategy.BALANCED.value,
                "max_size_gb": None,
                "prefer_quantized": True,
                "auto_download": True,
                "quality_threshold": 5
            }
        
        try:
            with open(self.preferences_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_preferences(self) -> None:
        """Save user preferences"""
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def _load_selection_history(self) -> List[Dict[str, Any]]:
        """Load model selection history"""
        if not self.selection_history_file.exists():
            return []
        
        try:
            with open(self.selection_history_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_selection_history(self) -> None:
        """Save model selection history"""
        try:
            # Keep only last 50 selections
            history = self.selection_history[-50:]
            with open(self.selection_history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error saving selection history: {e}")
    
    def _get_environment_report(self):
        """Get cached environment report"""
        if self._env_report is None:
            self._env_report = check_environment()
        return self._env_report
    
    def _calculate_compatibility_score(self, model_spec: ModelSpec) -> Tuple[float, List[str]]:
        """Calculate how compatible a model is with current hardware"""
        env_report = self._get_environment_report()
        issues = []
        score = 0.0
        
        # RAM compatibility (40% of score)
        if model_spec.min_ram_gb <= env_report.hardware.available_ram_gb:
            score += 40.0
        else:
            ram_deficit = model_spec.min_ram_gb - env_report.hardware.available_ram_gb
            score += max(0, 40.0 - (ram_deficit * 10))  # Penalty for RAM shortage
            issues.append(f"Insufficient RAM: need {model_spec.min_ram_gb}GB, have {env_report.hardware.available_ram_gb:.1f}GB")
        
        # GPU compatibility (30% of score)
        if model_spec.requires_gpu:
            if env_report.hardware.has_gpu:
                if model_spec.min_vram_gb and env_report.hardware.total_vram_gb:
                    if model_spec.min_vram_gb <= env_report.hardware.total_vram_gb:
                        score += 30.0
                    else:
                        vram_deficit = model_spec.min_vram_gb - env_report.hardware.total_vram_gb
                        score += max(0, 30.0 - (vram_deficit * 5))
                        issues.append(f"Insufficient VRAM: need {model_spec.min_vram_gb}GB, have {env_report.hardware.total_vram_gb:.1f}GB")
                else:
                    score += 20.0  # GPU available but VRAM unknown
            else:
                issues.append("Model requires GPU but none detected")
        else:
            # CPU-compatible model gets full GPU score
            score += 30.0
        
        # Dependency compatibility (20% of score)
        required_deps = ["torch", "transformers", "accelerate"]
        available_deps = [dep.name for dep in env_report.dependencies if dep.available]
        
        dep_score = sum(20.0 / len(required_deps) for dep in required_deps if dep in available_deps)
        score += dep_score
        
        missing_deps = [dep for dep in required_deps if dep not in available_deps]
        if missing_deps:
            issues.append(f"Missing dependencies: {', '.join(missing_deps)}")
        
        # Size compatibility (10% of score)
        if model_spec.size_gb <= 5.0:  # Small models get bonus
            score += 10.0
        elif model_spec.size_gb <= 15.0:  # Medium models
            score += 7.0
        else:  # Large models
            score += 3.0
        
        return min(100.0, score), issues
    
    def _calculate_selection_score(self, model_spec: ModelSpec, criteria: ModelSelectionCriteria, 
                                 compatibility_score: float, is_downloaded: bool) -> float:
        """Calculate selection score based on criteria and compatibility"""
        base_score = compatibility_score
        
        # Strategy-based scoring
        if criteria.strategy == SelectionStrategy.QUALITY_FIRST:
            base_score += model_spec.quality_score * 5
        elif criteria.strategy == SelectionStrategy.SPEED_FIRST:
            base_score += model_spec.speed_score * 5
        elif criteria.strategy == SelectionStrategy.BALANCED:
            base_score += (model_spec.quality_score + model_spec.speed_score) * 2.5
        elif criteria.strategy == SelectionStrategy.MINIMAL_RESOURCES:
            # Prefer smaller, faster models
            size_penalty = model_spec.size_gb * 2
            base_score = base_score - size_penalty + model_spec.speed_score * 3
        
        # Bonus for already downloaded models
        if is_downloaded:
            base_score += 20.0
        
        # Bonus for quantized models if preferred
        if criteria.prefer_quantized and "gguf" in model_spec.name.lower():
            base_score += 15.0
        
        # Penalty for models that don't meet quality threshold
        if model_spec.quality_score < criteria.min_quality_score:
            base_score -= (criteria.min_quality_score - model_spec.quality_score) * 10
        
        # Size constraints
        if criteria.max_size_gb and model_spec.size_gb > criteria.max_size_gb:
            base_score -= 50.0  # Heavy penalty for oversized models
        
        return max(0.0, base_score)
    
    def _estimate_load_time(self, model_spec: ModelSpec, is_downloaded: bool) -> float:
        """Estimate model loading time in seconds"""
        base_time = model_spec.size_gb * 2.0  # ~2 seconds per GB
        
        # Quantized models load faster
        if "gguf" in model_spec.name.lower() or "4bit" in model_spec.name.lower():
            base_time *= 0.7
        
        # GPU models load faster than CPU
        if model_spec.requires_gpu:
            env_report = self._get_environment_report()
            if env_report.hardware.has_gpu:
                base_time *= 0.8
        
        # Downloaded models load immediately, others need download time
        if not is_downloaded:
            # Estimate download time (assuming 10MB/s)
            download_time = (model_spec.size_gb * 1024) / 10
            base_time += download_time
        
        return base_time
    
    def get_model_candidates(self, criteria: ModelSelectionCriteria) -> List[ModelCandidate]:
        """Get all model candidates with selection metadata"""
        all_models = self.registry.get_all_models()
        downloaded_models = set(self.downloader.list_downloaded_models())
        candidates = []
        
        for model_name, model_spec in all_models.items():
            # Skip models that don't meet basic criteria
            if criteria.require_local and model_name not in downloaded_models:
                continue
            
            if criteria.max_size_gb and model_spec.size_gb > criteria.max_size_gb:
                continue
            
            # Calculate scores
            compatibility_score, issues = self._calculate_compatibility_score(model_spec)
            is_downloaded = model_name in downloaded_models
            selection_score = self._calculate_selection_score(
                model_spec, criteria, compatibility_score, is_downloaded
            )
            
            # Determine hardware match
            env_report = self._get_environment_report()
            if model_spec.requires_gpu and env_report.hardware.has_gpu:
                hardware_match = "GPU"
            elif model_spec.is_cpu_compatible:
                hardware_match = "CPU"
            else:
                hardware_match = "Incompatible"
            
            candidate = ModelCandidate(
                model_spec=model_spec,
                compatibility_score=compatibility_score,
                selection_score=selection_score,
                is_downloaded=is_downloaded,
                download_size_gb=model_spec.size_gb if not is_downloaded else 0.0,
                estimated_load_time=self._estimate_load_time(model_spec, is_downloaded),
                hardware_match=hardware_match,
                issues=issues
            )
            
            candidates.append(candidate)
        
        # Sort by selection score
        candidates.sort(key=lambda c: c.selection_score, reverse=True)
        return candidates
    
    def select_best_model(self, criteria: Optional[ModelSelectionCriteria] = None) -> Optional[ModelCandidate]:
        """Select the best model based on criteria"""
        if criteria is None:
            criteria = ModelSelectionCriteria(
                strategy=SelectionStrategy(self.user_preferences.get("strategy", "balanced")),
                max_size_gb=self.user_preferences.get("max_size_gb"),
                prefer_quantized=self.user_preferences.get("prefer_quantized", True),
                allow_download=self.user_preferences.get("auto_download", True),
                min_quality_score=self.user_preferences.get("quality_threshold", 5)
            )
        
        candidates = self.get_model_candidates(criteria)
        
        if not candidates:
            return None
        
        # Filter out models with critical issues if we have alternatives
        viable_candidates = [c for c in candidates if c.compatibility_score > 50.0]
        if viable_candidates:
            candidates = viable_candidates
        
        best_candidate = candidates[0]
        
        # Record selection
        from datetime import datetime
        self.selection_history.append({
            "timestamp": datetime.now().isoformat(),
            "model_name": best_candidate.model_spec.name,
            "selection_score": best_candidate.selection_score,
            "compatibility_score": best_candidate.compatibility_score,
            "strategy": criteria.strategy.value,
            "was_downloaded": best_candidate.is_downloaded
        })
        self._save_selection_history()
        
        return best_candidate
    
    def get_fallback_hierarchy(self) -> List[str]:
        """Get fallback hierarchy for model selection"""
        env_report = self._get_environment_report()
        hierarchy = []
        
        # Primary: Best GPU model if available
        if env_report.hardware.has_gpu and env_report.hardware.total_vram_gb and env_report.hardware.total_vram_gb >= 8:
            gpu_models = self.registry.get_gpu_models(int(env_report.hardware.total_vram_gb))
            if gpu_models:
                best_gpu = max(gpu_models, key=lambda m: m.quality_score)
                hierarchy.append(best_gpu.name)
        
        # Secondary: Best CPU-compatible quantized model
        cpu_models = self.registry.get_cpu_compatible_models()
        quantized_cpu = [m for m in cpu_models if "gguf" in m.name.lower()]
        if quantized_cpu:
            best_quantized = max(quantized_cpu, key=lambda m: m.quality_score)
            hierarchy.append(best_quantized.name)
        
        # Tertiary: GPT-2 for testing
        if "gpt2" in self.registry.get_all_models():
            hierarchy.append("gpt2")
        
        # Final fallback: Mock generator (handled by content generator)
        hierarchy.append("mock")
        
        return hierarchy
    
    def update_preferences(self, **kwargs) -> None:
        """Update user preferences"""
        self.user_preferences.update(kwargs)
        self._save_preferences()
    
    def get_model_recommendations(self, count: int = 3) -> List[Tuple[ModelCandidate, str]]:
        """Get model recommendations with explanations"""
        criteria = ModelSelectionCriteria(
            strategy=SelectionStrategy.BALANCED,
            allow_download=True
        )
        
        candidates = self.get_model_candidates(criteria)[:count]
        recommendations = []
        
        for candidate in candidates:
            # Generate explanation
            explanation_parts = []
            
            if candidate.is_downloaded:
                explanation_parts.append("Already downloaded")
            else:
                explanation_parts.append(f"Download required ({candidate.download_size_gb:.1f}GB)")
            
            explanation_parts.append(f"Quality: {candidate.model_spec.quality_score}/10")
            explanation_parts.append(f"Speed: {candidate.model_spec.speed_score}/10")
            explanation_parts.append(f"Hardware: {candidate.hardware_match}")
            
            if candidate.issues:
                explanation_parts.append(f"Issues: {len(candidate.issues)}")
            
            explanation = " | ".join(explanation_parts)
            recommendations.append((candidate, explanation))
        
        return recommendations
    
    def print_selection_report(self, candidate: ModelCandidate) -> None:
        """Print detailed selection report"""
        print("=" * 60)
        print("MODEL SELECTION REPORT")
        print("=" * 60)
        
        print(f"Selected Model: {candidate.model_spec.name}")
        print(f"Repository: {candidate.model_spec.repo_id}")
        print(f"Size: {candidate.model_spec.size_gb:.1f}GB")
        print(f"Type: {candidate.model_spec.model_type.value}")
        print(f"Quantization: {candidate.model_spec.quantization.value}")
        
        print(f"\nScores:")
        print(f"  Selection Score: {candidate.selection_score:.1f}/100")
        print(f"  Compatibility: {candidate.compatibility_score:.1f}/100")
        print(f"  Quality: {candidate.model_spec.quality_score}/10")
        print(f"  Speed: {candidate.model_spec.speed_score}/10")
        
        print(f"\nStatus:")
        print(f"  Downloaded: {'Yes' if candidate.is_downloaded else 'No'}")
        print(f"  Hardware Match: {candidate.hardware_match}")
        print(f"  Estimated Load Time: {candidate.estimated_load_time:.1f}s")
        
        if candidate.download_size_gb > 0:
            print(f"  Download Size: {candidate.download_size_gb:.1f}GB")
        
        if candidate.issues:
            print(f"\nIssues:")
            for issue in candidate.issues:
                print(f"  • {issue}")
        
        print("=" * 60)


def create_model_selector(cache_dir: str = "download/models", 
                         config_dir: str = ".kiro/model_selection") -> ModelSelector:
    """Factory function to create ModelSelector"""
    return ModelSelector(cache_dir, config_dir)