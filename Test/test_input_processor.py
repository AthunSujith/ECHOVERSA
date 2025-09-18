"""
Unit tests for the input processing module.
Tests text, audio, and drawing input processing functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import base64
import io
from PIL import Image
import json

# Import the modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.input_processor import InputProcessor, AudioTranscriber, DrawingProcessor
from app.data_models import ProcessedInput, InputType


class TestInputProcessor(unittest.TestCase):
    """Test cases for the main InputProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = InputProcessor()
    
    def test_process_text_input_valid(self):
        """Test processing valid text input."""
        text = "This is a test message for emotional support."
        result = self.processor.process_text_input(text)
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.content, text)
        self.assertEqual(result.input_type, InputType.TEXT)
        self.assertIsNone(result.raw_data)
        self.assertIn("original_length", result.metadata)
        self.assertIn("cleaned_length", result.metadata)
        self.assertEqual(result.metadata["processing_method"], "text_cleanup")
    
    def test_process_text_input_with_whitespace(self):
        """Test processing text input with leading/trailing whitespace."""
        text = "  \n  Test message with whitespace  \t  "
        expected_cleaned = "Test message with whitespace"
        result = self.processor.process_text_input(text)
        
        self.assertEqual(result.content, expected_cleaned)
        self.assertEqual(result.metadata["original_length"], len(text))
        self.assertEqual(result.metadata["cleaned_length"], len(expected_cleaned))
    
    def test_process_text_input_with_metadata(self):
        """Test processing text input with additional metadata."""
        text = "Test message"
        metadata = {"source": "test", "priority": "high"}
        result = self.processor.process_text_input(text, metadata)
        
        self.assertEqual(result.content, text)
        self.assertIn("source", result.metadata)
        self.assertIn("priority", result.metadata)
        self.assertEqual(result.metadata["source"], "test")
        self.assertEqual(result.metadata["priority"], "high")
    
    def test_process_text_input_empty_string(self):
        """Test processing empty text input raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_text_input("")
        self.assertIn("non-empty string", str(context.exception))
    
    def test_process_text_input_none(self):
        """Test processing None text input raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_text_input(None)
        self.assertIn("non-empty string", str(context.exception))
    
    def test_process_text_input_whitespace_only(self):
        """Test processing whitespace-only text input raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_text_input("   \n\t   ")
        self.assertIn("cannot be empty after cleaning", str(context.exception))
    
    def test_process_text_input_too_long(self):
        """Test processing text input that exceeds maximum length."""
        # Create text longer than the 10000 character limit
        long_text = "a" * 10001
        with self.assertRaises(ValueError) as context:
            self.processor.process_text_input(long_text)
        self.assertIn("exceeds maximum length", str(context.exception))
    
    def test_process_audio_input_valid(self):
        """Test processing valid audio input."""
        # Create mock audio data with WAV header
        audio_data = b'RIFF' + b'\x00' * 100  # Mock WAV file
        filename = "test_audio.wav"
        
        with patch.object(self.processor.audio_transcriber, 'transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = "Transcribed audio content"
            
            result = self.processor.process_audio_input(audio_data, filename)
            
            self.assertIsInstance(result, ProcessedInput)
            self.assertEqual(result.content, "Transcribed audio content")
            self.assertEqual(result.input_type, InputType.AUDIO)
            self.assertEqual(result.raw_data, audio_data)
            self.assertIn("filename", result.metadata)
            self.assertIn("file_size", result.metadata)
            self.assertTrue(result.metadata["transcription_success"])
            self.assertEqual(result.metadata["filename"], filename)
            self.assertEqual(result.metadata["file_size"], len(audio_data))
            mock_transcribe.assert_called_once_with(audio_data)
    
    def test_process_audio_input_transcription_failure(self):
        """Test processing audio input when transcription fails."""
        audio_data = b'RIFF' + b'\x00' * 100  # Mock WAV file
        filename = "test_audio.wav"
        
        with patch.object(self.processor.audio_transcriber, 'transcribe_audio') as mock_transcribe:
            mock_transcribe.side_effect = RuntimeError("Transcription failed")
            
            result = self.processor.process_audio_input(audio_data, filename)
            
            self.assertEqual(result.content, f"Audio file: {filename}")
            self.assertFalse(result.metadata["transcription_success"])
            self.assertIn("transcription_error", result.metadata)
    
    def test_process_audio_input_invalid_format(self):
        """Test processing audio input with invalid format."""
        invalid_audio = b'INVALID_HEADER' + b'\x00' * 50
        
        with self.assertRaises(ValueError) as context:
            self.processor.process_audio_input(invalid_audio, "test.wav")
        self.assertIn("Invalid audio file format", str(context.exception))
    
    def test_process_audio_input_empty_data(self):
        """Test processing empty audio data raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_audio_input(b"", "test.wav")
        self.assertIn("non-empty bytes", str(context.exception))
    
    def test_process_audio_input_none_data(self):
        """Test processing None audio data raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_audio_input(None, "test.wav")
        self.assertIn("non-empty bytes", str(context.exception))
    
    def test_process_drawing_input_base64(self):
        """Test processing drawing input from base64 data."""
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        test_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        
        result = self.processor.process_drawing_input(base64_data)
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.DRAWING)
        self.assertIsNotNone(result.raw_data)
        self.assertIn("Hand-drawn sketch", result.content)
        self.assertTrue(result.metadata["has_png_data"])
        self.assertGreater(result.metadata["png_size"], 0)
    
    def test_process_drawing_input_data_url(self):
        """Test processing drawing input from data URL format."""
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        test_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_url = f"data:image/png;base64,{base64_data}"
        
        result = self.processor.process_drawing_input(data_url)
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.DRAWING)
        self.assertIsNotNone(result.raw_data)
    
    def test_process_drawing_input_canvas_dict(self):
        """Test processing drawing input from canvas dictionary."""
        canvas_data = {
            'width': 300,
            'height': 200,
            'strokes': [
                {'x': 10, 'y': 10, 'color': 'black'},
                {'x': 20, 'y': 20, 'color': 'red'}
            ],
            'background_color': 'white'
        }
        
        result = self.processor.process_drawing_input(canvas_data)
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.DRAWING)
        self.assertIsNotNone(result.raw_data)
        self.assertIn("strokes", result.content)
        self.assertTrue(result.metadata["has_png_data"])
    
    def test_process_drawing_input_empty_canvas(self):
        """Test processing empty canvas data."""
        canvas_data = {
            'width': 400,
            'height': 400,
            'strokes': [],
            'background_color': 'white'
        }
        
        result = self.processor.process_drawing_input(canvas_data)
        
        self.assertIn("Empty canvas", result.content)
    
    def test_process_drawing_input_invalid_data(self):
        """Test processing invalid drawing data raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_drawing_input(None)
        self.assertIn("cannot be empty", str(context.exception))
    
    def test_process_drawing_input_invalid_base64(self):
        """Test processing invalid base64 data raises ValueError."""
        invalid_base64 = "invalid_base64_data"
        
        with self.assertRaises(ValueError) as context:
            self.processor.process_drawing_input(invalid_base64)
        self.assertIn("Failed to process", str(context.exception))
    
    def test_is_valid_audio_format_wav(self):
        """Test audio format validation for WAV files."""
        wav_data = b'RIFF' + b'\x00' * 100
        self.assertTrue(self.processor._is_valid_audio_format(wav_data))
    
    def test_is_valid_audio_format_mp3(self):
        """Test audio format validation for MP3 files."""
        mp3_data = b'ID3' + b'\x00' * 100
        self.assertTrue(self.processor._is_valid_audio_format(mp3_data))
    
    def test_is_valid_audio_format_mp3_frame_sync(self):
        """Test audio format validation for MP3 frame sync."""
        mp3_frame = b'\xFF\xFB' + b'\x00' * 100
        self.assertTrue(self.processor._is_valid_audio_format(mp3_frame))
    
    def test_is_valid_audio_format_invalid(self):
        """Test audio format validation for invalid data."""
        invalid_data = b'INVALID' + b'\x00' * 100
        self.assertFalse(self.processor._is_valid_audio_format(invalid_data))
    
    def test_is_valid_audio_format_too_short(self):
        """Test audio format validation for data too short."""
        short_data = b'RI'
        self.assertFalse(self.processor._is_valid_audio_format(short_data))


