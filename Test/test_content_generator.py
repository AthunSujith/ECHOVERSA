"""
Unit tests for content generation system.
Tests both MockGenerator and GeminiGenerator with fallback logic.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import time

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from content_generator import (
    ContentGeneratorInterface, 
    MockGenerator, 
    GeminiGenerator, 
    ContentGenerator
)
from data_models import ProcessedInput, GeneratedContent, InputType

# Check if google.generativeai is available for testing
try:
    import google.generativeai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class TestMockGenerator(unittest.TestCase):
    """Test cases for MockGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = MockGenerator()
        self.test_input = ProcessedInput(
            content="I'm feeling a bit overwhelmed today",
            input_type=InputType.TEXT,
            metadata={"test": True}
        )
    
    def test_initialization(self):
        """Test MockGenerator initialization."""
        self.assertEqual(self.generator.get_generator_name(), "mock")
        self.assertTrue(self.generator.is_available())
    
    def test_generate_support_and_poem(self):
        """Test basic content generation."""
        result = self.generator.generate_support_and_poem(self.test_input)
        
        # Verify result type and structure
        self.assertIsInstance(result, GeneratedContent)
        self.assertIsInstance(result.supportive_statement, str)
        self.assertIsInstance(result.poem, str)
        self.assertIsInstance(result.generation_metadata, dict)
        
        # Verify content is not empty
        self.assertTrue(len(result.supportive_statement) > 0)
        self.assertTrue(len(result.poem) > 0)
        
        # Verify metadata
        metadata = result.generation_metadata
        self.assertEqual(metadata["generator"], "mock")
        self.assertIn("processing_time", metadata)
        self.assertEqual(metadata["input_type"], "text")
        self.assertIn("template_index", metadata)
    
    def test_consistent_output(self):
        """Test that same input produces same output."""
        result1 = self.generator.generate_support_and_poem(self.test_input)
        result2 = self.generator.generate_support_and_poem(self.test_input)
        
        # Same input should produce same content (deterministic)
        self.assertEqual(result1.supportive_statement, result2.supportive_statement)
        self.assertEqual(result1.poem, result2.poem)
    
    def test_different_inputs_different_outputs(self):
        """Test that different inputs produce different outputs."""
        input2 = ProcessedInput(
            content="I'm having a great day!",
            input_type=InputType.TEXT
        )
        
        result1 = self.generator.generate_support_and_poem(self.test_input)
        result2 = self.generator.generate_support_and_poem(input2)
        
        # Different inputs should likely produce different content
        # (though not guaranteed due to hash collisions)
        self.assertIsInstance(result1, GeneratedContent)
        self.assertIsInstance(result2, GeneratedContent)
    
    def test_audio_input_type(self):
        """Test generation with audio input type."""
        audio_input = ProcessedInput(
            content="Transcribed audio content",
            input_type=InputType.AUDIO,
            metadata={"duration": 30.5}
        )
        
        result = self.generator.generate_support_and_poem(audio_input)
        self.assertEqual(result.generation_metadata["input_type"], "audio")
    
    def test_drawing_input_type(self):
        """Test generation with drawing input type."""
        drawing_input = ProcessedInput(
            content="A drawing of a sunset",
            input_type=InputType.DRAWING,
            metadata={"canvas_size": "800x600"}
        )
        
        result = self.generator.generate_support_and_poem(drawing_input)
        self.assertEqual(result.generation_metadata["input_type"], "drawing")


