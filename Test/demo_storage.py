"""
Demonstration script for the storage manager functionality.
Shows how to use the storage system for user management and interaction persistence.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.storage_manager import StorageManager, HistoryManager
from app.data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType
import tempfile
import shutil


def demo_storage_system():
    """Demonstrate the complete storage system functionality."""
    print("=== EchoVerse Storage System Demo ===\n")
    
    # Create temporary directory for demo
    demo_dir = tempfile.mkdtemp()
    print(f"Demo directory: {demo_dir}")
    
    try:
        # Initialize storage manager
        storage = StorageManager(demo_dir)
        print("✓ Storage manager initialized")
        
        # Create a demo user
        user = User(
            nickname="demo_user",
            password="demo_pass123",
            preferences={"theme": "dark", "auto_save": True}
        )
        
        # Save user profile and create directory
        storage.create_user_directory(user)
        storage.save_user_profile(user)
        print("✓ User profile created and saved")
        
        # Verify user exists
        if storage.user_exists("demo_user"):
            print("✓ User existence verified")
        
        # Create some demo interactions
        interactions_data = [
            {
                "content": "I'm feeling anxious about my upcoming presentation",
                "input_type": InputType.TEXT,
                "support": "You've got this! Presentations can feel overwhelming, but remember that you're prepared and capable.",
                "poem": "Breathe deep, stand tall,\nYour voice matters most of all.\nWith courage in your heart so true,\nSuccess will surely come to you."
            },
            {
                "content": "Had a great day at the park with my family",
                "input_type": InputType.TEXT,
                "support": "What a wonderful way to spend time! Family moments in nature are truly special and rejuvenating.",
                "poem": "Sunshine and laughter fill the air,\nFamily bonds beyond compare.\nIn nature's embrace, hearts unite,\nMemories made in golden light."
            },
            {
                "content": "Feeling creative today, want to draw something",
                "input_type": InputType.DRAWING,
                "support": "Creativity is such a beautiful expression of your inner self. Let your imagination flow freely!",
                "poem": "Colors dance upon the page,\nArt becomes your sacred stage.\nEvery stroke tells your story,\nCreation in all its glory."
            }
        ]
        
        saved_interactions = []
        
        for i, data in enumerate(interactions_data):
            # Create input data
            input_data = ProcessedInput(
                content=data["content"],
                input_type=data["input_type"],
                metadata={"demo": True, "session": i + 1}
            )
            
            # Add some fake raw data for the drawing
            if data["input_type"] == InputType.DRAWING:
                input_data.raw_data = b"fake PNG data for demo drawing"
            
            # Create generated content
            generated_content = GeneratedContent(
                supportive_statement=data["support"],
                poem=data["poem"],
                generation_metadata={"model": "demo", "processing_time": 0.5}
            )
            
            # Create interaction
            interaction = Interaction(
                input_data=input_data,
                generated_content=generated_content
            )
            
            # Save interaction
            interaction_id = storage.save_interaction(user, interaction)
            saved_interactions.append(interaction_id)
            print(f"✓ Saved interaction {i + 1}: {interaction_id[:8]}...")
        
        print(f"\n✓ Created {len(saved_interactions)} demo interactions")
        
        # Demonstrate loading functionality
        print("\n=== Loading and History Demo ===")
        
        # Load user profile
        loaded_user = storage.load_user_profile("demo_user")
        print(f"✓ Loaded user: {loaded_user.nickname}")
        print(f"  - Preferences: {loaded_user.preferences}")
        print(f"  - Total prompts: {len(loaded_user.prompts)}")
        
        # Load complete history
        history = storage.load_user_history(loaded_user)
        print(f"✓ Loaded {len(history)} interactions from history")
        
        # Demonstrate individual interaction loading
        first_interaction = storage.load_interaction("demo_user", saved_interactions[0])
        if first_interaction:
            print(f"✓ Loaded individual interaction:")
            print(f"  - Input: {first_interaction.input_data.content[:50]}...")
            print(f"  - Support: {first_interaction.generated_content.supportive_statement[:50]}...")
        
        # Demonstrate history manager
        print("\n=== History Manager Demo ===")
        history_manager = HistoryManager(storage)
        
        # Get recent interactions
        recent = history_manager.get_recent_interactions(loaded_user, limit=2)
        print(f"✓ Retrieved {len(recent)} recent interactions")
        
        # Search interactions
        search_results = history_manager.search_interactions(loaded_user, "family")
        print(f"✓ Found {len(search_results)} interactions containing 'family'")
        
        # Get interaction summary
        summary = history_manager.get_interaction_summary(loaded_user)
        print(f"✓ Interaction summary:")
        print(f"  - Total interactions: {summary['total_interactions']}")
        print(f"  - Input types: {summary['input_types']}")
        print(f"  - Average content length: {summary['avg_content_length']} characters")
        
        # Get storage statistics
        stats = storage.get_storage_stats("demo_user")
        print(f"✓ Storage statistics:")
        print(f"  - Total size: {stats['total_size']} bytes ({stats['total_size_mb']} MB)")
        print(f"  - File count: {stats['file_count']}")
        print(f"  - Interaction count: {stats['interaction_count']}")
        
        # Demonstrate deletion
        print("\n=== Deletion Demo ===")
        interaction_to_delete = saved_interactions[-1]
        if storage.delete_interaction("demo_user", interaction_to_delete):
            print(f"✓ Successfully deleted interaction {interaction_to_delete[:8]}...")
            
            # Verify deletion
            updated_history = storage.load_user_history(loaded_user)
            print(f"✓ History now contains {len(updated_history)} interactions")
        
        print("\n=== Demo Complete ===")
        print("✓ All storage system features demonstrated successfully!")
        
    except Exception as e:
        print(f"✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up demo directory
        if os.path.exists(demo_dir):
            shutil.rmtree(demo_dir)
            print(f"✓ Cleaned up demo directory")
    
    return True


if __name__ == "__main__":
    success = demo_storage_system()
    sys.exit(0 if success else 1)