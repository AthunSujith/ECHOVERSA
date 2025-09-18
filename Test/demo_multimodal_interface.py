#!/usr/bin/env python3
"""
Demo script to test the multi-modal input interface in Streamlit.
This script demonstrates the functionality without running the full UI.
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
from datetime import datetime
import tempfile
import io
from PIL import Image
import base64


def demo_text_processing():
    """Demonstrate text input processing."""
    print("🔤 TEXT INPUT PROCESSING DEMO")
    print("-" * 40)
    
    processor = InputProcessor()
    
    # Test various text inputs
    test_inputs = [
        "I'm feeling overwhelmed with work today and need some encouragement.",
        "I had an amazing day and want to celebrate my achievements!",
        "I'm worried about my upcoming presentation and feeling anxious.",
        "Just a short message.",
        "A" * 50 + " - This is a longer message to test character limits and processing."
    ]
    
    for i, text in enumerate(test_inputs, 1):
        print(f"\n📝 Test {i}: Processing text input...")
        print(f"   Input: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            processed = processor.process_text_input(
                text,
                metadata={"source": "demo", "timestamp": datetime.now().isoformat()}
            )
            
            print(f"   ✅ Success: {processed.input_type.value}")
            print(f"   📊 Length: {len(processed.content)} chars")
            print(f"   🔧 Method: {processed.metadata.get('processing_method')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_audio_processing():
    """Demonstrate audio input processing."""
    print("\n\n🎤 AUDIO INPUT PROCESSING DEMO")
    print("-" * 40)
    
    processor = InputProcessor()
    
    # Create mock audio files with different formats
    audio_tests = [
        ("WAV", b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00' + b'\x00' * 1024),
        ("MP3", b'ID3\x03\x00\x00\x00' + b'\x00' * 512),
        ("OGG", b'OggS\x00\x02\x00\x00' + b'\x00' * 256),
    ]
    
    for i, (format_name, audio_data) in enumerate(audio_tests, 1):
        print(f"\n🎵 Test {i}: Processing {format_name} audio...")
        print(f"   File size: {len(audio_data)} bytes")
        
        try:
            processed = processor.process_audio_input(
                audio_data,
                filename=f"test_audio_{i}.{format_name.lower()}",
                metadata={
                    "source": "demo",
                    "timestamp": datetime.now().isoformat(),
                    "format": format_name
                }
            )
            
            print(f"   ✅ Success: {processed.input_type.value}")
            print(f"   📁 Content: {processed.content}")
            print(f"   🔤 Transcription attempted: {processed.metadata.get('transcription_attempted')}")
            print(f"   📊 Raw data size: {len(processed.raw_data)} bytes")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_drawing_processing():
    """Demonstrate drawing input processing."""
    print("\n\n🎨 DRAWING INPUT PROCESSING DEMO")
    print("-" * 40)
    
    processor = InputProcessor()
    
    # Test 1: Canvas data processing
    print("\n🖌️ Test 1: Processing canvas data...")
    canvas_data = {
        "width": 500,
        "height": 300,
        "strokes": [
            {"type": "path", "points": [[10, 10], [50, 50], [100, 30]], "color": "#FF0000"},
            {"type": "circle", "center": [200, 150], "radius": 25, "color": "#00FF00"},
            {"type": "rect", "x": 300, "y": 100, "width": 80, "height": 60, "color": "#0000FF"}
        ],
        "background_color": "#FFFFFF"
    }
    
    try:
        processed = processor.process_drawing_input(
            canvas_data,
            metadata={"source": "demo", "timestamp": datetime.now().isoformat()}
        )
        
        print(f"   ✅ Success: {processed.input_type.value}")
        print(f"   📝 Description: {processed.content}")
        print(f"   🖼️ PNG generated: {processed.metadata.get('has_png_data')}")
        print(f"   📊 PNG size: {processed.metadata.get('png_size', 0)} bytes")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Base64 image processing
    print("\n🖼️ Test 2: Processing base64 image...")
    
    # Create a simple test image
    test_image = Image.new('RGB', (200, 200), color='lightblue')
    # Draw a simple pattern
    from PIL import ImageDraw
    draw = ImageDraw.Draw(test_image)
    draw.ellipse([50, 50, 150, 150], fill='red', outline='black')
    draw.rectangle([75, 75, 125, 125], fill='yellow')
    
    # Convert to base64
    buffer = io.BytesIO()
    test_image.save(buffer, format='PNG')
    image_data = buffer.getvalue()
    base64_data = base64.b64encode(image_data).decode()
    base64_with_prefix = f"data:image/png;base64,{base64_data}"
    
    try:
        processed = processor.process_drawing_input(
            base64_with_prefix,
            metadata={"source": "demo", "timestamp": datetime.now().isoformat()}
        )
        
        print(f"   ✅ Success: {processed.input_type.value}")
        print(f"   📝 Description: {processed.content}")
        print(f"   🖼️ PNG processed: {processed.metadata.get('has_png_data')}")
        print(f"   📊 PNG size: {processed.metadata.get('png_size', 0)} bytes")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def demo_validation():
    """Demonstrate input validation."""
    print("\n\n🔍 INPUT VALIDATION DEMO")
    print("-" * 40)
    
    processor = InputProcessor()
    
    # Test invalid inputs
    validation_tests = [
        ("Empty text", lambda: processor.process_text_input("")),
        ("None text", lambda: processor.process_text_input(None)),
        ("Empty audio", lambda: processor.process_audio_input(b"", "empty.wav")),
        ("Invalid audio", lambda: processor.process_audio_input(b"not audio data", "fake.wav")),
        ("None drawing", lambda: processor.process_drawing_input(None)),
        ("Empty canvas", lambda: processor.process_drawing_input({})),
    ]
    
    for test_name, test_func in validation_tests:
        print(f"\n🧪 Testing: {test_name}")
        try:
            result = test_func()
            print(f"   ⚠️ Unexpected success: {result}")
        except ValueError as e:
            print(f"   ✅ Correctly rejected: {e}")
        except Exception as e:
            print(f"   ❓ Unexpected error: {e}")


def main():
    """Run the multi-modal input interface demo."""
    print("🎯 MULTI-MODAL INPUT INTERFACE DEMO")
    print("=" * 50)
    print("This demo shows the input processing capabilities")
    print("that power the Streamlit multi-modal interface.")
    print("=" * 50)
    
    try:
        demo_text_processing()
        demo_audio_processing()
        demo_drawing_processing()
        demo_validation()
        
        print("\n" + "=" * 50)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("The multi-modal input interface is ready for use.")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()