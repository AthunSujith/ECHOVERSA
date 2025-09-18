#!/usr/bin/env python3
"""
Test script for local model integration
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from data_models import ProcessedInput, InputType
from content_generator import LocalModelGenerator, ContentGenerator

def test_local_model():
    """Test local model generation"""
    print("🧪 Testing Local Model Integration")
    print("=" * 50)
    
    # Test input
    test_input = ProcessedInput(
        content="I'm feeling a bit overwhelmed with work today and could use some encouragement.",
        input_type=InputType.TEXT,
        metadata={"test": True}
    )
    
    print(f"📝 Test Input: {test_input.content}")
    print()
    
    # Test LocalModelGenerator directly
    print("1. Testing LocalModelGenerator directly...")
    try:
        local_gen = LocalModelGenerator("tinyllama-1.1b-chat-gguf-q4")
        
        if local_gen.is_available():
            print(f"✅ {local_gen.get_generator_name()} is available")
            
            print("🔄 Generating content...")
            result = local_gen.generate_support_and_poem(test_input)
            
            print(f"💬 Supportive Statement:")
            print(f"   {result.supportive_statement}")
            print()
            print(f"📝 Poem:")
            print(f"   {result.poem}")
            print()
            print(f"⏱️  Processing time: {result.generation_metadata.get('processing_time', 0):.2f}s")
            
        else:
            print("❌ LocalModelGenerator is not available")
            
    except Exception as e:
        print(f"❌ LocalModelGenerator failed: {e}")
    
    print()
    
    # Test ContentGenerator with fallback chain
    print("2. Testing ContentGenerator with fallback chain...")
    try:
        content_gen = ContentGenerator()
        
        print(f"🔄 Using generator: {content_gen.current_generator.get_generator_name()}")
        
        result = content_gen.generate_support_and_poem(test_input)
        
        print(f"💬 Supportive Statement:")
        print(f"   {result.supportive_statement}")
        print()
        print(f"📝 Poem:")
        print(f"   {result.poem}")
        print()
        print(f"🏷️  Generator used: {result.generation_metadata.get('generator', 'unknown')}")
        print(f"⏱️  Processing time: {result.generation_metadata.get('processing_time', 0):.2f}s")
        
    except Exception as e:
        print(f"❌ ContentGenerator failed: {e}")

if __name__ == "__main__":
    test_local_model()