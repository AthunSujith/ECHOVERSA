"""
Test script for history panel functionality.
Tests the integration between storage system and history display.
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.storage_manager import StorageManager, HistoryManager
from app.data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType


def create_test_user():
    """Create a test user with some interaction history."""
    user = User(
        nickname="testuser",
        password="testpass123",
        preferences={"theme": "light"},
        prompts=[]
    )
    return user


def create_test_interaction(content, input_type=InputType.TEXT):
    """Create a test interaction."""
    interaction = Interaction()
    
    # Add input data
    interaction.input_data = ProcessedInput(
        content=content,
        input_type=input_type,
        metadata={"test": True}
    )
    
    # Add generated content
    interaction.generated_content = GeneratedContent(
        supportive_statement=f"This is a supportive response to: {content}",
        poem=f"A poem about {content[:20]}...\nWith hope and light,\nEverything's alright.",
        generation_metadata={"model": "test", "timestamp": datetime.now().isoformat()}
    )
    
    return interaction


def test_history_functionality():
    """Test the history panel functionality."""
    print("Testing History Panel Functionality")
    print("=" * 50)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    print(f"Using test directory: {test_dir}")
    
    try:
        # Initialize storage manager
        storage = StorageManager(test_dir)
        history_manager = HistoryManager(storage)
        
        # Create test user
        user = create_test_user()
        print(f"Created test user: {user.nickname}")
        
        # Create user directory and save profile
        storage.create_user_directory(user)
        storage.save_user_profile(user)
        print("User profile saved")
        
        # Create some test interactions
        test_interactions = [
            ("Feeling anxious about work today", InputType.TEXT),
            ("Excited about my new project", InputType.TEXT),
            ("Reflecting on friendship and connections", InputType.TEXT),
        ]
        
        saved_interactions = []
        for content, input_type in test_interactions:
            interaction = create_test_interaction(content, input_type)
            interaction_id = storage.save_interaction(user, interaction)
            saved_interactions.append(interaction_id)
            print(f"Saved interaction: {interaction_id} - {content[:30]}...")
        
        # Test loading user history
        print("\nTesting history loading...")
        loaded_user = storage.load_user_profile(user.nickname)
        if loaded_user:
            print(f"Loaded user profile: {loaded_user.nickname}")
            print(f"User has {len(loaded_user.prompts)} prompts in history")
            
            # Load full interaction history
            interactions = storage.load_user_history(loaded_user)
            print(f"Loaded {len(interactions)} full interactions")
            
            # Test history manager functionality
            recent_interactions = history_manager.get_recent_interactions(loaded_user, limit=5)
            print(f"Recent interactions: {len(recent_interactions)}")
            
            # Test search functionality
            search_results = history_manager.search_interactions(loaded_user, "anxious")
            print(f"Search results for 'anxious': {len(search_results)}")
            
            # Test interaction summary
            summary = history_manager.get_interaction_summary(loaded_user)
            print(f"Interaction summary: {summary}")
            
            # Display interaction details
            print("\nInteraction Details:")
            for i, interaction in enumerate(interactions):
                print(f"  {i+1}. ID: {interaction.id}")
                print(f"     Input: {interaction.input_data.content[:50]}...")
                print(f"     Support: {interaction.generated_content.supportive_statement[:50]}...")
                print(f"     Poem: {interaction.generated_content.poem[:50]}...")
                print(f"     Timestamp: {interaction.timestamp}")
                print()
        
        print("✅ History functionality test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")


def test_history_preview_format():
    """Test the format expected by the history panel."""
    print("\nTesting History Preview Format")
    print("=" * 50)
    
    test_dir = tempfile.mkdtemp()
    
    try:
        storage = StorageManager(test_dir)
        user = create_test_user()
        
        # Create and save user
        storage.create_user_directory(user)
        storage.save_user_profile(user)
        
        # Create test interaction
        interaction = create_test_interaction("Testing preview format functionality")
        storage.save_interaction(user, interaction)
        
        # Load history and convert to preview format (simulating UI code)
        loaded_user = storage.load_user_profile(user.nickname)
        interactions = storage.load_user_history(loaded_user)
        
        # Convert to preview format like the UI does
        history_items = []
        for interaction in interactions:
            preview_text = "Untitled"
            if interaction.input_data and interaction.input_data.content:
                content = interaction.input_data.content.strip()
                preview_text = content[:50] + "..." if len(content) > 50 else content
            
            timestamp_str = interaction.timestamp.strftime("%Y-%m-%d %H:%M")
            
            history_item = {
                'id': interaction.id,
                'preview': preview_text,
                'timestamp': timestamp_str,
                'input_type': interaction.input_data.input_type.value if interaction.input_data else 'unknown',
                'supportive_statement': interaction.generated_content.supportive_statement if interaction.generated_content else '',
                'poem': interaction.generated_content.poem if interaction.generated_content else '',
                'interaction_obj': interaction
            }
            history_items.append(history_item)
        
        print(f"Generated {len(history_items)} history preview items")
        for item in history_items:
            print(f"  - {item['preview']} ({item['timestamp']}) [{item['input_type']}]")
        
        print("✅ History preview format test completed successfully!")
        
    except Exception as e:
        print(f"❌ Preview format test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_history_functionality()
    test_history_preview_format()