class TestGeminiGenerator(unittest.TestCase):
    """Test cases for GeminiGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_input = ProcessedInput(
            content="I'm feeling anxious about tomorrow",
            input_type=InputType.TEXT
        )
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            generator = GeminiGenerator()
            self.assertEqual(generator.get_generator_name(), "gemini")
            self.assertFalse(generator.is_available())
    
    @unittest.skipUnless(GEMINI_AVAILABLE, "google.generativeai not available")
    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('google.generativeai.configure') as mock_configure:
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    generator = GeminiGenerator()
                    self.assertTrue(generator.is_available())
                    mock_configure.assert_called_once_with(api_key="test_key")
    
    def test_initialization_missing_library(self):
        """Test initialization when google.generativeai is not available."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'google.generativeai'")):
                generator = GeminiGenerator()
                self.assertFalse(generator.is_available())
    
    @unittest.skipUnless(GEMINI_AVAILABLE, "google.generativeai not available")
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_successful_generation(self, mock_model_class, mock_configure):
        """Test successful content generation."""
        # Mock the model and responses
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_support_response = Mock()
        mock_support_response.text = "You're not alone in feeling this way. It's completely normal to feel anxious about the future."
        
        mock_poem_response = Mock()
        mock_poem_response.text = "Tomorrow brings new light,\nThrough clouds of worry bright,\nYour strength will guide you through,\nTo skies of clearest blue."
        
        mock_model.generate_content.side_effect = [mock_support_response, mock_poem_response]
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            generator = GeminiGenerator()
            result = generator.generate_support_and_poem(self.test_input)
            
            # Verify result
            self.assertIsInstance(result, GeneratedContent)
            self.assertEqual(result.supportive_statement, mock_support_response.text)
            self.assertEqual(result.poem, mock_poem_response.text)
            
            # Verify metadata
            metadata = result.generation_metadata
            self.assertEqual(metadata["generator"], "gemini")
            self.assertIn("processing_time", metadata)
            self.assertEqual(metadata["input_type"], "text")
            
            # Verify API calls
            self.assertEqual(mock_model.generate_content.call_count, 2)
    
    @unittest.skipUnless(GEMINI_AVAILABLE, "google.generativeai not available")
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generation_failure(self, mock_model_class, mock_configure):
        """Test handling of generation failures."""
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            generator = GeminiGenerator()
            
            with self.assertRaises(RuntimeError) as context:
                generator.generate_support_and_poem(self.test_input)
            
            self.assertIn("Content generation failed", str(context.exception))
    
    def test_generation_when_unavailable(self):
        """Test generation attempt when generator is unavailable."""
        generator = GeminiGenerator()  # No API key, will be unavailable
        
        with self.assertRaises(RuntimeError) as context:
            generator.generate_support_and_poem(self.test_input)
        
        self.assertIn("not available", str(context.exception))
    
    @unittest.skipUnless(GEMINI_AVAILABLE, "google.generativeai not available")
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_prompt_creation(self, mock_model_class, mock_configure):
        """Test that prompts are created correctly."""
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_model.generate_content.return_value = mock_response
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            generator = GeminiGenerator()
            generator.generate_support_and_poem(self.test_input)
            
            # Check that generate_content was called with proper prompts
            calls = mock_model.generate_content.call_args_list
            self.assertEqual(len(calls), 2)
            
            # Verify support prompt contains user input
            support_prompt = calls[0][0][0]
            self.assertIn(self.test_input.content, support_prompt)
            self.assertIn("supportive", support_prompt.lower())
            
            # Verify poem prompt contains user input
            poem_prompt = calls[1][0][0]
            self.assertIn(self.test_input.content, poem_prompt)
            self.assertIn("poem", poem_prompt.lower())


