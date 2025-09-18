"""
Integration tests for content generation system with existing data models.
"""

import unittest
import os
import sys

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from content_generator import ContentGenerator
from data_models import ProcessedInput, GeneratedContent, InputType


class TestContentGenerationIntegration(unittest.TestCase):
    """Integration tests for content generation with data models."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = ContentGenerator()
    
    def test_text_input_integration(self):
        """Test complete flow with text input."""
        # Create processed input
        input_data = ProcessedInput(
            content="I'm feeling stressed about work today",
            input_type=InputType.TEXT,
            metadata={"source": "user_input"}
        )
        
        # Generate content
        result = self.generator.generate_support_and_poem(input_data)
        
        # Verify result structure
        self.assertIsInstance(result, GeneratedContent)
        self.assertTrue(len(result.supportive_statement) > 0)
        self.assertTrue(len(result.poem) > 0)
        self.assertIsInstance(result.generation_metadata, dict)
        
        # Verify metadata contains expected fields
        metadata = result.generation_metadata
        self.assertIn("generator", metadata)
        self.assertIn("processing_time", metadata)
        self.assertIn("input_type", metadata)
        self.assertEqual(metadata["input_type"], "text")
    
    def test_audio_input_integration(self):
        """Test complete flow with audio input."""
        input_data = ProcessedInput(
            content="Transcribed audio: I had a difficult conversation today",
            input_type=InputType.AUDIO,
            metadata={"duration": 15.5, "transcribed": True}
        )
        
        result = self.generator.generate_support_and_poem(input_data)
        
        self.assertIsInstance(result, GeneratedContent)
        self.assertEqual(result.generation_metadata["input_type"], "audio")
    
    def test_drawing_input_integration(self):
        """Test complete flow with drawing input."""
        input_data = ProcessedInput(
            content="A drawing showing a person sitting alone under a tree",
            input_type=InputType.DRAWING,
            metadata={"canvas_size": "800x600", "colors_used": ["blue", "green", "brown"]}
        )
        
        result = self.generator.generate_support_and_poem(input_data)
        
        self.assertIsInstance(result, GeneratedContent)
        self.assertEqual(result.generation_metadata["input_type"], "drawing")
    
    def test_data_model_validation(self):
        """Test that generated content passes data model validation."""
        input_data = ProcessedInput(
            content="I'm looking for some encouragement",
            input_type=InputType.TEXT
        )
        
        result = self.generator.generate_support_and_poem(input_data)
        
        # The GeneratedContent constructor should validate the data
        # If this doesn't raise an exception, validation passed
        validated_content = GeneratedContent(
            supportive_statement=result.supportive_statement,
            poem=result.poem,
            generation_metadata=result.generation_metadata
        )
        
        self.assertEqual(validated_content.supportive_statement, result.supportive_statement)
        self.assertEqual(validated_content.poem, result.poem)
    
    def test_generator_availability(self):
        """Test generator availability methods."""
        # Should have at least mock generator available
        available_generators = self.generator.get_available_generators()
        self.assertIn("mock", available_generators)
        
        # Current generator should be set
        current_name = self.generator.get_current_generator_name()
        self.assertIn(current_name, ["mock", "gemini"])
    
    def test_consistent_generation(self):
        """Test that generation is consistent for same input."""
        input_data = ProcessedInput(
            content="Test consistency",
            input_type=InputType.TEXT
        )
        
        result1 = self.generator.generate_support_and_poem(input_data)
        result2 = self.generator.generate_support_and_poem(input_data)
        
        # Mock generator should produce consistent results
        if self.generator.get_current_generator_name() == "mock":
            self.assertEqual(result1.supportive_statement, result2.supportive_statement)
            self.assertEqual(result1.poem, result2.poem)
    
    def test_error_handling_with_invalid_input(self):
        """Test error handling with invalid input data."""
        # This should raise a validation error in ProcessedInput constructor
        with self.assertRaises(ValueError):
            ProcessedInput(
                content="",  # Empty content should fail validation
                input_type=InputType.TEXT
            )
    
    def test_metadata_preservation(self):
        """Test that input metadata is preserved in generation metadata."""
        input_data = ProcessedInput(
            content="Test metadata preservation",
            input_type=InputType.TEXT,
            metadata={"test_key": "test_value", "timestamp": "2024-01-01"}
        )
        
        result = self.generator.generate_support_and_poem(input_data)
        
        # Generation metadata should contain information about the input
        metadata = result.generation_metadata
        self.assertEqual(metadata["input_type"], "text")
        self.assertIn("content_length", metadata)
        self.assertEqual(metadata["content_length"], len(input_data.content))


if __name__ == '__main__':
    unittest.main(verbosity=2)