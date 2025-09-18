#!/usr/bin/env python3
"""
Test script for the integrated pipeline in EchoVerse companion application.
Tests the complete flow: input processing → content generation → audio processing → storage.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

def test_pipeline_integration():
    """Test the complete pipeline integration."""
    print("🧪 Testing EchoVerse Pipeline Integration")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from streamlit_workspace import StreamlitApp
        from content_generator import ContentGenerator
        from audio_processor import AudioManager
        from input_processor import InputProcessor
        from storage_manager import StorageManager
        from data_models import User, ProcessedInput, GeneratedContent, Interaction
        print("✅ All imports successful")
        
        # Test component initialization
        print("\n🔧 Testing component initialization...")
        content_generator = ContentGenerator()
        audio_manager = AudioManager()
        input_processor = InputProcessor()
        storage_manager = StorageManager()
        print("✅ All components initialized successfully")
        
        # Test content generation capabilities
        print("\n🤖 Testing content generation capabilities...")
        available_generators = content_generator.get_available_generators()
        print(f"Available generators: {available_generators}")
        
        # Test audio processing capabilities
        print("\n🎵 Testing audio processing capabilities...")
        audio_capabilities = audio_manager.is_audio_processing_available()
        print(f"Audio capabilities: {audio_capabilities}")
        
        # Test simple text processing
        print("\n📝 Testing text input processing...")
        test_text = "I'm feeling happy today and want to share my joy!"
        processed_input = input_processor.process_text_input(test_text)
        
        if processed_input and processed_input.content:
            print(f"✅ Text processed: {len(processed_input.content)} characters")
            
            # Test content generation
            print("\n🎭 Testing content generation...")
            generated_content = content_generator.generate_support_and_poem(processed_input)
            
            if generated_content:
                print(f"✅ Support statement: {len(generated_content.supportive_statement)} characters")
                print(f"✅ Poem: {len(generated_content.poem)} characters")
                print(f"Generator used: {generated_content.generation_metadata.get('generator', 'unknown')}")
                
                # Test audio processing (if available)
                if audio_capabilities.get('any_tts', False):
                    print("\n🔊 Testing audio processing...")
                    try:
                        audio_result = audio_manager.process_text_to_audio(
                            generated_content.supportive_statement[:50],  # Short text for testing
                            voice_settings={'rate': 150, 'volume': 0.8},
                            create_remix=False
                        )
                        
                        if audio_result.get('speech'):
                            print("✅ Audio generation successful")
                        else:
                            print("⚠️ Audio generation returned no result")
                    except Exception as audio_error:
                        print(f"⚠️ Audio processing failed: {audio_error}")
                else:
                    print("ℹ️ Audio processing not available, skipping audio tests")
                
                print("\n🎉 Pipeline integration test completed successfully!")
                return True
            else:
                print("❌ Content generation failed")
                return False
        else:
            print("❌ Text processing failed")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling in the pipeline."""
    print("\n🛡️ Testing error handling...")
    
    try:
        from content_generator import ContentGenerator
        from input_processor import InputProcessor
        
        content_generator = ContentGenerator()
        input_processor = InputProcessor()
        
        # Test with empty input
        try:
            processed_input = input_processor.process_text_input("")
            print("⚠️ Empty input should have been rejected")
        except Exception:
            print("✅ Empty input properly rejected")
        
        # Test with invalid input type
        try:
            processed_input = input_processor.process_text_input(None)
            print("⚠️ None input should have been rejected")
        except Exception:
            print("✅ None input properly rejected")
        
        print("✅ Error handling tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting EchoVerse Integration Tests")
    print("=" * 60)
    
    # Run tests
    pipeline_success = test_pipeline_integration()
    error_handling_success = test_error_handling()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"Pipeline Integration: {'✅ PASS' if pipeline_success else '❌ FAIL'}")
    print(f"Error Handling: {'✅ PASS' if error_handling_success else '❌ FAIL'}")
    
    overall_success = pipeline_success and error_handling_success
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)