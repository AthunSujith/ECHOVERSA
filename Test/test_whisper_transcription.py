"""
Unit tests for Whisper transcription functionality in EchoVerse companion application.
Tests the AudioTranscriber class and integration with ProcessedInput data model.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.input_processor import AudioTranscriber, InputProcessor
from app.data_models import ProcessedInput, InputType


class TestAudioTranscriber(unittest.TestCase):
    """Test cases for AudioTranscriber class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transcriber = AudioTranscriber()
        self.sample_audio_data = b'RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00'  # Mock WAV header
    
    def test_init_without_whisper(self):
        """Test AudioTranscriber initialization when Whisper is not available."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=False):
            transcriber = AudioTranscriber()
            self.assertFalse(transcriber.whisper_available)
            self.assertIsNone(transcriber.whisper_model)
    
    def test_init_with_whisper(self):
        """Test AudioTranscriber initialization when Whisper is available."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=True):
            with patch('app.input_processor.AudioTranscriber._load_whisper_model') as mock_load:
                transcriber = AudioTranscriber()
                self.assertTrue(transcriber.whisper_available)
                mock_load.assert_called_once()
    
    def test_check_whisper_availability_available(self):
        """Test Whisper availability check when Whisper is installed."""
        # Create a fresh transcriber and test the method directly
        transcriber = AudioTranscriber()
        
        # Mock the import to succeed
        with patch('builtins.__import__', return_value=Mock()):
            result = transcriber._check_whisper_availability()
            self.assertTrue(result)
    
    def test_check_whisper_availability_not_available(self):
        """Test Whisper availability check when Whisper is not installed."""
        with patch('builtins.__import__', side_effect=ImportError()):
            result = AudioTranscriber()._check_whisper_availability()
            self.assertFalse(result)
    
    def test_transcribe_audio_whisper_not_available(self):
        """Test transcription when Whisper is not available."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=False):
            transcriber = AudioTranscriber()
            
            with self.assertRaises(RuntimeError) as context:
                transcriber.transcribe_audio(self.sample_audio_data)
            
            self.assertIn("Whisper transcription not available", str(context.exception))
    
    def test_transcribe_audio_success(self):
        """Test successful audio transcription with Whisper."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=True):
            with patch('app.input_processor.AudioTranscriber._load_whisper_model'):
                with patch('app.input_processor.AudioTranscriber._whisper_transcribe', return_value="Hello, this is a test transcription.") as mock_whisper:
                    transcriber = AudioTranscriber()
                    result = transcriber.transcribe_audio(self.sample_audio_data)
                    
                    self.assertEqual(result, "Hello, this is a test transcription.")
                    mock_whisper.assert_called_once_with(self.sample_audio_data)
    
    def test_transcribe_audio_empty_result(self):
        """Test transcription with empty result from Whisper."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=True):
            with patch('app.input_processor.AudioTranscriber._load_whisper_model'):
                with patch('app.input_processor.AudioTranscriber._whisper_transcribe', side_effect=RuntimeError("Empty transcription result")):
                    transcriber = AudioTranscriber()
                    
                    # Should fallback to mock transcription
                    result = transcriber.transcribe_audio(self.sample_audio_data)
                    self.assertIn("audio message", result.lower())
    
    def test_transcribe_audio_whisper_failure_with_fallback(self):
        """Test transcription failure with fallback to mock transcription."""
        with patch('app.input_processor.AudioTranscriber._check_whisper_availability', return_value=True):
            with patch('app.input_processor.AudioTranscriber._load_whisper_model'):
                with patch('app.input_processor.AudioTranscriber._whisper_transcribe', side_effect=RuntimeError("Whisper processing error")):
                    transcriber = AudioTranscriber()
                    result = transcriber.transcribe_audio(self.sample_audio_data)
                    
                    # Should fallback to mock transcription
                    self.assertIn("audio message", result.lower())
    
    def test_mock_transcription_short_audio(self):
        """Test mock transcription for short audio files."""
        transcriber = AudioTranscriber()
        short_audio = b'x' * 1000  # 1KB
        result = transcriber._mock_transcription(short_audio)
        self.assertEqual(result, "Short audio message recorded")
    
    def test_mock_transcription_medium_audio(self):
        """Test mock transcription for medium audio files."""
        transcriber = AudioTranscriber()
        medium_audio = b'x' * 100000  # 100KB
        result = transcriber._mock_transcription(medium_audio)
        self.assertEqual(result, "Medium length audio message with personal thoughts and feelings")
    
    def test_mock_transcription_long_audio(self):
        """Test mock transcription for long audio files."""
        transcriber = AudioTranscriber()
        long_audio = b'x' * 500000  # 500KB
        result = transcriber._mock_transcription(long_audio)
        self.assertEqual(result, "Long audio message containing detailed personal reflection and emotional expression")


class TestInputProcessorWithWhisper(unittest.TestCase):
    """Test cases for InputProcessor integration with Whisper transcription."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = InputProcessor()
        self.sample_audio_data = b'RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00'  # Mock WAV header
    
    @patch('app.input_processor.AudioTranscriber.transcribe_audio')
    def test_process_audio_input_with_successful_transcription(self, mock_transcribe):
        """Test audio input processing with successful Whisper transcription."""
        mock_transcribe.return_value = "This is a transcribed message from the audio file."
        
        result = self.processor.process_audio_input(self.sample_audio_data, "test.wav")
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.AUDIO)
        self.assertEqual(result.content, "This is a transcribed message from the audio file.")
        self.assertEqual(result.transcription, "This is a transcribed message from the audio file.")
        self.assertEqual(result.raw_data, self.sample_audio_data)
        
        # Check metadata
        self.assertTrue(result.metadata["transcription_attempted"])
        self.assertTrue(result.metadata["transcription_success"])
        self.assertIsNone(result.metadata["transcription_error"])
        self.assertEqual(result.metadata["filename"], "test.wav")
    
    @patch('app.input_processor.AudioTranscriber.transcribe_audio')
    def test_process_audio_input_with_failed_transcription(self, mock_transcribe):
        """Test audio input processing with failed Whisper transcription."""
        mock_transcribe.side_effect = RuntimeError("Transcription failed")
        
        result = self.processor.process_audio_input(self.sample_audio_data, "test.wav")
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.AUDIO)
        self.assertEqual(result.content, "Audio file: test.wav")
        self.assertIsNone(result.transcription)
        self.assertEqual(result.raw_data, self.sample_audio_data)
        
        # Check metadata
        self.assertTrue(result.metadata["transcription_attempted"])
        self.assertFalse(result.metadata["transcription_success"])
        self.assertEqual(result.metadata["transcription_error"], "Transcription failed")
    
    @patch('app.input_processor.AudioTranscriber.transcribe_audio')
    def test_process_audio_input_with_long_transcription(self, mock_transcribe):
        """Test audio input processing with transcription that exceeds length limits."""
        # Create a very long transcription that would exceed validation limits
        long_transcription = "This is a very long transcription. " * 2000  # Very long text
        mock_transcribe.return_value = long_transcription
        
        result = self.processor.process_audio_input(self.sample_audio_data, "test.wav")
        
        self.assertIsInstance(result, ProcessedInput)
        self.assertEqual(result.input_type, InputType.AUDIO)
        # Content should be truncated message, but full transcription preserved
        self.assertIn("transcription available but truncated", result.content)
        self.assertEqual(result.transcription, long_transcription)
    
    def test_process_audio_input_with_invalid_data(self):
        """Test audio input processing with invalid audio data."""
        with self.assertRaises(ValueError) as context:
            self.processor.process_audio_input(b"", "test.wav")
        
        self.assertIn("Audio data must be non-empty bytes", str(context.exception))
    
    def test_process_audio_input_with_invalid_format(self):
        """Test audio input processing with invalid audio format."""
        invalid_audio = b"This is not audio data"
        
        with self.assertRaises(ValueError) as context:
            self.processor.process_audio_input(invalid_audio, "test.wav")
        
        self.assertIn("Invalid audio file format", str(context.exception))
    
    @patch('app.input_processor.AudioTranscriber.transcribe_audio')
    def test_process_audio_input_metadata_includes_whisper_status(self, mock_transcribe):
        """Test that processed audio input includes Whisper availability in metadata."""
        mock_transcribe.return_value = "Test transcription"
        
        result = self.processor.process_audio_input(self.sample_audio_data, "test.wav")
        
        # Check that Whisper availability is included in metadata
        self.assertIn("whisper_available", result.metadata)
        self.assertIsInstance(result.metadata["whisper_available"], bool)


