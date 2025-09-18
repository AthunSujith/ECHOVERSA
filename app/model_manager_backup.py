"""
Local Model Management System for EchoVerse
Handles model selection, hardware mapping, and capability assessment
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import json


class ModelType(Enum):
    """Model architecture types"""
    MPT = "mpt"
    FALCON = "falcon"
    GPT2 = "gpt2"
    LLAMA = "llama"
    PHI = "phi"
    TINYLLAMA = "tinyllama"
    STABLELM = "stablelm"


class QuantizationType(Enum):
    """Model quantization formats"""
    FULL_PRECISION = "fp16"
    GGML_Q4 = "ggml_q4"
    GGML_Q8 = "ggml_q8"
    GGUF_Q4 = "gguf_q4"
    GGUF_Q8 = "gguf_q8"
    BITSANDBYTES_4BIT = "bnb_4bit"
    BITSANDBYTES_8BIT = "bnb_8bit"


class HardwareRequirement(Enum):
    """Hardware requirement categories"""
    GPU_HIGH = "gpu_high"  # ≥24GB VRAM
    GPU_MID = "gpu_mid"    # 8-16GB VRAM
    GPU_LOW = "gpu_low"    # 4-8GB VRAM
    CPU_ONLY = "cpu_only"  # CPU with sufficient RAM


@dataclass
class ModelSpec:
    """Specification for a supported model"""
    name: str
    model_type: ModelType
    size_gb: float
    min_vram_gb: Optional[int]
    min_ram_gb: int
    hardware_req: HardwareRequirement
    quantization: QuantizationType
    repo_id: str
    quality_score: int  # 1-10 scale
    speed_score: int    # 1-10 scale (higher = faster)
    description: str
    license: str
    gated: bool = False
    
    @property
    def is_cpu_compatible(self) -> bool:
        """Check if model can run on CPU"""
        return self.hardware_req == HardwareRequirement.CPU_ONLY or \
               self.quantization in [QuantizationType.GGML_Q4, QuantizationType.GGML_Q8, 
                                   QuantizationType.GGUF_Q4, QuantizationType.GGUF_Q8]
    
    @property
    def requires_gpu(self) -> bool:
        """Check if model requires GPU"""
        return self.hardware_req in [HardwareRequirement.GPU_HIGH, 
                                   HardwareRequirement.GPU_MID, 
                                   HardwareRequirement.GPU_LOW]


class ModelRegistry:
    """Registry of supported models with hardware mapping"""
    
    def __init__(self):
        self._models = self._initialize_model_specs()
    
    def _initialize_model_specs(self) -> Dict[str, ModelSpec]:
        """Initialize the registry with supported model specifications"""
        models = {}
        
        # MPT-7B Instruct variants
        models["mpt-7b-instruct"] = ModelSpec(
            name="mpt-7b-instruct",
            model_type=ModelType.MPT,
            size_gb=13.5,
            min_vram_gb=16,
            min_ram_gb=32,
            hardware_req=HardwareRequirement.GPU_MID,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="mosaicml/mpt-7b-instruct",
            quality_score=8,
            speed_score=7,
            description="High-quality instruction-following model",
            license="Apache-2.0"
        )
        
        models["mpt-7b-instruct-gguf-q4"] = ModelSpec(
            name="mpt-7b-instruct-gguf-q4",
            model_type=ModelType.MPT,
            size_gb=4.2,
            min_vram_gb=None,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/mpt-7B-instruct-GGUF",
            quality_score=7,
            speed_score=8,
            description="CPU-optimized quantized MPT-7B",
            license="Apache-2.0"
        )
        
        # Falcon-7B Instruct variants
        models["falcon-7b-instruct"] = ModelSpec(
            name="falcon-7b-instruct",
            model_type=ModelType.FALCON,
            size_gb=14.2,
            min_vram_gb=16,
            min_ram_gb=32,
            hardware_req=HardwareRequirement.GPU_MID,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="tiiuae/falcon-7b-instruct",
            quality_score=8,
            speed_score=6,
            description="Strong general-purpose instruction model",
            license="Apache-2.0"
        )
        
        models["falcon-7b-instruct-gguf-q4"] = ModelSpec(
            name="falcon-7b-instruct-gguf-q4",
            model_type=ModelType.FALCON,
            size_gb=4.1,
            min_vram_gb=None,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/falcon-7b-instruct-GGUF",
            quality_score=7,
            speed_score=7,
            description="CPU-optimized quantized Falcon-7B",
            license="Apache-2.0"
        )
        
        # GPT-2 for testing (lightweight)
        models["gpt2"] = ModelSpec(
            name="gpt2",
            model_type=ModelType.GPT2,
            size_gb=0.5,
            min_vram_gb=None,
            min_ram_gb=2,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="gpt2",
            quality_score=4,
            speed_score=10,
            description="Lightweight model for testing and development",
            license="MIT"
        )
        
        # Additional quantized variants for different hardware configs
        models["mpt-7b-instruct-4bit"] = ModelSpec(
            name="mpt-7b-instruct-4bit",
            model_type=ModelType.MPT,
            size_gb=4.5,
            min_vram_gb=6,
            min_ram_gb=16,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.BITSANDBYTES_4BIT,
            repo_id="mosaicml/mpt-7b-instruct",
            quality_score=7,
            speed_score=8,
            description="4-bit quantized MPT-7B for lower VRAM",
            license="Apache-2.0"
        )
        
        # Phi-2 (2.7B) - Strong reasoning for its size
        models["phi-2"] = ModelSpec(
            name="phi-2",
            model_type=ModelType.PHI,
            size_gb=5.4,
            min_vram_gb=8,
            min_ram_gb=16,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="microsoft/phi-2",
            quality_score=8,
            speed_score=7,
            description="Strong reasoning capabilities for 2.7B parameters, trained on curated high-quality data",
            license="MIT"
        )
        
        models["phi-2-gguf-q4"] = ModelSpec(
            name="phi-2-gguf-q4",
            model_type=ModelType.PHI,
            size_gb=1.7,
            min_vram_gb=None,
            min_ram_gb=4,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/phi-2-GGUF",
            quality_score=7,
            speed_score=8,
            description="CPU-optimized quantized Phi-2, excellent reasoning with low resource usage",
            license="MIT"
        )
        
        # TinyLlama (1.1B) - Chat-tuned lightweight model
        models["tinyllama-1.1b-chat"] = ModelSpec(
            name="tinyllama-1.1b-chat",
            model_type=ModelType.TINYLLAMA,
            size_gb=2.2,
            min_vram_gb=4,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            quality_score=6,
            speed_score=9,
            description="Chat-tuned 1.1B model, surprisingly good for its size, designed for lightweight devices",
            license="Apache-2.0"
        )
        
        models["tinyllama-1.1b-chat-gguf-q4"] = ModelSpec(
            name="tinyllama-1.1b-chat-gguf-q4",
            model_type=ModelType.TINYLLAMA,
            size_gb=0.6,
            min_vram_gb=None,
            min_ram_gb=2,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
            quality_score=5,
            speed_score=10,
            description="Ultra-lightweight quantized TinyLlama, perfect for supportive companion apps",
            license="Apache-2.0"
        )
        
        # StableLM 2 Zephyr 1.6B - Chat-focused with empathetic output
        models["stablelm-2-zephyr-1.6b"] = ModelSpec(
            name="stablelm-2-zephyr-1.6b",
            model_type=ModelType.STABLELM,
            size_gb=3.2,
            min_vram_gb=4,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="stabilityai/stablelm-2-zephyr-1_6b",
            quality_score=7,
            speed_score=8,
            description="Chat-focused model with empathetic output, tuned for instruction following",
            license="Apache-2.0"
        )
        
        models["stablelm-2-zephyr-1.6b-gguf-q4"] = ModelSpec(
            name="stablelm-2-zephyr-1.6b-gguf-q4",
            model_type=ModelType.STABLELM,
            size_gb=1.0,
            min_vram_gb=None,
            min_ram_gb=3,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/stablelm-2-zephyr-1_6b-GGUF",
            quality_score=6,
            speed_score=9,
            description="CPU-optimized StableLM Zephyr, excellent for empathetic companion applications",
            license="Apache-2.0"
        )
        
        # Phi-2 (2.7B) - Strong reasoning for its size
        models["phi-2"] = ModelSpec(
            name="phi-2",
            model_type=ModelType.PHI,
            size_gb=5.4,
            min_vram_gb=8,
            min_ram_gb=16,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="microsoft/phi-2",
            quality_score=8,
            speed_score=7,
            description="Strong reasoning capabilities for 2.7B parameters, trained on curated high-quality data",
            license="MIT"
        )
        
        models["phi-2-gguf-q4"] = ModelSpec(
            name="phi-2-gguf-q4",
            model_type=ModelType.PHI,
            size_gb=1.7,
            min_vram_gb=None,
            min_ram_gb=4,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/phi-2-GGUF",
            quality_score=7,
            speed_score=8,
            description="CPU-optimized quantized Phi-2, excellent reasoning with low resource usage",
            license="MIT"
        )
        
        # TinyLlama (1.1B) - Chat-tuned lightweight model
        models["tinyllama-1.1b-chat"] = ModelSpec(
            name="tinyllama-1.1b-chat",
            model_type=ModelType.TINYLLAMA,
            size_gb=2.2,
            min_vram_gb=4,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            quality_score=6,
            speed_score=9,
            description="Chat-tuned 1.1B model, surprisingly good for its size, designed for lightweight devices",
            license="Apache-2.0"
        )
        
        models["tinyllama-1.1b-chat-gguf-q4"] = ModelSpec(
            name="tinyllama-1.1b-chat-gguf-q4",
            model_type=ModelType.TINYLLAMA,
            size_gb=0.6,
            min_vram_gb=None,
            min_ram_gb=2,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
            quality_score=5,
            speed_score=10,
            description="Ultra-lightweight quantized TinyLlama, perfect for supportive companion apps",
            license="Apache-2.0"
        )
        
        # StableLM 2 Zephyr 1.6B - Chat-focused with empathetic output
        models["stablelm-2-zephyr-1.6b"] = ModelSpec(
            name="stablelm-2-zephyr-1.6b",
            model_type=ModelType.STABLELM,
            size_gb=3.2,
            min_vram_gb=4,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.GPU_LOW,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="stabilityai/stablelm-2-zephyr-1_6b",
            quality_score=7,
            speed_score=8,
            description="Chat-focused model with empathetic output, tuned for instruction following",
            license="Apache-2.0"
        )
        
        models["stablelm-2-zephyr-1.6b-gguf-q4"] = ModelSpec(
            name="stablelm-2-zephyr-1.6b-gguf-q4",
            model_type=ModelType.STABLELM,
            size_gb=1.0,
            min_vram_gb=None,
            min_ram_gb=3,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="TheBloke/stablelm-2-zephyr-1_6b-GGUF",
            quality_score=6,
            speed_score=9,
            description="CPU-optimized StableLM Zephyr, excellent for empathetic companion applications",
            license="Apache-2.0"
        )
        
        return models
    
    def get_model(self, name: str) -> Optional[ModelSpec]:
        """Get model specification by name"""
        return self._models.get(name)
    
    def get_all_models(self) -> Dict[str, ModelSpec]:
        """Get all registered models"""
        return self._models.copy()
    
    def get_models_by_hardware(self, hardware_req: HardwareRequirement) -> List[ModelSpec]:
        """Get models compatible with specific hardware requirement"""
        return [model for model in self._models.values() 
                if model.hardware_req == hardware_req]
    
    def get_cpu_compatible_models(self) -> List[ModelSpec]:
        """Get all CPU-compatible models"""
        return [model for model in self._models.values() if model.is_cpu_compatible]
    
    def get_gpu_models(self, min_vram_gb: int) -> List[ModelSpec]:
        """Get GPU models that fit within VRAM constraint"""
        return [model for model in self._models.values() 
                if model.requires_gpu and (model.min_vram_gb or 0) <= min_vram_gb]
    
    def get_models_by_type(self, model_type: ModelType) -> List[ModelSpec]:
        """Get models of specific architecture type"""
        return [model for model in self._models.values() 
                if model.model_type == model_type]
    
    def get_capability_matrix(self) -> Dict[str, Dict[str, any]]:
        """Generate capability matrix for all models"""
        matrix = {}
        for name, model in self._models.items():
            matrix[name] = {
                "quality_score": model.quality_score,
                "speed_score": model.speed_score,
                "size_gb": model.size_gb,
                "hardware_req": model.hardware_req.value,
                "cpu_compatible": model.is_cpu_compatible,
                "gpu_required": model.requires_gpu,
                "min_vram_gb": model.min_vram_gb,
                "min_ram_gb": model.min_ram_gb,
                "quantization": model.quantization.value,
                "license": model.license,
                "gated": model.gated
            }
        return matrix
    
    def recommend_models(self, available_vram_gb: Optional[int] = None, 
                        available_ram_gb: int = 8, 
                        prefer_quality: bool = True) -> List[Tuple[ModelSpec, str]]:
        """Recommend models based on available hardware"""
        recommendations = []
        
        # Filter models by hardware constraints
        compatible_models = []
        for model in self._models.values():
            # Check RAM requirement
            if model.min_ram_gb > available_ram_gb:
                continue
                
            # Check VRAM requirement for GPU models
            if model.requires_gpu:
                if available_vram_gb is None or (model.min_vram_gb or 0) > available_vram_gb:
                    continue
            
            compatible_models.append(model)
        
        # Sort by preference (quality vs speed)
        if prefer_quality:
            compatible_models.sort(key=lambda m: (m.quality_score, m.speed_score), reverse=True)
        else:
            compatible_models.sort(key=lambda m: (m.speed_score, m.quality_score), reverse=True)
        
        # Generate recommendations with reasoning
        for model in compatible_models[:5]:  # Top 5 recommendations
            if model.requires_gpu and available_vram_gb:
                reason = f"GPU model, requires {model.min_vram_gb}GB VRAM (available: {available_vram_gb}GB)"
            elif model.is_cpu_compatible:
                reason = f"CPU-compatible, requires {model.min_ram_gb}GB RAM (available: {available_ram_gb}GB)"
            else:
                reason = "Compatible with current hardware"
            
            recommendations.append((model, reason))
        
        return recommendations
    
    def export_to_json(self, filepath: str) -> None:
        """Export model registry to JSON file"""
        export_data = {}
        for name, model in self._models.items():
            export_data[name] = {
                "name": model.name,
                "model_type": model.model_type.value,
                "size_gb": model.size_gb,
                "min_vram_gb": model.min_vram_gb,
                "min_ram_gb": model.min_ram_gb,
                "hardware_req": model.hardware_req.value,
                "quantization": model.quantization.value,
                "repo_id": model.repo_id,
                "quality_score": model.quality_score,
                "speed_score": model.speed_score,
                "description": model.description,
                "license": model.license,
                "gated": model.gated
            }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)


# Global model registry instance
model_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance"""
    return model_registry