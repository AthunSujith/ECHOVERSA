"""
Tests for the Model Manager module
"""

import unittest
import tempfile
import os
import json
from app.model_manager import (
    ModelRegistry, ModelSpec, ModelType, QuantizationType, 
    HardwareRequirement, get_model_registry
)


class TestModelSpec(unittest.TestCase):
    """Test ModelSpec dataclass functionality"""
    
    def setUp(self):
        self.gpu_model = ModelSpec(
            name="test-gpu-model",
            model_type=ModelType.MPT,
            size_gb=10.0,
            min_vram_gb=16,
            min_ram_gb=32,
            hardware_req=HardwareRequirement.GPU_MID,
            quantization=QuantizationType.FULL_PRECISION,
            repo_id="test/gpu-model",
            quality_score=8,
            speed_score=7,
            description="Test GPU model",
            license="Apache-2.0"
        )
        
        self.cpu_model = ModelSpec(
            name="test-cpu-model",
            model_type=ModelType.FALCON,
            size_gb=4.0,
            min_vram_gb=None,
            min_ram_gb=8,
            hardware_req=HardwareRequirement.CPU_ONLY,
            quantization=QuantizationType.GGUF_Q4,
            repo_id="test/cpu-model",
            quality_score=6,
            speed_score=9,
            description="Test CPU model",
            license="MIT"
        )
    
    def test_cpu_compatibility(self):
        """Test CPU compatibility detection"""
        self.assertFalse(self.gpu_model.is_cpu_compatible)
        self.assertTrue(self.cpu_model.is_cpu_compatible)
    
    def test_gpu_requirement(self):
        """Test GPU requirement detection"""
        self.assertTrue(self.gpu_model.requires_gpu)
        self.assertFalse(self.cpu_model.requires_gpu)


class TestModelRegistry(unittest.TestCase):
    """Test ModelRegistry functionality"""
    
    def setUp(self):
        self.registry = ModelRegistry()
    
    def test_model_retrieval(self):
        """Test getting models by name"""
        mpt_model = self.registry.get_model("mpt-7b-instruct")
        self.assertIsNotNone(mpt_model)
        self.assertEqual(mpt_model.name, "mpt-7b-instruct")
        self.assertEqual(mpt_model.model_type, ModelType.MPT)
        
        # Test non-existent model
        self.assertIsNone(self.registry.get_model("non-existent-model"))
    
    def test_get_all_models(self):
        """Test getting all models"""
        all_models = self.registry.get_all_models()
        self.assertGreater(len(all_models), 0)
        
        # Check that expected models are present
        expected_models = ["mpt-7b-instruct", "falcon-7b-instruct", "gpt2"]
        for model_name in expected_models:
            self.assertIn(model_name, all_models)
    
    def test_get_models_by_hardware(self):
        """Test filtering models by hardware requirement"""
        cpu_models = self.registry.get_models_by_hardware(HardwareRequirement.CPU_ONLY)
        self.assertGreater(len(cpu_models), 0)
        
        for model in cpu_models:
            self.assertEqual(model.hardware_req, HardwareRequirement.CPU_ONLY)
        
        gpu_mid_models = self.registry.get_models_by_hardware(HardwareRequirement.GPU_MID)
        self.assertGreater(len(gpu_mid_models), 0)
        
        for model in gpu_mid_models:
            self.assertEqual(model.hardware_req, HardwareRequirement.GPU_MID)
    
    def test_get_cpu_compatible_models(self):
        """Test getting CPU-compatible models"""
        cpu_compatible = self.registry.get_cpu_compatible_models()
        self.assertGreater(len(cpu_compatible), 0)
        
        for model in cpu_compatible:
            self.assertTrue(model.is_cpu_compatible)
    
    def test_get_gpu_models(self):
        """Test getting GPU models within VRAM constraint"""
        # Test with high VRAM
        high_vram_models = self.registry.get_gpu_models(24)
        self.assertGreater(len(high_vram_models), 0)
        
        # Test with low VRAM
        low_vram_models = self.registry.get_gpu_models(8)
        for model in low_vram_models:
            self.assertTrue(model.requires_gpu)
            self.assertLessEqual(model.min_vram_gb or 0, 8)
    
    def test_get_models_by_type(self):
        """Test filtering models by architecture type"""
        mpt_models = self.registry.get_models_by_type(ModelType.MPT)
        self.assertGreater(len(mpt_models), 0)
        
        for model in mpt_models:
            self.assertEqual(model.model_type, ModelType.MPT)
        
        gpt2_models = self.registry.get_models_by_type(ModelType.GPT2)
        self.assertGreater(len(gpt2_models), 0)
        
        for model in gpt2_models:
            self.assertEqual(model.model_type, ModelType.GPT2)
    
    def test_capability_matrix(self):
        """Test capability matrix generation"""
        matrix = self.registry.get_capability_matrix()
        self.assertGreater(len(matrix), 0)
        
        # Check matrix structure for a known model
        self.assertIn("gpt2", matrix)
        gpt2_info = matrix["gpt2"]
        
        required_keys = [
            "quality_score", "speed_score", "size_gb", "hardware_req",
            "cpu_compatible", "gpu_required", "min_vram_gb", "min_ram_gb",
            "quantization", "license", "gated"
        ]
        
        for key in required_keys:
            self.assertIn(key, gpt2_info)
    
    def test_model_recommendations(self):
        """Test model recommendation system"""
        # Test CPU-only recommendations
        cpu_recs = self.registry.recommend_models(available_vram_gb=None, available_ram_gb=16)
        self.assertGreater(len(cpu_recs), 0)
        
        for model, reason in cpu_recs:
            self.assertLessEqual(model.min_ram_gb, 16)
        
        # Test GPU recommendations
        gpu_recs = self.registry.recommend_models(available_vram_gb=16, available_ram_gb=32)
        self.assertGreater(len(gpu_recs), 0)
        
        # Test quality vs speed preference
        quality_recs = self.registry.recommend_models(
            available_vram_gb=16, available_ram_gb=32, prefer_quality=True
        )
        speed_recs = self.registry.recommend_models(
            available_vram_gb=16, available_ram_gb=32, prefer_quality=False
        )
        
        # Should get different ordering
        if len(quality_recs) > 1 and len(speed_recs) > 1:
            self.assertNotEqual(quality_recs[0][0].name, speed_recs[0][0].name)
    
    def test_export_to_json(self):
        """Test JSON export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.registry.export_to_json(temp_path)
            
            # Verify file was created and contains valid JSON
            self.assertTrue(os.path.exists(temp_path))
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            self.assertGreater(len(data), 0)
            
            # Check structure of exported data
            for model_name, model_data in data.items():
                required_fields = [
                    "name", "model_type", "size_gb", "hardware_req",
                    "quantization", "repo_id", "quality_score", "speed_score",
                    "description", "license", "gated"
                ]
                
                for field in required_fields:
                    self.assertIn(field, model_data)
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGlobalRegistry(unittest.TestCase):
    """Test global registry access"""
    
    def test_get_model_registry(self):
        """Test global registry access function"""
        registry = get_model_registry()
        self.assertIsInstance(registry, ModelRegistry)
        
        # Should return the same instance
        registry2 = get_model_registry()
        self.assertIs(registry, registry2)


if __name__ == '__main__':
    unittest.main()