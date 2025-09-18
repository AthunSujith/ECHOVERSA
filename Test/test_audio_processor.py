"""
Unit tests for audio processing module.
Tests TTS processing, audio remixing, and fallback systems.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os
import sys
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from audio_processor import (
    TTSProcessor, AudioRemixer, AudioManager, Voice,
    get_default_background_music_path, validate_audio_file, create_silence_audio
)
from data_models import AudioFile


class TestTTSProcessor(unittest.TestCase):
    """Test cases for TTSProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tts_processor = TTSProcessor()
        self.test_text = "Hello, this is a test message for TTS conversion."
    
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
    
    @patch('app.audio_processor.pyttsx3')
    def test_configure_pyttsx3(self, mock_pyttsx3):
        """Test pyttsx3 configuration."""
        mock_engine = Mock()
        mock_voices = [Mock(name='Microsoft Zira', id='voice1')]
        mock_engine.getProperty.return_value = mock_voices
        mock_pyttsx3.init.return_value = mock_engine
        
        processor = TTSProcessor()
        processor.pyttsx3_engine = mock_engine
        processor._configure_pyttsx3()
        
        # Verify engine properties were set
        mock_engine.setProperty.assert_any_call('rate', 150)
        mock_engine.setProperty.assert_any_call('volume', 0.8)
    
    def test_text_to_speech_empty_text(self):
        """Test TTS with empty text."""
        result = self.tts_processor.text_to_speech("")
        self.assertIsNone(result)
        
        result = self.tts_processor.text_to_speech("   ")
        self.assertIsNone(result)
    
    @patch('audio_processor.requests')
    @patch('audio_processor.tempfile')
    def test_elevenlabs_tts_success(self, mock_tempfile, mock_requests):
        """Test successful ElevenLabs TTS conversion."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        mock_requests.post.return_value = mock_response
        
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_audio.mp3"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        processor = TTSProcessor(elevenlabs_api_key="test_key")
        
        with patch('audio_processor.REQUESTS_AVAILABLE', True):
            result = processor._elevenlabs_tts(self.test_text, {})
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.metadata["provider"], "elevenlabs")
    
    @patch('audio_processor.requests')
    def test_elevenlabs_tts_api_error(self, mock_requests):
        """Test ElevenLabs TTS API error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response
        
        processor = TTSProcessor(elevenlabs_api_key="test_key")
        
        with patch('audio_processor.REQUESTS_AVAILABLE', True):
            result = processor._elevenlabs_tts(self.test_text, {})
        
        self.assertIsNone(result)
    
    @patch('audio_processor.tempfile')
    def test_pyttsx3_tts_success(self, mock_tempfile):
        """Test successful pyttsx3 TTS conversion."""
        mock_engine = Mock()
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_audio.wav"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        processor = TTSProcessor()
        processor.pyttsx3_engine = mock_engine
        
        result = processor._pyttsx3_tts(self.test_text, {'rate': 120})
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.metadata["provider"], "pyttsx3")
        mock_engine.setProperty.assert_any_call('rate', 120)
        mock_engine.save_to_file.assert_called_once()
        mock_engine.runAndWait.assert_called_once()
    
    @patch('audio_processor.pyttsx3')
    def test_get_available_voices(self, mock_pyttsx3):
        """Test getting available voices."""
        mock_engine = Mock()
        mock_voice = Mock()
        mock_voice.id = "voice1"
        mock_voice.name = "Microsoft Zira - English (United States)"
        mock_voice.languages = ["en"]
        mock_engine.getProperty.return_value = [mock_voice]
        
        processor = TTSProcessor(elevenlabs_api_key="test_key")
        processor.pyttsx3_engine = mock_engine
        
        voices = processor.get_available_voices()
        
        self.assertIsInstance(voices, list)
        self.assertGreater(len(voices), 0)
        
        # Check pyttsx3 voice
        pyttsx3_voices = [v for v in voices if v.provider == 'pyttsx3']
        self.assertGreater(len(pyttsx3_voices), 0)
        
        # Check ElevenLabs voices
        elevenlabs_voices = [v for v in voices if v.provider == 'elevenlabs']
        self.assertGreater(len(elevenlabs_voices), 0)


