#!/usr/bin/env python3
"""
Test script for enhanced session management functionality.
Tests automatic saving, session restoration, history caching, and data migration.
"""

import sys
import os
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
import uuid

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType
    from storage_manager import StorageManager
    from session_manager import SessionManager
    from auth_manager import UserManager
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)


class TestEnhancedSessionManagement:
    """Test class for enhanced session management functionality."""
    
    def __init__(self):
        """Initialize test environment."""
        self.temp_dir = None
        self.storage_manager = None
        self.session_manager = None
        self.user_manager = None
        self.test_user = None
        
    def setup_test_environment(self):
        """Set up temporary test environment."""
        print("Setting up test environment...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="echoverse_session_test_")
        print(f"Test directory: {self.temp_dir}")
        
        # Initialize managers
        self.storage_manager = StorageManager(self.temp_dir)
        self.session_manager = SessionManager(self.storage_manager, self.temp_dir)
        self.user_manager = UserManager(self.storage_manager)
        
        # Create test user
        success, message = self.user_manager.register_user("testuser", "testpass")
        if success:
            session_token, _ = self.user_manager.login_user("testuser", "testpass")
            self.test_user = self.user_manager.get_current_user(session_token)
            print(f"Test user created: {self.test_user.nickname}")
        else:
            raise Exception(f"Failed to create test user: {message}")
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up test directory: {self.temp_dir}")
    
    def create_test_interaction(self, content: str = "Test interaction") -> Interaction:
        """Create a test interaction."""
        processed_input = ProcessedInput(
            content=content,
            input_type=InputType.TEXT,
            metadata={"test": True}
        )
        
        generated_content = GeneratedContent(
            supportive_statement=f"Supportive response for: {content}",
            poem=f"A poem about: {content}",
            generation_metadata={"generator": "test"}
        )
        
        interaction = Interaction(
            input_data=processed_input,
            generated_content=generated_content
        )
        
        return interaction
    
    def test_automatic_saving(self):
        """Test automatic saving of completed interactions."""
        print("\n=== Testing Automatic Saving ===")
        
        # Start session
        session_token = self.session_manager.start_session(self.test_user)
        print(f"Started session: {session_token[:8]}...")
        
        # Create and save interactions
        interactions = []
        for i in range(3):
            interaction = self.create_test_interaction(f"Test content {i+1}")
            
            # Test automatic saving
            success = self.session_manager.save_interaction_to_session(interaction)
            assert success, f"Failed to automatically save interaction {i+1}"
            
            interactions.append(interaction)
            print(f"Automatically saved interaction {i+1}: {interaction.id[:8]}...")
        
        # Verify interactions are in session cache
        session_cache = self.session_manager.session_data.get("interaction_cache", [])
        assert len(session_cache) == 3, f"Expected 3 interactions in cache, got {len(session_cache)}"
        
        print("✅ Automatic saving test passed")
        return interactions
    
    def test_session_restoration(self):
        """Test session restoration on application restart."""
        print("\n=== Testing Session Restoration ===")
        
        # Create interactions and end session
        interactions = self.test_automatic_saving()
        old_session_token = self.session_manager.current_session_id
        self.session_manager.end_session()
        
        # Create new session manager (simulating app restart)
        new_session_manager = SessionManager(self.storage_manager, self.temp_dir)
        
        # Restore session
        restored_data = new_session_manager.restore_session_on_startup(self.test_user, old_session_token)
        
        assert restored_data, "Failed to restore session data"
        assert "workspace_state" in restored_data, "Workspace state not restored"
        
        restored_count = restored_data.get("restored_interactions", 0)
        assert restored_count > 0, f"Expected restored interactions, got {restored_count}"
        
        print(f"✅ Session restoration test passed - restored {restored_count} interactions")
        
        # Update session manager for further tests
        self.session_manager = new_session_manager
        self.session_manager.start_session(self.test_user, old_session_token)
    
    def test_history_caching(self):
        """Test history loading and caching for performance."""
        print("\n=== Testing History Caching ===")
        
        # Test cached history retrieval
        cached_history = self.session_manager.get_cached_history(self.test_user)
        assert isinstance(cached_history, list), "Cached history should be a list"
        
        print(f"Retrieved {len(cached_history)} items from cache")
        
        # Test cache with limit
        limited_history = self.session_manager.get_cached_history(self.test_user, limit=2)
        assert len(limited_history) <= 2, f"Expected max 2 items, got {len(limited_history)}"
        
        # Test preloading
        preload_success = self.session_manager.preload_history_cache(self.test_user, background=False)
        assert preload_success, "Failed to preload history cache"
        
        # Test history statistics
        stats = self.session_manager.get_history_statistics(self.test_user)
        assert "total_interactions" in stats, "Statistics should include total_interactions"
        assert stats["total_interactions"] > 0, "Should have interactions in statistics"
        
        print(f"✅ History caching test passed - {stats['total_interactions']} total interactions")
    
    def test_data_migration(self):
        """Test data migration and backup functionality."""
        print("\n=== Testing Data Migration ===")
        
        # Create backup
        backup_success = self.session_manager.create_data_backup(self.test_user, "test")
        assert backup_success, "Failed to create data backup"
        
        # Find the backup file
        backup_dir = Path(self.temp_dir) / ".kiro" / "backups"
        backup_files = list(backup_dir.glob(f"{self.test_user.nickname}_backup_test_*.json"))
        assert len(backup_files) > 0, "No backup files found"
        
        backup_file = backup_files[0]
        print(f"Created backup: {backup_file.name}")
        
        # Verify backup content
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        assert "backup_timestamp" in backup_data, "Backup should have timestamp"
        assert "user_profile" in backup_data, "Backup should have user profile"
        assert "interactions" in backup_data, "Backup should have interactions"
        
        # Test migration (create new user and migrate data)
        success, _ = self.user_manager.register_user("migrated_user", "testpass")
        assert success, "Failed to create migration target user"
        
        session_token, _ = self.user_manager.login_user("migrated_user", "testpass")
        migrated_user = self.user_manager.get_current_user(session_token)
        
        # Perform migration
        migration_success = self.session_manager.migrate_user_data(str(backup_file), migrated_user)
        assert migration_success, "Failed to migrate user data"
        
        # Verify migrated data
        migrated_history = self.storage_manager.load_user_history(migrated_user)
        assert len(migrated_history) > 0, "Migrated user should have interaction history"
        
        print(f"✅ Data migration test passed - migrated {len(migrated_history)} interactions")
    
    def test_storage_availability_check(self):
        """Test storage availability checking."""
        print("\n=== Testing Storage Availability ===")
        
        # Test normal storage availability
        is_available, error_msg = self.session_manager.check_storage_availability()
        assert is_available, f"Storage should be available: {error_msg}"
        
        print("✅ Storage availability test passed")
    
    def test_session_persistence_on_shutdown(self):
        """Test session persistence during shutdown."""
        print("\n=== Testing Session Persistence on Shutdown ===")
        
        # Add some workspace state
        workspace_updates = {
            "current_view": "workspace",
            "selected_interaction": "test_id",
            "user_preferences": {"theme": "dark"}
        }
        
        update_success = self.session_manager.update_workspace_state(workspace_updates)
        assert update_success, "Failed to update workspace state"
        
        # Test shutdown persistence
        shutdown_success = self.session_manager.persist_session_on_shutdown()
        assert shutdown_success, "Failed to persist session on shutdown"
        
        print("✅ Session persistence on shutdown test passed")
    
    def test_cleanup_functionality(self):
        """Test cleanup of expired sessions and backups."""
        print("\n=== Testing Cleanup Functionality ===")
        
        # Test session cleanup (should not clean recent sessions)
        cleaned_count = self.session_manager.cleanup_expired_sessions(max_age_days=1)
        print(f"Cleaned up {cleaned_count} expired sessions")
        
        print("✅ Cleanup functionality test passed")
    
    def run_all_tests(self):
        """Run all session management tests."""
        print("🚀 Starting Enhanced Session Management Tests")
        print("=" * 60)
        
        try:
            self.setup_test_environment()
            
            # Run tests in order
            self.test_automatic_saving()
            self.test_session_restoration()
            self.test_history_caching()
            self.test_data_migration()
            self.test_storage_availability_check()
            self.test_session_persistence_on_shutdown()
            self.test_cleanup_functionality()
            
            print("\n" + "=" * 60)
            print("🎉 All Enhanced Session Management Tests Passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup_test_environment()
        
        return True


def main():
    """Main test function."""
    tester = TestEnhancedSessionManagement()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Enhanced session management implementation is working correctly!")
        return 0
    else:
        print("\n❌ Enhanced session management tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())