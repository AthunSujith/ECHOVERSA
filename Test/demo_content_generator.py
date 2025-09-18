"""
Demo script for content generation system.
Shows the content generator in action with different input types.
"""

import os
import sys

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from content_generator import ContentGenerator
from data_models import ProcessedInput, InputType


def demo_content_generation():
    """Demonstrate content generation with different input types."""
    print("=== EchoVerse Content Generation Demo ===\n")
    
    # Initialize content generator
    generator = ContentGenerator()
    print(f"Initialized content generator with: {generator.get_available_generators()}")
    print(f"Current generator: {generator.get_current_generator_name()}")
    print(f"Gemini available: {generator.is_gemini_available()}\n")
    
    # Demo inputs
    demo_inputs = [
        {
            "content": "I'm feeling overwhelmed with all the tasks I need to complete today.",
            "input_type": InputType.TEXT,
            "description": "Text Input - Feeling Overwhelmed"
        },
        {
            "content": "Transcribed audio: I just had a really good conversation with a friend and I'm feeling grateful.",
            "input_type": InputType.AUDIO,
            "description": "Audio Input - Feeling Grateful"
        },
        {
            "content": "A drawing of a person standing on a mountain peak, looking at the sunrise.",
            "input_type": InputType.DRAWING,
            "description": "Drawing Input - Mountain Sunrise"
        }
    ]
    
    for i, demo_input in enumerate(demo_inputs, 1):
        print(f"--- Demo {i}: {demo_input['description']} ---")
        print(f"Input: {demo_input['content'][:60]}...")
        
        # Create processed input
        processed_input = ProcessedInput(
            content=demo_input['content'],
            input_type=demo_input['input_type'],
            metadata={"demo": True, "index": i}
        )
        
        try:
            # Generate content
            result = generator.generate_support_and_poem(processed_input)
            
            print(f"\n✨ Supportive Statement:")
            print(f"   {result.supportive_statement}")
            
            print(f"\n🌟 Poem:")
            print(f"   {result.poem}")
            
            print(f"\n📊 Generation Metadata:")
            metadata = result.generation_metadata
            print(f"   Generator: {metadata.get('generator', 'unknown')}")
            print(f"   Processing Time: {metadata.get('processing_time', 0):.3f}s")
            print(f"   Input Type: {metadata.get('input_type', 'unknown')}")
            print(f"   Content Length: {metadata.get('content_length', 0)} chars")
            
        except Exception as e:
            print(f"❌ Error generating content: {e}")
        
        print("\n" + "="*60 + "\n")
    
    print("Demo completed! 🎉")


def demo_fallback_behavior():
    """Demonstrate fallback behavior when generators fail."""
    print("=== Fallback Behavior Demo ===\n")
    
    generator = ContentGenerator()
    
    # Test with a simple input
    test_input = ProcessedInput(
        content="This is a test of the fallback system.",
        input_type=InputType.TEXT
    )
    
    print("Testing fallback behavior...")
    print(f"Available generators: {generator.get_available_generators()}")
    
    try:
        result = generator.generate_support_and_poem(test_input)
        print(f"✅ Successfully generated content using: {result.generation_metadata['generator']}")
        print(f"Supportive statement: {result.supportive_statement[:50]}...")
        print(f"Poem: {result.poem[:50]}...")
    except Exception as e:
        print(f"❌ All generators failed: {e}")
    
    print("\nFallback demo completed! 🎉\n")


if __name__ == "__main__":
    try:
        demo_content_generation()
        demo_fallback_behavior()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()