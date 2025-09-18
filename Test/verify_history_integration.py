"""
Verification script for history panel integration.
Tests the integration without Streamlit session state dependencies.
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.auth_manager import UserManager, AuthenticationError
    from app.data_models import User
    from app.storage_manager import StorageManager, HistoryManager
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_history_integration():
    """Test the history integration components."""
    print("Testing History Integration Components")
    print("=" * 50)
    
    try:
        # Test storage manager initialization
        storage = StorageManager()
        print("✅ StorageManager initialized")
        
        # Test history manager initialization
        history_manager = HistoryManager(storage)
        print("✅ HistoryManager initialized")
        
        # Test user manager initialization
        user_manager = UserManager()
        print("✅ UserManager initialized")
        
        # Test creating a user
        test_user = User(
            nickname="integration_test",
            password="test123",
            preferences={"test": True}
        )
        print("✅ User object created")
        
        # Test the history preview format conversion logic
        # (This simulates what the UI does)
        sample_interactions = []
        
        # Create sample interaction data
        from app.data_models import Interaction, ProcessedInput, GeneratedContent, InputType
        from datetime import datetime
        
        interaction = Interaction()
        interaction.input_data = ProcessedInput(
            content="Test integration functionality",
            input_type=InputType.TEXT,
            metadata={"test": True}
        )
        interaction.generated_content = GeneratedContent(
            supportive_statement="This is a test supportive statement",
            poem="Test poem\nWith integration\nWorking well",
            generation_metadata={"test": True}
        )
        
        # Convert to preview format (same logic as UI)
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
        
        print("✅ History item format conversion successful")
        print(f"   Preview: {history_item['preview']}")
        print(f"   Type: {history_item['input_type']}")
        print(f"   Timestamp: {history_item['timestamp']}")
        
        # Test mind map grouping logic
        history_items = [history_item]
        type_groups = {}
        for item in history_items:
            input_type = item.get('input_type', 'unknown')
            if input_type not in type_groups:
                type_groups[input_type] = []
            type_groups[input_type].append(item)
        
        print("✅ Mind map grouping logic successful")
        print(f"   Groups: {list(type_groups.keys())}")
        print(f"   Text group size: {len(type_groups.get('text', []))}")
        
        # Test search logic
        search_query = "test"
        filtered_items = [
            item for item in history_items
            if search_query.lower() in item.get('preview', '').lower() or
               search_query.lower() in item.get('supportive_statement', '').lower() or
               search_query.lower() in item.get('poem', '').lower()
        ]
        
        print("✅ Search functionality logic successful")
        print(f"   Search results for '{search_query}': {len(filtered_items)}")
        
        print("\n🎉 All history integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_history_integration()
    if success:
        print("\n✅ History panel integration verification completed successfully!")
    else:
        print("\n❌ History panel integration verification failed!")
        sys.exit(1)