class TestAudioRemixer(unittest.TestCase):
    """Test cases for AudioRemixer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.remixer = AudioRemixer()
        
        # Create temporary test files
        self.temp_speech_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        self.temp_speech_file.write(b"fake_speech_data")
        self.temp_speech_file.close()
        
        self.temp_music_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        self.temp_music_file.write(b"fake_music_data")
        self.temp_music_file.close()
        
        self.speech_audio = AudioFile(
            file_path=self.temp_speech_file.name,
            duration=5.0,
            format="wav"
        )
        
        self.music_audio = AudioFile(
            file_path=self.temp_music_file.name,
            duration=10.0,
            format="wav"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_speech_file.name)
            os.unlink(self.temp_music_file.name)
        except:
            pass
    
    def test_create_remix_no_background_music(self):
        """Test remix creation without background music."""
        result = self.remixer.create_remix(self.speech_audio)
        self.assertEqual(result, self.speech_audio)
    
    def test_create_remix_invalid_speech_file(self):
        """Test remix creation with invalid speech file."""
        invalid_audio = AudioFile(file_path="/nonexistent/file.wav")
        result = self.remixer.create_remix(invalid_audio, self.music_audio)
        self.assertIsNone(result)
    
    @patch('audio_processor.PYDUB_AVAILABLE', True)
    @patch('audio_processor.AudioSegment')
    @patch('audio_processor.tempfile')
    def test_pydub_remix_success(self, mock_tempfile, mock_audio_segment):
        """Test successful remix creation with pydub."""
        # Setup mocks
        mock_speech = Mock()
        mock_speech.__len__ = Mock(return_value=5000)  # 5 seconds
        mock_music = Mock()
        mock_music.__len__ = Mock(return_value=3000)  # 3 seconds
        mock_music.__mul__ = Mock(return_value=mock_music)
        mock_music.__getitem__ = Mock(return_value=mock_music)
        
        mock_mixed = Mock()
        mock_mixed.__len__ = Mock(return_value=5000)
        mock_speech.overlay.return_value = mock_mixed
        
        mock_audio_segment.from_file.side_effect = [mock_speech, mock_music]
        
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/remix.wav"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        result = self.remixer._pydub_remix(self.speech_audio, self.music_audio, 0.7)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.metadata["provider"], "pydub_remix")
        self.assertEqual(result.metadata["volume_ratio"], 0.7)
    
    @patch('audio_processor.NUMPY_AVAILABLE', True)
    @patch('audio_processor.shutil')
    @patch('audio_processor.tempfile')
    def test_numpy_remix_fallback(self, mock_tempfile, mock_shutil):
        """Test numpy fallback remix creation."""
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/remix.wav"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        result = self.remixer._numpy_remix(self.speech_audio, self.music_audio, 0.7)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.metadata["provider"], "numpy_fallback")
        mock_shutil.copy2.assert_called_once()
    
    @patch('audio_processor.PYDUB_AVAILABLE', True)
    @patch('audio_processor.AudioSegment')
    @patch('audio_processor.tempfile')
    def test_apply_audio_effects(self, mock_tempfile, mock_audio_segment):
        """Test applying audio effects."""
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio.__add__ = Mock(return_value=mock_audio)  # Volume adjustment
        mock_audio.fade_in.return_value = mock_audio
        mock_audio.fade_out.return_value = mock_audio
        mock_audio_segment.from_file.return_value = mock_audio
        
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/effects.wav"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        effects = {
            'volume': 5,  # +5 dB
            'fade_in': 1.0,  # 1 second fade in
            'fade_out': 2.0   # 2 second fade out
        }
        
        result = self.remixer.apply_audio_effects(self.speech_audio, effects)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.metadata["effects_applied"], effects)
        mock_audio.fade_in.assert_called_with(1000)  # 1 second in ms
        mock_audio.fade_out.assert_called_with(2000)  # 2 seconds in ms


class TestAudioManager(unittest.TestCase):
    """Test cases for AudioManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = AudioManager()
        self.test_text = "This is a test message for audio processing."
    
    @patch('audio_processor.TTSProcessor')
    @patch('audio_processor.AudioRemixer')
    def test_init(self, mock_remixer, mock_tts):
        """Test AudioManager initialization."""
        manager = AudioManager(elevenlabs_api_key="test_key")
        
        mock_tts.assert_called_once_with("test_key")
        mock_remixer.assert_called_once()
    
    def test_process_text_to_audio_speech_only(self):
        """Test text-to-audio processing without remix."""
        mock_audio = AudioFile(file_path="/tmp/speech.wav", format="wav")
        self.manager.tts_processor.text_to_speech = Mock(return_value=mock_audio)
        
        result = self.manager.process_text_to_audio(self.test_text)
        
        self.assertIn('speech', result)
        self.assertIn('remix', result)
        self.assertEqual(result['speech'], mock_audio)
        self.assertIsNone(result['remix'])
    
    def test_process_text_to_audio_with_remix(self):
        """Test text-to-audio processing with remix."""
        mock_speech = AudioFile(file_path="/tmp/speech.wav", format="wav")
        mock_remix = AudioFile(file_path="/tmp/remix.wav", format="wav")
        
        self.manager.tts_processor.text_to_speech = Mock(return_value=mock_speech)
        self.manager.audio_remixer.create_remix = Mock(return_value=mock_remix)
        
        result = self.manager.process_text_to_audio(
            self.test_text,
            background_music_path="/tmp/music.wav",
            create_remix=True
        )
        
        self.assertEqual(result['speech'], mock_speech)
        self.assertEqual(result['remix'], mock_remix)
    
    def test_process_text_to_audio_tts_failure(self):
        """Test text-to-audio processing when TTS fails."""
        self.manager.tts_processor.text_to_speech = Mock(return_value=None)
        
        result = self.manager.process_text_to_audio(self.test_text)
        
        self.assertIsNone(result['speech'])
        self.assertIsNone(result['remix'])
    
    @patch('audio_processor.os.path.exists')
    @patch('audio_processor.os.path.getsize')
    def test_get_audio_info(self, mock_getsize, mock_exists):
        """Test getting audio file information."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        audio_file = AudioFile(
            file_path="/tmp/test.wav",
            duration=5.0,
            format="wav",
            metadata={"provider": "test"}
        )
        
        info = self.manager.get_audio_info(audio_file)
        
        self.assertEqual(info['file_path'], "/tmp/test.wav")
        self.assertEqual(info['duration'], 5.0)
        self.assertEqual(info['format'], "wav")
        self.assertTrue(info['exists'])
        self.assertEqual(info['file_size'], 1024)
    
    @patch('audio_processor.os.path.exists')
    @patch('audio_processor.os.unlink')
    def test_cleanup_temp_files(self, mock_unlink, mock_exists):
        """Test cleanup of temporary files."""
        mock_exists.return_value = True
        
        temp_files = [
            AudioFile(file_path="/tmp/temp1.wav"),
            AudioFile(file_path="/tmp/temp2.wav"),
            AudioFile(file_path="/permanent/file.wav")  # Should not be deleted
        ]
        
        self.manager.cleanup_temp_files(temp_files)
        
        # Only temp files should be deleted
        self.assertEqual(mock_unlink.call_count, 2)
    
    def test_is_audio_processing_available(self):
        """Test checking audio processing availability."""
        availability = self.manager.is_audio_processing_available()
        
        self.assertIsInstance(availability, dict)
        self.assertIn('pyttsx3_tts', availability)
        self.assertIn('elevenlabs_tts', availability)
        self.assertIn('pydub_mixing', availability)
        self.assertIn('numpy_fallback', availability)
        self.assertIn('any_tts', availability)


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""
    
    @patch('audio_processor.os.path.exists')
    def test_get_default_background_music_path(self, mock_exists):
        """Test getting default background music path."""
        # Test when no files exist
        mock_exists.return_value = False
        result = get_default_background_music_path()
        self.assertIsNone(result)
        
        # Test when first file exists
        mock_exists.side_effect = lambda path: path == 'assets/background_music.mp3'
        result = get_default_background_music_path()
        self.assertEqual(result, 'assets/background_music.mp3')
    
    @patch('audio_processor.os.path.exists')
    def test_validate_audio_file_nonexistent(self, mock_exists):
        """Test validating non-existent audio file."""
        mock_exists.return_value = False
        result = validate_audio_file("/nonexistent/file.wav")
        self.assertFalse(result)
    
    @patch('audio_processor.os.path.exists')
    def test_validate_audio_file_invalid_extension(self, mock_exists):
        """Test validating file with invalid extension."""
        mock_exists.return_value = True
        result = validate_audio_file("/path/to/file.txt")
        self.assertFalse(result)
    
    @patch('audio_processor.os.path.exists')
    def test_validate_audio_file_valid(self, mock_exists):
        """Test validating valid audio file."""
        mock_exists.return_value = True
        result = validate_audio_file("/path/to/file.wav")
        self.assertTrue(result)
    
    @patch('audio_processor.PYDUB_AVAILABLE', True)
    @patch('audio_processor.AudioSegment')
    @patch('audio_processor.tempfile')
    def test_create_silence_audio(self, mock_tempfile, mock_audio_segment):
        """Test creating silence audio."""
        mock_silence = Mock()
        mock_audio_segment.silent.return_value = mock_silence
        
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/silence.wav"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
        
        result = create_silence_audio(3.5)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.duration, 3.5)
        mock_audio_segment.silent.assert_called_with(duration=3500)  # 3.5 seconds in ms


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
        
        self.assertEqual(voice.language, "en")
        self.assertEqual(voice.gender, "neutral")
        self.assertEqual(voice.provider, "pyttsx3")


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main()