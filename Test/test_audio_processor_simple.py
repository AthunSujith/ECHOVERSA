"""
Simplified unit tests for audio processing module.
Tests core functionality without complex mocking of optional dependencies.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from audio_processor import (
    TTSProcessor, AudioRemixer, AudioManager, Voice,
    validate_audio_file, get_default_background_music_path
)
from data_models import AudioFile


class TestTTSProcessorBasic(unittest.TestCase):
    """Basic test cases for TTSProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tts_processor = TTSProcessor()
    
    def test_init_without_api_key(self):
        """Test TTSProcessor initialization without API key."""
        processor = TTSProcessor()
        self.assertIsNone(processor.elevenlabs_api_key)
        self.assertIsNotNone(processor.logger)
    
    def test_init_with_api_key(self):
        """Test TTSProcessor initialization with API key."""
        api_key = "test_api_key_123"
        processor = TTSProcessor(elevenlabs_api_key=api_key)
        self.assertEqual(processor.elevenlabs_api_key, api_key)
    
    def test_text_to_speech_empty_text(self):
        """Test TTS with empty text."""
        result = self.tts_processor.text_to_speech("")
        self.assertIsNone(result)
        
        result = self.tts_processor.text_to_speech("   ")
        self.assertIsNone(result)
        
        result = self.tts_processor.text_to_speech(None)
        self.assertIsNone(result)
    
    def test_get_available_voices_returns_list(self):
        """Test that get_available_voices returns a list."""
        voices = self.tts_processor.get_available_voices()
        self.assertIsInstance(voices, list)
        
        # Should have at least ElevenLabs default voices if API key is provided
        processor_with_key = TTSProcessor(elevenlabs_api_key="test_key")
        voices_with_key = processor_with_key.get_available_voices()
        self.assertIsInstance(voices_with_key, list)
        self.assertGreater(len(voices_with_key), 0)