class TestProcessedInputWithTranscription(unittest.TestCase):
    """Test cases for ProcessedInput data model with transcription field."""
    
    def test_processed_input_with_transcription(self):
        """Test ProcessedInput creation with transcription field."""
        processed_input = ProcessedInput(
            content="Audio file content",
            input_type=InputType.AUDIO,
            transcription="This is the transcribed text"
        )
        
        self.assertEqual(processed_input.content, "Audio file content")
        self.assertEqual(processed_input.input_type, InputType.AUDIO)
        self.assertEqual(processed_input.transcription, "This is the transcribed text")
    
    def test_processed_input_without_transcription(self):
        """Test ProcessedInput creation without transcription field."""
        processed_input = ProcessedInput(
            content="Text content",
            input_type=InputType.TEXT
        )
        
        self.assertEqual(processed_input.content, "Text content")
        self.assertEqual(processed_input.input_type, InputType.TEXT)
        self.assertIsNone(processed_input.transcription)
    
    def test_processed_input_invalid_transcription_type(self):
        """Test ProcessedInput validation with invalid transcription type."""
        with self.assertRaises(ValueError) as context:
            ProcessedInput(
                content="Audio content",
                input_type=InputType.AUDIO,
                transcription=123  # Invalid type
            )
        
        self.assertIn("Transcription must be a string if provided", str(context.exception))


if __name__ == '__main__':
    unittest.main()