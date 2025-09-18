"""
Audio processing module for EchoVerse companion application.
Handles text-to-speech conversion, audio remixing, and audio file management
with graceful fallback systems for offline functionality.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import tempfile

from defensive_system import (
    defensive_wrapper, safe_api_call, get_defensive_logger, 
    get_degradation_manager, get_notification_manager, SeverityLevel,
    get_dependency_checker
)
from performance_optimizer import (
    get_performance_optimizer, monitor_performance, cache_result,
    LoadingIndicator, ProgressTracker
)

# Import with defensive fallback handling
dependency_checker = get_dependency_checker()
logger = get_defensive_logger("audio_processor")
degradation_manager = get_degradation_manager()
notification_manager = get_notification_manager()

# Check dependencies with defensive system
pyttsx3_dep = dependency_checker.check_dependency(
    "pyttsx3", 
    required=False, 
    fallback_available=True, 
    fallback_description="Mock TTS generator"
)
PYTTSX3_AVAILABLE = pyttsx3_dep.available

requests_dep = dependency_checker.check_dependency(
    "requests", 
    required=False, 
    fallback_available=True, 
    fallback_description="Local-only mode"
)
REQUESTS_AVAILABLE = requests_dep.available

pydub_dep = dependency_checker.check_dependency(
    "pydub", 
    required=False, 
    fallback_available=True, 
    fallback_description="Numpy-based audio mixing"
)
PYDUB_AVAILABLE = pydub_dep.available

numpy_dep = dependency_checker.check_dependency(
    "numpy", 
    required=False, 
    fallback_available=True, 
    fallback_description="Basic audio operations"
)
NUMPY_AVAILABLE = numpy_dep.available

# Import modules if available
if PYTTSX3_AVAILABLE:
    import pyttsx3

if REQUESTS_AVAILABLE:
    import requests

if PYDUB_AVAILABLE:
    from pydub import AudioSegment

if NUMPY_AVAILABLE:
    import numpy as np

try:
    import shutil
    SHUTIL_AVAILABLE = True
except ImportError:
    SHUTIL_AVAILABLE = False

try:
    from .data_models import AudioFile
except ImportError:
    from data_models import AudioFile


@dataclass
class Voice:
    """Voice configuration for TTS."""
    id: str
    name: str
    language: str = "en"
    gender: str = "neutral"
    provider: str = "pyttsx3"


class TTSProcessor:
    """
    Text-to-speech processor with ElevenLabs API and pyttsx3 fallback.
    Handles voice synthesis with graceful degradation.
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize TTS processor with LOCAL MODELS ONLY - ElevenLabs disabled.
        
        Args:
            elevenlabs_api_key: Ignored - using only local TTS
        """
        self.elevenlabs_api_key = None  # Force disable ElevenLabs
        self.logger = logging.getLogger(__name__)
        self.logger.info("TTS initialized with LOCAL MODELS ONLY - ElevenLabs API disabled")
        
        # Initialize pyttsx3 engine if available
        self.pyttsx3_engine = None
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                self._configure_pyttsx3()
            except Exception as e:
                self.logger.warning(f"Failed to initialize pyttsx3: {e}")
                self.pyttsx3_engine = None
    
    def _configure_pyttsx3(self):
        """Configure pyttsx3 engine with optimal settings."""
        if not self.pyttsx3_engine:
            return
            
        try:
            # Set speech rate (words per minute)
            self.pyttsx3_engine.setProperty('rate', 150)
            
            # Set volume (0.0 to 1.0)
            self.pyttsx3_engine.setProperty('volume', 0.8)
            
            # Try to set a pleasant voice
            voices = self.pyttsx3_engine.getProperty('voices')
            if voices:
                # Prefer female voices for supportive content
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.pyttsx3_engine.setProperty('voice', voice.id)
                        break
        except Exception as e:
            self.logger.warning(f"Failed to configure pyttsx3: {e}")    

    @defensive_wrapper(fallback_value=None, component_name="tts_processor")
    @monitor_performance("text_to_speech_conversion")
    def text_to_speech(self, text: str, voice_settings: Optional[Dict[str, Any]] = None) -> Optional[AudioFile]:
        """
        Convert text to speech using ElevenLabs API with pyttsx3 fallback.
        
        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration
            
        Returns:
            AudioFile object or None if conversion fails
        """
        if not text or not text.strip():
            logger.logger.error("Empty text provided for TTS conversion")
            return None
        
        voice_settings = voice_settings or {}
        
        # Try ElevenLabs first if API key is available
        if self.elevenlabs_api_key and REQUESTS_AVAILABLE:
            def elevenlabs_call():
                return self._elevenlabs_tts(text, voice_settings)
            
            def pyttsx3_fallback():
                if self.pyttsx3_engine:
                    return self._pyttsx3_tts(text, voice_settings)
                return None
            
            result, success = safe_api_call(
                api_name="elevenlabs_tts",
                api_function=elevenlabs_call,
                fallback_function=pyttsx3_fallback,
                max_retries=2
            )
            
            if result:
                if not success:
                    degradation_manager.register_component_degradation(
                        component="elevenlabs_api",
                        reason="API call failed",
                        impact="Using local TTS instead",
                        severity=SeverityLevel.LOW
                    )
                return result
        
        # Direct fallback to pyttsx3
        if self.pyttsx3_engine:
            return self._pyttsx3_tts(text, voice_settings)
        
        # No TTS engines available
        degradation_manager.register_component_failure(
            component="tts_engines",
            error=Exception("No TTS engines available"),
            fallback_description="Text-only mode"
        )
        
        logger.logger.error("No TTS engines available")
        return None
    
    @defensive_wrapper(fallback_value=None, component_name="elevenlabs_tts")
    def _elevenlabs_tts(self, text: str, voice_settings: Dict[str, Any]) -> Optional[AudioFile]:
        """
        Convert text to speech using ElevenLabs API with defensive error handling.
        
        Args:
            text: Text to convert
            voice_settings: Voice configuration
            
        Returns:
            AudioFile object or None if conversion fails
        """
        try:
            voice_id = voice_settings.get('voice_id', 'EXAVITQu4vr4xnSDxMaL')  # Default voice
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": voice_settings.get('stability', 0.5),
                    "similarity_boost": voice_settings.get('similarity_boost', 0.5)
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Save audio to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(response.content)
                temp_file.close()
                
                # Convert to WAV if pydub is available
                if PYDUB_AVAILABLE:
                    try:
                        audio = AudioSegment.from_mp3(temp_file.name)
                        wav_file = temp_file.name.replace('.mp3', '.wav')
                        audio.export(wav_file, format="wav")
                        os.unlink(temp_file.name)  # Remove MP3 file
                        
                        return AudioFile(
                            file_path=wav_file,
                            duration=len(audio) / 1000.0,  # Convert to seconds
                            format="wav",
                            metadata={"provider": "elevenlabs", "voice_id": voice_id}
                        )
                    except Exception as conversion_error:
                        logger.logger.warning(f"Audio conversion failed, using MP3: {conversion_error}")
                        # Fallback to MP3 if conversion fails
                        return AudioFile(
                            file_path=temp_file.name,
                            format="mp3",
                            metadata={"provider": "elevenlabs", "voice_id": voice_id, "conversion_failed": True}
                        )
                else:
                    return AudioFile(
                        file_path=temp_file.name,
                        format="mp3",
                        metadata={"provider": "elevenlabs", "voice_id": voice_id}
                    )
            else:
                logger.logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                # Register API failure for monitoring
                degradation_manager.register_component_degradation(
                    component="elevenlabs_api",
                    reason=f"HTTP {response.status_code}",
                    impact="Will use local TTS",
                    severity=SeverityLevel.MEDIUM
                )
                return None
                
        except requests.exceptions.Timeout:
            logger.logger.error("ElevenLabs API timeout")
            degradation_manager.register_component_degradation(
                component="elevenlabs_api",
                reason="API timeout",
                impact="Will use local TTS",
                severity=SeverityLevel.MEDIUM
            )
            return None
        except requests.exceptions.ConnectionError:
            logger.logger.error("ElevenLabs API connection error")
            degradation_manager.register_component_degradation(
                component="elevenlabs_api",
                reason="Connection error",
                impact="Will use local TTS",
                severity=SeverityLevel.MEDIUM
            )
            return None
        except Exception as e:
            logger.logger.error(f"ElevenLabs TTS failed: {e}")
            return None
    
    def _pyttsx3_tts(self, text: str, voice_settings: Dict[str, Any]) -> Optional[AudioFile]:
        """
        Convert text to speech using pyttsx3.
        
        Args:
            text: Text to convert
            voice_settings: Voice configuration
            
        Returns:
            AudioFile object or None if conversion fails
        """
        try:
            # Create temporary file for output
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Configure engine with voice settings
            if 'rate' in voice_settings:
                self.pyttsx3_engine.setProperty('rate', voice_settings['rate'])
            if 'volume' in voice_settings:
                self.pyttsx3_engine.setProperty('volume', voice_settings['volume'])
            
            # Save to file
            self.pyttsx3_engine.save_to_file(text, temp_file.name)
            self.pyttsx3_engine.runAndWait()
            
            return AudioFile(
                file_path=temp_file.name,
                format="wav",
                metadata={"provider": "pyttsx3"}
            )
            
        except Exception as e:
            self.logger.error(f"pyttsx3 TTS failed: {e}")
            return None
    
    def get_available_voices(self) -> List[Voice]:
        """
        Get list of available voices from all providers.
        
        Returns:
            List of Voice objects
        """
        voices = []
        
        # Add pyttsx3 voices if available
        if self.pyttsx3_engine:
            try:
                pyttsx3_voices = self.pyttsx3_engine.getProperty('voices')
                for voice in pyttsx3_voices:
                    voices.append(Voice(
                        id=voice.id,
                        name=voice.name,
                        language=getattr(voice, 'languages', ['en'])[0] if hasattr(voice, 'languages') else 'en',
                        gender='female' if 'female' in voice.name.lower() else 'male',
                        provider='pyttsx3'
                    ))
            except Exception as e:
                self.logger.warning(f"Failed to get pyttsx3 voices: {e}")
        
        # Add default ElevenLabs voices if API key is available
        if self.elevenlabs_api_key:
            voices.extend([
                Voice(id='EXAVITQu4vr4xnSDxMaL', name='Bella', language='en', gender='female', provider='elevenlabs'),
                Voice(id='ErXwobaYiN019PkySvjV', name='Antoni', language='en', gender='male', provider='elevenlabs'),
                Voice(id='MF3mGyEYCl7XYWbV9V6O', name='Elli', language='en', gender='female', provider='elevenlabs'),
            ])
        
        return voices


class AudioRemixer:
    """
    Audio remixer for combining speech with background music.
    Supports pydub and numpy fallback implementations.
    """
    
    def __init__(self):
        """Initialize audio remixer with available libraries."""
        self.logger = logging.getLogger(__name__)
    
    def create_remix(self, speech_audio: AudioFile, background_music: Optional[AudioFile] = None,
                    volume_ratio: float = 0.7) -> Optional[AudioFile]:
        """
        Create audio remix by combining speech with background music.
        
        Args:
            speech_audio: Primary speech audio file
            background_music: Optional background music file
            volume_ratio: Speech to music volume ratio (0.0 to 1.0)
            
        Returns:
            AudioFile object with remixed audio or None if failed
        """
        if not speech_audio or not os.path.exists(speech_audio.file_path):
            self.logger.error("Invalid speech audio file")
            return None
        
        # If no background music, return original speech
        if not background_music or not os.path.exists(background_music.file_path):
            return speech_audio
        
        # Try pydub first
        if PYDUB_AVAILABLE:
            return self._pydub_remix(speech_audio, background_music, volume_ratio)
        
        # Fallback to numpy
        if NUMPY_AVAILABLE:
            return self._numpy_remix(speech_audio, background_music, volume_ratio)
        
        self.logger.warning("No audio mixing libraries available, returning original speech")
        return speech_audio
    
    def _pydub_remix(self, speech_audio: AudioFile, background_music: AudioFile,
                    volume_ratio: float) -> Optional[AudioFile]:
        """
        Create remix using pydub library.
        
        Args:
            speech_audio: Speech audio file
            background_music: Background music file
            volume_ratio: Volume ratio for mixing
            
        Returns:
            AudioFile with remixed audio or None if failed
        """
        try:
            # Load audio files
            speech = AudioSegment.from_file(speech_audio.file_path)
            music = AudioSegment.from_file(background_music.file_path)
            
            # Adjust music length to match speech
            if len(music) < len(speech):
                # Loop music to match speech length
                loops_needed = (len(speech) // len(music)) + 1
                music = music * loops_needed
            
            # Trim music to speech length
            music = music[:len(speech)]
            
            # Adjust volumes
            speech_volume = volume_ratio
            music_volume = 1.0 - volume_ratio
            
            speech = speech + (20 * np.log10(speech_volume))  # Convert to dB
            music = music + (20 * np.log10(music_volume))
            
            # Mix audio
            mixed = speech.overlay(music)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            mixed.export(temp_file.name, format="wav")
            
            return AudioFile(
                file_path=temp_file.name,
                duration=len(mixed) / 1000.0,
                format="wav",
                metadata={
                    "provider": "pydub_remix",
                    "speech_file": speech_audio.file_path,
                    "music_file": background_music.file_path,
                    "volume_ratio": volume_ratio
                }
            )
            
        except Exception as e:
            self.logger.error(f"Pydub remix failed: {e}")
            return None
    
    def _numpy_remix(self, speech_audio: AudioFile, background_music: AudioFile,
                    volume_ratio: float) -> Optional[AudioFile]:
        """
        Create remix using numpy fallback (basic implementation).
        
        Args:
            speech_audio: Speech audio file
            background_music: Background music file
            volume_ratio: Volume ratio for mixing
            
        Returns:
            AudioFile with remixed audio or None if failed
        """
        try:
            # This is a simplified implementation
            # In a real scenario, you'd need to read WAV files properly
            # For now, we'll just copy the speech file and add metadata
            
            import shutil
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Copy speech file as fallback
            shutil.copy2(speech_audio.file_path, temp_file.name)
            
            return AudioFile(
                file_path=temp_file.name,
                duration=speech_audio.duration,
                format="wav",
                metadata={
                    "provider": "numpy_fallback",
                    "speech_file": speech_audio.file_path,
                    "music_file": background_music.file_path,
                    "volume_ratio": volume_ratio,
                    "note": "Fallback implementation - music not actually mixed"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Numpy remix fallback failed: {e}")
            return None
    
    def apply_audio_effects(self, audio: AudioFile, effects: Dict[str, Any]) -> Optional[AudioFile]:
        """
        Apply audio effects to an audio file.
        
        Args:
            audio: Input audio file
            effects: Dictionary of effects to apply
            
        Returns:
            AudioFile with effects applied or None if failed
        """
        if not audio or not os.path.exists(audio.file_path):
            return None
        
        if not PYDUB_AVAILABLE:
            self.logger.warning("Pydub not available - effects not applied")
            return audio
        
        try:
            audio_segment = AudioSegment.from_file(audio.file_path)
            
            # Apply volume adjustment
            if 'volume' in effects:
                volume_change = effects['volume']  # in dB
                audio_segment = audio_segment + volume_change
            
            # Apply fade in/out
            if 'fade_in' in effects:
                fade_in_ms = int(effects['fade_in'] * 1000)
                audio_segment = audio_segment.fade_in(fade_in_ms)
            
            if 'fade_out' in effects:
                fade_out_ms = int(effects['fade_out'] * 1000)
                audio_segment = audio_segment.fade_out(fade_out_ms)
            
            # Save processed audio
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            audio_segment.export(temp_file.name, format="wav")
            
            return AudioFile(
                file_path=temp_file.name,
                duration=len(audio_segment) / 1000.0,
                format="wav",
                metadata={
                    **audio.metadata,
                    "effects_applied": effects,
                    "processed_by": "pydub_effects"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Audio effects processing failed: {e}")
            return audio


class AudioManager:
    """
    Main audio manager that coordinates TTS and remixing operations.
    Provides high-level interface for audio processing pipeline.
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize audio manager with TTS and remixing capabilities.
        
        Args:
            elevenlabs_api_key: Optional ElevenLabs API key
        """
        self.tts_processor = TTSProcessor(elevenlabs_api_key)
        self.audio_remixer = AudioRemixer()
        self.logger = logging.getLogger(__name__)
    
    @monitor_performance("complete_audio_processing")
    def process_text_to_audio(self, text: str, voice_settings: Optional[Dict[str, Any]] = None,
                             background_music_path: Optional[str] = None,
                             create_remix: bool = False) -> Dict[str, Optional[AudioFile]]:
        """
        Complete text-to-audio processing pipeline.
        
        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration
            background_music_path: Optional path to background music
            create_remix: Whether to create remixed version
            
        Returns:
            Dictionary with 'speech' and optionally 'remix' AudioFile objects
        """
        result = {'speech': None, 'remix': None}
        
        # Determine total steps for progress tracking
        total_steps = 2 if (create_remix and background_music_path) else 1
        progress = ProgressTracker(total_steps, "Processing audio")
        
        try:
            # Convert text to speech
            progress.update(1, "Converting text to speech")
            with LoadingIndicator("Converting text to speech...", show_spinner=False):
                speech_audio = self.tts_processor.text_to_speech(text, voice_settings)
                if not speech_audio:
                    self.logger.error("Failed to convert text to speech")
                    progress.complete("Text-to-speech failed")
                    return result
                
                result['speech'] = speech_audio
            
            # Create remix if requested and background music is provided
            if create_remix and background_music_path:
                progress.update(2, "Creating audio remix")
                with LoadingIndicator("Creating audio remix...", show_spinner=False):
                    background_music = AudioFile(file_path=background_music_path)
                    remix_audio = self.audio_remixer.create_remix(speech_audio, background_music)
                    result['remix'] = remix_audio
            
            progress.complete("Audio processing complete")
            return result
            
        except Exception as e:
            progress.complete(f"Error: {str(e)}")
            raise
    
    def get_audio_info(self, audio_file: AudioFile) -> Dict[str, Any]:
        """
        Get detailed information about an audio file.
        
        Args:
            audio_file: AudioFile to analyze
            
        Returns:
            Dictionary with audio file information
        """
        info = {
            'file_path': audio_file.file_path,
            'format': audio_file.format,
            'duration': audio_file.duration,
            'metadata': audio_file.metadata,
            'exists': os.path.exists(audio_file.file_path) if audio_file.file_path else False,
            'file_size': None
        }
        
        if info['exists']:
            try:
                info['file_size'] = os.path.getsize(audio_file.file_path)
                
                # Get additional info with pydub if available
                if PYDUB_AVAILABLE:
                    audio_segment = AudioSegment.from_file(audio_file.file_path)
                    info.update({
                        'channels': audio_segment.channels,
                        'frame_rate': audio_segment.frame_rate,
                        'sample_width': audio_segment.sample_width,
                        'duration_precise': len(audio_segment) / 1000.0
                    })
            except Exception as e:
                self.logger.warning(f"Failed to get audio info: {e}")
        
        return info
    
    def cleanup_temp_files(self, audio_files: List[AudioFile]):
        """
        Clean up temporary audio files.
        
        Args:
            audio_files: List of AudioFile objects to clean up
        """
        for audio_file in audio_files:
            if audio_file and audio_file.file_path:
                try:
                    if os.path.exists(audio_file.file_path) and 'tmp' in audio_file.file_path:
                        os.unlink(audio_file.file_path)
                        self.logger.debug(f"Cleaned up temp file: {audio_file.file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp file {audio_file.file_path}: {e}")
    
    def is_audio_processing_available(self) -> Dict[str, bool]:
        """
        Check availability of audio processing capabilities.
        
        Returns:
            Dictionary indicating which features are available
        """
        return {
            'pyttsx3_tts': PYTTSX3_AVAILABLE and self.tts_processor.pyttsx3_engine is not None,
            'elevenlabs_tts': bool(self.tts_processor.elevenlabs_api_key and REQUESTS_AVAILABLE),
            'pydub_mixing': PYDUB_AVAILABLE,
            'numpy_fallback': NUMPY_AVAILABLE,
            'any_tts': (PYTTSX3_AVAILABLE and self.tts_processor.pyttsx3_engine is not None) or 
                      (bool(self.tts_processor.elevenlabs_api_key and REQUESTS_AVAILABLE))
        }


# Utility functions for audio processing

def get_default_background_music_path() -> Optional[str]:
    """
    Get path to default background music file if available.
    
    Returns:
        Path to default background music or None
    """
    # Look for common background music files in the project
    possible_paths = [
        'assets/background_music.mp3',
        'assets/background_music.wav',
        'audio/background.mp3',
        'audio/background.wav',
        'resources/music.mp3'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def validate_audio_file(file_path: str) -> bool:
    """
    Validate if a file is a valid audio file.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        True if valid audio file, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    # Check file extension
    valid_extensions = ['.wav', '.mp3', '.m4a', '.ogg', '.flac']
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext not in valid_extensions:
        return False
    
    # Try to load with pydub if available
    if PYDUB_AVAILABLE:
        try:
            AudioSegment.from_file(file_path)
            return True
        except Exception:
            return False
    
    # Basic validation - file exists and has valid extension
    return True


def create_silence_audio(duration_seconds: float) -> Optional[AudioFile]:
    """
    Create a silent audio file of specified duration.
    
    Args:
        duration_seconds: Duration of silence in seconds
        
    Returns:
        AudioFile with silence or None if failed
    """
    if not PYDUB_AVAILABLE:
        return None
    
    try:
        silence = AudioSegment.silent(duration=int(duration_seconds * 1000))
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        silence.export(temp_file.name, format="wav")
        
        return AudioFile(
            file_path=temp_file.name,
            duration=duration_seconds,
            format="wav",
            metadata={"provider": "pydub_silence"}
        )
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to create silence: {e}")
        return None