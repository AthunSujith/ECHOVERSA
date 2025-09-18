"""
Demo script to showcase the history panel and mind map functionality.
Creates sample data and demonstrates the visualization features.
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.storage_manager import StorageManager, HistoryManager
from app.data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType


def create_demo_user():
    """Create a demo user."""
    user = User(
        nickname="demo_user",
        password="demo123",
        preferences={"theme": "light", "voice": "default"},
        prompts=[]
    )
    return user


def create_demo_interactions():
    """Create a variety of demo interactions."""
    interactions_data = [
        # Text interactions
        ("Feeling overwhelmed with work deadlines", InputType.TEXT, 
         "It's completely natural to feel overwhelmed when facing multiple deadlines. Remember to break tasks into smaller, manageable pieces and take breaks when needed.",
         "Deadlines loom like mountains high,\nBut step by step, you'll reach the sky.\nOne task at a time, one breath, one day,\nYou'll find your strength to pave the way."),
        
        ("Excited about learning a new skill", InputType.TEXT,
         "Your enthusiasm for learning is wonderful! This curiosity and drive will open new doors and bring fresh perspectives to your life.",
         "New skills like seeds in fertile ground,\nWith practice, growth will soon be found.\nEach lesson learned, each challenge met,\nBuilds wisdom that you won't forget."),
        
        ("Worried about an upcoming presentation", InputType.TEXT,
         "Presentation nerves are completely normal and show that you care about doing well. Your preparation and passion will shine through.",
         "Before the crowd, your heart may race,\nBut knowledge gives you strength and grace.\nSpeak your truth with confidence clear,\nYour message is what they need to hear."),
        
        # Audio interactions (simulated)
        ("Shared feelings about family relationships", InputType.AUDIO,
         "Family relationships can be complex, but the love and care you show demonstrates your commitment to maintaining these important bonds.",
         "Family ties like golden thread,\nThrough joy and tears, through words unsaid.\nLove endures through thick and thin,\nThe heart knows where it all begins."),
        
        ("Recorded thoughts about career goals", InputType.AUDIO,
         "Having clear career goals shows your ambition and self-awareness. Trust in your abilities and take steps toward your dreams.",
         "Dreams of work that feeds the soul,\nCareer paths leading to your goal.\nWith vision clear and purpose true,\nSuccess will surely come to you."),
        
        # Drawing interactions (simulated)
        ("Drew a picture of my happy place", InputType.DRAWING,
         "Creating art of your happy place is a beautiful way to connect with what brings you peace and joy. Hold onto that feeling.",
         "Colors bright on canvas white,\nYour happy place, a pure delight.\nIn every stroke, in every hue,\nLies peace and joy that lives in you."),
        
        ("Sketched my feelings about change", InputType.DRAWING,
         "Using art to express feelings about change shows great emotional intelligence. Change can be challenging, but it also brings growth.",
         "Lines and shapes on paper dance,\nChange brings fear, but also chance.\nIn every curve, in every line,\nNew possibilities align."),
    ]
    
    interactions = []
    base_time = datetime.now() - timedelta(days=7)
    
    for i, (content, input_type, support, poem) in enumerate(interactions_data):
        interaction = Interaction()
        interaction.timestamp = base_time + timedelta(days=i, hours=i*2)
        
        # Add input data
        interaction.input_data = ProcessedInput(
            content=content,
            input_type=input_type,
            metadata={"demo": True, "session": f"demo_session_{i}"}
        )
        
        # Add generated content
        interaction.generated_content = GeneratedContent(
            supportive_statement=support,
            poem=poem,
            generation_metadata={
                "model": "demo_generator",
                "timestamp": interaction.timestamp.isoformat(),
                "processing_time": 1.5 + (i * 0.2)
            }
        )
        
        interactions.append(interaction)
    
    return interactions


def demonstrate_mind_map_logic(history_items):
    """Demonstrate the mind map visualization logic."""
    print("\n🗺️ Mind Map Visualization Demo")
    print("=" * 50)
    
    # Group interactions by input type (same logic as in UI)
    type_groups = {}
    for item in history_items:
        input_type = item.get('input_type', 'unknown')
        if input_type not in type_groups:
            type_groups[input_type] = []
        type_groups[input_type].append(item)
    
    # Create mind map structure
    mindmap_text = "**Your Interaction Journey:**\n\n"
    
    type_icons = {
        'text': '📝 Text Conversations',
        'audio': '🎤 Audio Messages', 
        'drawing': '🎨 Creative Drawings',
        'unknown': '💭 Other Interactions'
    }
    
    for input_type, items in type_groups.items():
        mindmap_text += f"**{type_icons.get(input_type, f'📋 {input_type.title()}')}** ({len(items)} interactions)\n"
        
        # Show recent items in this category
        recent_items = items[:3]  # Show up to 3 recent items per type
        for item in recent_items:
            preview = item.get('preview', 'Untitled')[:30] + "..." if len(item.get('preview', '')) > 30 else item.get('preview', 'Untitled')
            timestamp = item.get('timestamp', 'Unknown')
            mindmap_text += f"  └─ *{preview}* ({timestamp})\n"
        
        if len(items) > 3:
            mindmap_text += f"  └─ ... and {len(items) - 3} more\n"
        
        mindmap_text += "\n"
    
    print(mindmap_text)
    
    # Add summary statistics
    total_interactions = len(history_items)
    if total_interactions > 0:
        # Calculate some basic stats
        recent_date = max(item.get('timestamp', '') for item in history_items)
        oldest_date = min(item.get('timestamp', '') for item in history_items)
        
        print("**📊 Summary:**")
        print(f"- Total interactions: {total_interactions}")
        print(f"- Most recent: {recent_date}")
        print(f"- First interaction: {oldest_date}")
        
        # Show distribution by type
        type_counts = {}
        for item in history_items:
            input_type = item.get('input_type', 'unknown')
            type_counts[input_type] = type_counts.get(input_type, 0) + 1
        
        print("- Input type distribution:")
        for input_type, count in type_counts.items():
            percentage = (count / total_interactions) * 100
            print(f"  - {input_type.title()}: {count} ({percentage:.1f}%)")


def run_demo():
    """Run the complete history panel demo."""
    print("🎵 EchoVerse History Panel Demo")
    print("=" * 50)
    
    # Create temporary directory for demo
    test_dir = tempfile.mkdtemp()
    print(f"Demo directory: {test_dir}")
    
    try:
        # Initialize storage
        storage = StorageManager(test_dir)
        history_manager = HistoryManager(storage)
        
        # Create demo user
        user = create_demo_user()
        storage.create_user_directory(user)
        storage.save_user_profile(user)
        print(f"Created demo user: {user.nickname}")
        
        # Create and save demo interactions
        demo_interactions = create_demo_interactions()
        print(f"\nCreating {len(demo_interactions)} demo interactions...")
        
        for i, interaction in enumerate(demo_interactions):
            interaction_id = storage.save_interaction(user, interaction)
            print(f"  {i+1}. {interaction.input_data.content[:40]}... [{interaction.input_data.input_type.value}]")
        
        # Load history and convert to preview format
        loaded_user = storage.load_user_profile(user.nickname)
        interactions = storage.load_user_history(loaded_user)
        
        # Convert to UI preview format
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
        
        print(f"\n📚 Loaded {len(history_items)} history items")
        
        # Demonstrate search functionality
        print("\n🔍 Search Functionality Demo")
        search_queries = ["work", "excited", "family", "drawing"]
        
        for query in search_queries:
            results = [
                item for item in history_items
                if query.lower() in item.get('preview', '').lower() or
                   query.lower() in item.get('supportive_statement', '').lower() or
                   query.lower() in item.get('poem', '').lower()
            ]
            print(f"  Search '{query}': {len(results)} results")
        
        # Demonstrate mind map visualization
        demonstrate_mind_map_logic(history_items)
        
        # Show detailed interaction example
        print("\n📝 Sample Interaction Detail")
        print("=" * 50)
        if history_items:
            sample = history_items[0]
            print(f"ID: {sample['id']}")
            print(f"Timestamp: {sample['timestamp']}")
            print(f"Input Type: {sample['input_type']}")
            print(f"Preview: {sample['preview']}")
            print(f"Supportive Statement: {sample['supportive_statement']}")
            print(f"Poem:\n{sample['poem']}")
        
        print("\n✅ History panel demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"\nCleaned up demo directory: {test_dir}")


if __name__ == "__main__":
    run_demo()