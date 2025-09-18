"""
Demo script for audio processing pipeline.
Shows how to use TTSProcessor, AudioRemixer, and AudioManager.
"""

import sys
import os
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from audio_processor import TTSProcessor, AudioRemixer, AudioManager, Voice
from data_models import AudioFile


def demo_tts_processor():
    """Demonstrate TTSProcessor functionality."""
    print("=== TTS Processor Demo ===")
    
    # Initialize TTS processor
    tts = TTSProcessor()
    
    # Check availability
    availability = {
        'pyttsx3_engine': tts.pyttsx3_engine is not None,
        'elevenlabs_api_key': tts.elevenlabs_api_key is not None
    }
    print(f"TTS Availability: {availability}")
    
    # Get available voices
    voices = tts.get_available_voices()
    print(f"Available voices: {len(voices)}")
    for voice in voices[:3]:  # Show first 3 voices
        print(f"  - {voice.name} ({voice.provider}, {voice.language}, {voice.gender})")
    
    # Test text-to-speech (will fail without proper setup, but shows the interface)
    test_text = "Hello, this is a test of the text-to-speech system."
    print(f"\nTesting TTS with text: '{test_text}'")
    
    audio_result = tts.text_to_speech(test_text)
    if audio_result:
        print(f"TTS Success: {audio_result.file_path}")
        print(f"Duration: {audio_result.duration}s")
        print(f"Format: {audio_result.format}")
        print(f"Provider: {audio_result.metadata.get('provider', 'unknown')}")
    else:
        print("TTS failed (expected without proper dependencies/API keys)")
    
    print()


def demo_audio_remixer():
    """Demonstrate AudioRemixer functionality."""
    print("=== Audio Remixer Demo ===")
    
    remixer = AudioRemixer()
    
    # Create mock audio files for demonstration
    speech_audio = AudioFile(
        file_path="mock_speech.wav",
        duration=5.0,
        format="wav",
        metadata={"provider": "mock"}
    )
    
    music_audio = AudioFile(
        file_path="mock_music.wav",
        duration=10.0,
        format="wav",
        metadata={"provider": "mock"}
    )
    
    print("Testing remix creation...")
    
    # Test remix without background music
    result1 = remixer.create_remix(speech_audio)
    print(f"Remix without music: {result1 == speech_audio}")
    
    # Test remix with background music (will use fallback)
    result2 = remixer.create_remix(speech_audio, music_audio)
    if result2:
        print(f"Remix with music: Success")
        print(f"Provider: {result2.metadata.get('provider', 'unknown')}")
    else:
        print("Remix failed")
    
    # Test audio effects
    effects = {
        'volume': 3,  # +3 dB
        'fade_in': 0.5,  # 0.5 second fade in
        'fade_out': 1.0   # 1 second fade out
    }
    
    result3 = remixer.apply_audio_effects(speech_audio, effects)
    if result3:
        print(f"Effects applied: {result3.metadata.get('effects_applied', {})}")
    else:
        print("Effects application failed")
    
    print()


def demo_audio_manager():
    """Demonstrate AudioManager functionality."""
    print("=== Audio Manager Demo ===")
    
    # Initialize with mock API key
    manager = AudioManager(elevenlabs_api_key="demo_key_123")
    
    # Check processing availability
    availability = manager.is_audio_processing_available()
    print("Audio Processing Availability:")
    for feature, available in availability.items():
        status = "✓" if available else "✗"
        print(f"  {status} {feature}")
    
    # Test complete text-to-audio pipeline
    test_text = "Welcome to EchoVerse, your supportive companion."
    print(f"\nProcessing text: '{test_text}'")
    
    voice_settings = {
        'rate': 150,
        'volume': 0.8,
        'voice_id': 'EXAVITQu4vr4xnSDxMaL'  # Bella voice
    }
    
    result = manager.process_text_to_audio(
        text=test_text,
        voice_settings=voice_settings,
        background_music_path="assets/background_music.mp3",
        create_remix=True
    )
    
    print("Processing results:")
    print(f"  Speech audio: {'✓' if result['speech'] else '✗'}")
    print(f"  Remix audio: {'✓' if result['remix'] else '✗'}")
    
    # Test audio info
    if result['speech']:
        info = manager.get_audio_info(result['speech'])
        print(f"\nSpeech audio info:")
        print(f"  File exists: {info['exists']}")
        print(f"  Duration: {info['duration']}s")
        print(f"  Format: {info['format']}")
    
    print()


def demo_voice_data_class():
    """Demonstrate Voice data class."""
    print("=== Voice Data Class Demo ===")
    
    # Create different voice configurations
    voices = [
        Voice(id="voice1", name="Bella", language="en", gender="female", provider="elevenlabs"),
        Voice(id="voice2", name="Antoni", language="en", gender="male", provider="elevenlabs"),
        Voice(id="voice3", name="System Voice", provider="pyttsx3"),  # Uses defaults
    ]
    
    print("Voice configurations:")
    for voice in voices:
        print(f"  {voice.name}:")
        print(f"    ID: {voice.id}")
        print(f"    Language: {voice.language}")
        print(f"    Gender: {voice.gender}")
        print(f"    Provider: {voice.provider}")
    
    print()


def demo_utility_functions():
    """Demonstrate utility functions."""
    print("=== Utility Functions Demo ===")
    
    from audio_processor import (
        validate_audio_file, 
        get_default_background_music_path,
        create_silence_audio
    )
    
    # Test file validation
    test_files = [
        "test.wav",
        "test.mp3", 
        "test.txt",
        "/nonexistent/file.wav"
    ]
    
    print("Audio file validation:")
    for file_path in test_files:
        is_valid = validate_audio_file(file_path)
        status = "✓" if is_valid else "✗"
        print(f"  {status} {file_path}")
    
    # Test default background music
    default_music = get_default_background_music_path()
    print(f"\nDefault background music: {default_music or 'None found'}")
    
    # Test silence creation
    silence = create_silence_audio(2.5)
    if silence:
        print(f"Created silence: {silence.duration}s at {silence.file_path}")
    else:
        print("Silence creation failed (pydub not available)")
    
    print()


def main():
    """Run all demos."""
    print("Audio Processing Pipeline Demo")
    print("=" * 50)
    print()
    
    demo_tts_processor()
    demo_audio_remixer()
    demo_audio_manager()
    demo_voice_data_class()
    demo_utility_functions()
    
    print("Demo completed!")
    print("\nNote: Some features may not work fully without:")
    print("- pyttsx3 library for local TTS")
    print("- ElevenLabs API key for premium TTS")
    print("- pydub library for audio processing")
    print("- requests library for API calls")


if __name__ == "__main__":
    main()