class TestAudioTranscriber(unittest.TestCase):
    """Test cases for the AudioTranscriber class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transcriber = AudioTranscriber()
    
    def test_check_whisper_availability_not_available(self):
        """Test Whisper availability check when not available."""
        with patch('builtins.__import__', side_effect=ImportError):
            transcriber = AudioTranscriber()
            self.assertFalse(transcriber.whisper_available)
    
    def test_transcribe_audio_whisper_not_available(self):
        """Test transcription when Whisper is not available."""
        self.transcriber.whisper_available = False
        
        with self.assertRaises(RuntimeError) as context:
            self.transcriber.transcribe_audio(b'test_audio_data')
        self.assertIn("not available", str(context.exception))
    
    def test_transcribe_audio_mock_transcription(self):
        """Test mock transcription functionality."""
        # Test different file sizes
        small_audio = b'RIFF' + b'\x00' * 1000  # ~1KB
        medium_audio = b'RIFF' + b'\x00' * 100000  # ~100KB
        large_audio = b'RIFF' + b'\x00' * 500000  # ~500KB
        
        small_result = self.transcriber._mock_transcription(small_audio)
        medium_result = self.transcriber._mock_transcription(medium_audio)
        large_result = self.transcriber._mock_transcription(large_audio)
        
        self.assertIn("Short audio", small_result)
        self.assertIn("Medium length", medium_result)
        self.assertIn("Long audio", large_result)
    
    def test_transcribe_audio_with_whisper_available(self):
        """Test transcription when Whisper is available."""
        self.transcriber.whisper_available = True
        audio_data = b'RIFF' + b'\x00' * 1000
        
        # This will use mock transcription since we don't have actual Whisper
        result = self.transcriber.transcribe_audio(audio_data)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestDrawingProcessor(unittest.TestCase):
    """Test cases for the DrawingProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DrawingProcessor()
    
    def test_process_canvas_data_base64_string(self):
        """Test processing base64 string canvas data."""
        # Create test image
        test_image = Image.new('RGB', (50, 50), color='green')
        buffer = io.BytesIO()
        test_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        
        png_data, description = self.processor.process_canvas_data(base64_data)
        
        self.assertIsNotNone(png_data)
        self.assertIsInstance(description, str)
        self.assertIn("sketch", description.lower())
    
    def test_process_canvas_data_dict(self):
        """Test processing dictionary canvas data."""
        canvas_data = {
            'width': 200,
            'height': 150,
            'strokes': [{'x': 10, 'y': 10}],
            'background_color': 'white'
        }
        
        png_data, description = self.processor.process_canvas_data(canvas_data)
        
        self.assertIsNotNone(png_data)
        self.assertIsInstance(description, str)
        self.assertIn("200x150", description)
    
    def test_process_canvas_data_invalid_type(self):
        """Test processing invalid canvas data type."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_canvas_data(123)
        self.assertIn("must be string", str(context.exception))
    
    def test_create_image_from_strokes(self):
        """Test creating image from stroke data."""
        strokes = [
            {'x': 10, 'y': 10, 'color': 'black'},
            {'x': 20, 'y': 20, 'color': 'red'}
        ]
        
        image = self.processor._create_image_from_strokes(100, 100, strokes, 'white')
        
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (100, 100))
    
    def test_generate_image_description(self):
        """Test generating description for PIL image."""
        test_image = Image.new('RGB', (100, 100), color=(255, 0, 0))  # Red image
        
        description = self.processor._generate_image_description(test_image)
        
        self.assertIsInstance(description, str)
        self.assertIn("100x100", description)
        self.assertIn("reddish", description)
    
    def test_generate_canvas_description_empty(self):
        """Test generating description for empty canvas."""
        canvas_data = {'width': 300, 'height': 200, 'strokes': []}
        
        description = self.processor._generate_canvas_description(canvas_data)
        
        self.assertIn("Empty canvas", description)
        self.assertIn("300x200", description)
    
    def test_generate_canvas_description_with_strokes(self):
        """Test generating description for canvas with strokes."""
        canvas_data = {
            'width': 400,
            'height': 300,
            'strokes': [{'x': i, 'y': i} for i in range(10)]  # 10 strokes
        }
        
        description = self.processor._generate_canvas_description(canvas_data)
        
        self.assertIn("10 strokes", description)
        self.assertIn("400x300", description)


if __name__ == '__main__':
    unittest.main()