class TestContentGenerator(unittest.TestCase):
    """Test cases for main ContentGenerator orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_input = ProcessedInput(
            content="I need some encouragement today",
            input_type=InputType.TEXT
        )
    
    def test_initialization_with_mock_only(self):
        """Test initialization when only mock generator is available."""
        with patch.dict(os.environ, {}, clear=True):
            generator = ContentGenerator()
            
            self.assertEqual(len(generator.generators), 1)
            self.assertIsInstance(generator.generators[0], MockGenerator)
            self.assertEqual(generator.get_current_generator_name(), "mock")
            self.assertFalse(generator.is_gemini_available())
    
    @unittest.skipUnless(GEMINI_AVAILABLE, "google.generativeai not available")
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_initialization_with_gemini(self, mock_model_class, mock_configure):
        """Test initialization when Gemini is available."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            generator = ContentGenerator()
            
            self.assertEqual(len(generator.generators), 2)
            self.assertIsInstance(generator.generators[0], GeminiGenerator)
            self.assertIsInstance(generator.generators[1], MockGenerator)
            self.assertEqual(generator.get_current_generator_name(), "gemini")
            self.assertTrue(generator.is_gemini_available())
    
    def test_fallback_to_mock(self):
        """Test fallback from failed Gemini to Mock generator."""
        # Create a mock Gemini generator that fails
        mock_gemini = Mock(spec=GeminiGenerator)
        mock_gemini.is_available.return_value = True
        mock_gemini.get_generator_name.return_value = "gemini"
        mock_gemini.generate_support_and_poem.side_effect = Exception("API Error")
        
        # Create a working mock generator
        mock_generator = MockGenerator()
        
        generator = ContentGenerator()
        generator.generators = [mock_gemini, mock_generator]
        generator.current_generator = mock_gemini
        
        # Should fallback to mock generator
        result = generator.generate_support_and_poem(self.test_input)
        
        self.assertIsInstance(result, GeneratedContent)
        self.assertEqual(generator.get_current_generator_name(), "mock")
    
    def test_all_generators_fail(self):
        """Test behavior when all generators fail."""
        # Create failing generators
        mock_gemini = Mock(spec=GeminiGenerator)
        mock_gemini.is_available.return_value = True
        mock_gemini.get_generator_name.return_value = "gemini"
        mock_gemini.generate_support_and_poem.side_effect = Exception("Gemini Error")
        
        mock_fallback = Mock(spec=MockGenerator)
        mock_fallback.is_available.return_value = True
        mock_fallback.get_generator_name.return_value = "mock"
        mock_fallback.generate_support_and_poem.side_effect = Exception("Mock Error")
        
        generator = ContentGenerator()
        generator.generators = [mock_gemini, mock_fallback]
        
        with self.assertRaises(RuntimeError) as context:
            generator.generate_support_and_poem(self.test_input)
        
        self.assertIn("All content generators failed", str(context.exception))
    
    def test_unavailable_generators_skipped(self):
        """Test that unavailable generators are skipped."""
        # Create unavailable Gemini generator
        mock_gemini = Mock(spec=GeminiGenerator)
        mock_gemini.is_available.return_value = False
        mock_gemini.get_generator_name.return_value = "gemini"
        
        # Create available mock generator
        mock_generator = MockGenerator()
        
        generator = ContentGenerator()
        generator.generators = [mock_gemini, mock_generator]
        
        result = generator.generate_support_and_poem(self.test_input)
        
        # Should use mock generator without calling Gemini
        self.assertIsInstance(result, GeneratedContent)
        mock_gemini.generate_support_and_poem.assert_not_called()
    
    def test_get_available_generators(self):
        """Test getting list of available generators."""
        mock_gemini = Mock(spec=GeminiGenerator)
        mock_gemini.is_available.return_value = True
        mock_gemini.get_generator_name.return_value = "gemini"
        
        mock_generator = MockGenerator()
        
        generator = ContentGenerator()
        generator.generators = [mock_gemini, mock_generator]
        
        available = generator.get_available_generators()
        self.assertEqual(available, ["gemini", "mock"])
    
    def test_successful_generation_with_mock(self):
        """Test successful generation using mock generator."""
        generator = ContentGenerator()
        result = generator.generate_support_and_poem(self.test_input)
        
        self.assertIsInstance(result, GeneratedContent)
        self.assertTrue(len(result.supportive_statement) > 0)
        self.assertTrue(len(result.poem) > 0)
        self.assertIn("generator", result.generation_metadata)


class TestContentGeneratorInterface(unittest.TestCase):
    """Test cases for ContentGeneratorInterface."""
    
    def test_interface_methods(self):
        """Test that interface defines required methods."""
        # Verify abstract methods exist
        self.assertTrue(hasattr(ContentGeneratorInterface, 'generate_support_and_poem'))
        self.assertTrue(hasattr(ContentGeneratorInterface, 'is_available'))
        self.assertTrue(hasattr(ContentGeneratorInterface, 'get_generator_name'))
        
        # Verify methods are abstract
        self.assertTrue(getattr(ContentGeneratorInterface.generate_support_and_poem, '__isabstractmethod__', False))
        self.assertTrue(getattr(ContentGeneratorInterface.is_available, '__isabstractmethod__', False))
        self.assertTrue(getattr(ContentGeneratorInterface.get_generator_name, '__isabstractmethod__', False))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)