class TestAudioRemixerBasic(unittest.TestCase):
    """Basic test cases for AudioRemixer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.remixer = AudioRemixer()
        
        # Create temporary test files
        self.temp_speech_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        self.temp_speech_file.write(b"fake_speech_data")
        self.temp_speech_file.close()
        
        self.speech_audio = AudioFile(
            file_path=self.temp_speech_file.name,
            duration=5.0,
            format="wav"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_speech_file.name)
        except:
            pass
    
    def test_create_remix_no_background_music(self):
        """Test remix creation without background music."""
        result = self.remixer.create_remix(self.speech_audio)
        self.assertEqual(result, self.speech_audio)
    
    def test_create_remix_invalid_speech_file(self):
        """Test remix creation with invalid speech file."""
        invalid_audio = AudioFile(file_path="/nonexistent/file.wav")
        result = self.remixer.create_remix(invalid_audio)
        self.assertIsNone(result)
    
    def test_apply_audio_effects_no_pydub(self):
        """Test applying audio effects when pydub is not available."""
        # This should return the original audio when pydub is not available
        effects = {'volume': 5, 'fade_in': 1.0}
        result = self.remixer.apply_audio_effects(self.speech_audio, effects)
        
        # Should return the original audio file when pydub is not available
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)


class TestAudioManagerBasic(unittest.TestCase):
    """Basic test cases for AudioManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = AudioManager()
    
    def test_init(self):
        """Test AudioManager initialization."""
        manager = AudioManager()
        self.assertIsNotNone(manager.tts_processor)
        self.assertIsNotNone(manager.audio_remixer)
        self.assertIsNotNone(manager.logger)
    
    def test_init_with_api_key(self):
        """Test AudioManager initialization with API key."""
        manager = AudioManager(elevenlabs_api_key="test_key")
        self.assertEqual(manager.tts_processor.elevenlabs_api_key, "test_key")
    
    def test_process_text_to_audio_tts_failure(self):
        """Test text-to-audio processing when TTS fails."""
        # Mock the TTS processor to return None
        self.manager.tts_processor.text_to_speech = Mock(return_value=None)
        
        result = self.manager.process_text_to_audio("test text")
        
        self.assertIn('speech', result)
        self.assertIn('remix', result)
        self.assertIsNone(result['speech'])
        self.assertIsNone(result['remix'])
    
    def test_get_audio_info_nonexistent_file(self):
        """Test getting audio info for non-existent file."""
        audio_file = AudioFile(
            file_path="/nonexistent/file.wav",
            duration=5.0,
            format="wav"
        )
        
        info = self.manager.get_audio_info(audio_file)
        
        self.assertEqual(info['file_path'], "/nonexistent/file.wav")
        self.assertEqual(info['duration'], 5.0)
        self.assertEqual(info['format'], "wav")
        self.assertFalse(info['exists'])
        self.assertIsNone(info['file_size'])
    
    def test_is_audio_processing_available(self):
        """Test checking audio processing availability."""
        availability = self.manager.is_audio_processing_available()
        
        self.assertIsInstance(availability, dict)
        self.assertIn('pyttsx3_tts', availability)
        self.assertIn('elevenlabs_tts', availability)
        self.assertIn('pydub_mixing', availability)
        self.assertIn('numpy_fallback', availability)
        self.assertIn('any_tts', availability)
        
        # All should be boolean values
        for key, value in availability.items():
            self.assertIsInstance(value, bool)
    
    def test_cleanup_temp_files_empty_list(self):
        """Test cleanup with empty list."""
        # Should not raise any exceptions
        self.manager.cleanup_temp_files([])
    
    def test_cleanup_temp_files_none_values(self):
        """Test cleanup with None values."""
        # Should not raise any exceptions
        self.manager.cleanup_temp_files([None, None])


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_validate_audio_file_nonexistent(self):
        """Test validating non-existent audio file."""
        result = validate_audio_file("/nonexistent/file.wav")
        self.assertFalse(result)
    
    def test_validate_audio_file_invalid_extension(self):
        """Test validating file with invalid extension."""
        # Create a temporary file with invalid extension
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            result = validate_audio_file(temp_file_path)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file_path)
    
    def test_validate_audio_file_valid_extension(self):
        """Test validating file with valid extension."""
        # Create a temporary file with valid extension
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
        
        try:
            result = validate_audio_file(temp_file_path)
            # Should return True for valid extension even if not real audio
            # (since pydub is not available to validate actual audio content)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file_path)
    
    def test_get_default_background_music_path_no_files(self):
        """Test getting default background music path when no files exist."""
        result = get_default_background_music_path()
        # Should return None when no default music files exist
        self.assertIsNone(result)


class TestVoiceDataClass(unittest.TestCase):
    """Test cases for Voice data class."""
    
    def test_voice_creation(self):
        """Test Voice object creation."""
        voice = Voice(
            id="voice123",
            name="Test Voice",
            language="en",
            gender="female",
            provider="elevenlabs"
        )
        
        self.assertEqual(voice.id, "voice123")
        self.assertEqual(voice.name, "Test Voice")
        self.assertEqual(voice.language, "en")
        self.assertEqual(voice.gender, "female")
        self.assertEqual(voice.provider, "elevenlabs")
    
    def test_voice_defaults(self):
        """Test Voice object with default values."""
        voice = Voice(id="voice123", name="Test Voice")
        
        self.assertEqual(voice.id, "voice123")
        self.assertEqual(voice.name, "Test Voice")
        self.assertEqual(voice.language, "en")
        self.assertEqual(voice.gender, "neutral")
        self.assertEqual(voice.provider, "pyttsx3")


class TestAudioFileIntegration(unittest.TestCase):
    """Integration tests with AudioFile data model."""
    
    def test_audio_manager_with_real_audio_file(self):
        """Test AudioManager with real AudioFile objects."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
        
        try:
            audio_file = AudioFile(
                file_path=temp_file_path,
                duration=3.5,
                format="wav",
                metadata={"test": "data"}
            )
            
            manager = AudioManager()
            info = manager.get_audio_info(audio_file)
            
            self.assertTrue(info['exists'])
            self.assertEqual(info['file_path'], temp_file_path)
            self.assertEqual(info['duration'], 3.5)
            self.assertEqual(info['format'], "wav")
            self.assertGreater(info['file_size'], 0)
            
        finally:
            os.unlink(temp_file_path)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main(verbosity=2)