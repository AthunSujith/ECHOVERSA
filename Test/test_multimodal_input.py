#!/usr/bin/env python3
"""
Test script for multi-modal input interface functionality.
Tests the InputProcessor integration with the Streamlit UI.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Import required modules
from input_processor import InputProcessor
from data_models import InputType, ProcessedInput
import tempfile
import io
from PIL import Image
import base64


def test_input_processor_initialization():
    """Test that InputProcessor can be initialized successfully."""
    print("Testing InputProcessor initialization...")
    try:
        processor = InputProcessor()
        print("✅ InputProcessor initialized successfully")
        return True
    except Exception as e:
        print(f"❌ InputProcessor initialization failed: {e}")
        return False


def test_text_input_processing():
    """Test text input processing functionality."""
    print("\nTesting text input processing...")
    try:
        processor = InputProcessor()
        
        # Test valid text input
        test_text = "I'm feeling happy today and want to share my joy with the world!"
        processed = processor.process_text_input(test_text)
        
        assert isinstance(processed, ProcessedInput)
        assert processed.input_type == InputType.TEXT
        assert processed.content == test_text
        assert processed.metadata is not None
        
        print(f"✅ Text input processed successfully: '{processed.content[:50]}...'")
        print(f"   Metadata: {processed.metadata}")
        return True
        
    except Exception as e:
        print(f"❌ Text input processing failed: {e}")
        return False


def test_audio_input_processing():
    """Test audio input processing functionality."""
    print("\nTesting audio input processing...")
    try:
        processor = InputProcessor()
        
        # Create a mock audio file (simple WAV header)
        mock_audio_data = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
        mock_audio_data += b'\x00' * 2048  # Add some audio data
        
        processed = processor.process_audio_input(mock_audio_data, "test_audio.wav")
        
        assert isinstance(processed, ProcessedInput)
        assert processed.input_type == InputType.AUDIO
        assert processed.raw_data == mock_audio_data
        assert processed.metadata is not None
        
        print(f"✅ Audio input processed successfully: '{processed.content}'")
        print(f"   File size: {len(processed.raw_data)} bytes")
        print(f"   Transcription attempted: {processed.metadata.get('transcription_attempted', False)}")
        return True
        
    except Exception as e:
        print(f"❌ Audio input processing failed: {e}")
        return False


def test_drawing_input_processing():
    """Test drawing input processing functionality."""
    print("\nTesting drawing input processing...")
    try:
        processor = InputProcessor()
        
        # Create a simple test image
        test_image = Image.new('RGB', (400, 400), color='white')
        
        # Convert to base64
        buffer = io.BytesIO()
        test_image.save(buffer, format='PNG')
        image_data = buffer.getvalue()
        base64_data = base64.b64encode(image_data).decode()
        base64_with_prefix = f"data:image/png;base64,{base64_data}"
        
        processed = processor.process_drawing_input(base64_with_prefix)
        
        assert isinstance(processed, ProcessedInput)
        assert processed.input_type == InputType.DRAWING
        assert processed.raw_data is not None
        assert processed.metadata is not None
        
        print(f"✅ Drawing input processed successfully: '{processed.content}'")
        print(f"   PNG size: {len(processed.raw_data)} bytes")
        print(f"   Has PNG data: {processed.metadata.get('has_png_data', False)}")
        return True
        
    except Exception as e:
        print(f"❌ Drawing input processing failed: {e}")
        return False


def test_canvas_data_processing():
    """Test canvas data processing functionality."""
    print("\nTesting canvas data processing...")
    try:
        processor = InputProcessor()
        
        # Create mock canvas data
        canvas_data = {
            "width": 400,
            "height": 400,
            "strokes": [
                {"type": "path", "points": [[10, 10], [50, 50], [100, 30]]},
                {"type": "circle", "center": [200, 200], "radius": 25}
            ],
            "background_color": "white"
        }
        
        processed = processor.process_drawing_input(canvas_data)
        
        assert isinstance(processed, ProcessedInput)
        assert processed.input_type == InputType.DRAWING
        assert processed.metadata is not None
        
        print(f"✅ Canvas data processed successfully: '{processed.content}'")
        print(f"   Canvas size: {canvas_data['width']}x{canvas_data['height']}")
        print(f"   Stroke count: {len(canvas_data['strokes'])}")
        return True
        
    except Exception as e:
        print(f"❌ Canvas data processing failed: {e}")
        return False


def test_input_validation():
    """Test input validation functionality."""
    print("\nTesting input validation...")
    try:
        processor = InputProcessor()
        
        # Test empty text input
        try:
            processor.process_text_input("")
            print("❌ Empty text input should have failed")
            return False
        except ValueError:
            print("✅ Empty text input correctly rejected")
        
        # Test invalid audio input
        try:
            processor.process_audio_input(b"", "empty.wav")
            print("❌ Empty audio input should have failed")
            return False
        except ValueError:
            print("✅ Empty audio input correctly rejected")
        
        # Test invalid drawing input
        try:
            processor.process_drawing_input(None)
            print("❌ None drawing input should have failed")
            return False
        except ValueError:
            print("✅ None drawing input correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Input validation testing failed: {e}")
        return False


def main():
    """Run all tests for multi-modal input interface."""
    print("🧪 Testing Multi-Modal Input Interface")
    print("=" * 50)
    
    tests = [
        test_input_processor_initialization,
        test_text_input_processing,
        test_audio_input_processing,
        test_drawing_input_processing,
        test_canvas_data_processing,
        test_input_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Multi-modal input interface is working correctly.")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)