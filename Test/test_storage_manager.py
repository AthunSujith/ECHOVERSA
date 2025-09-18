"""
Unit tests for the storage manager and file management system.
Tests all storage operations, user directory management, and data persistence.
"""

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.storage_manager import StorageManager, FileManager, HistoryManager, StorageError
from app.data_models import (
    User, Interaction, ProcessedInput, GeneratedContent, AudioFile, InputType
)


class TestStorageManager(unittest.TestCase):
    """Test cases for StorageManager class."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(self.test_dir)
        
        # Create test user
        self.test_user = User(
            nickname="testuser",
            password="testpass123",
            preferences={"theme": "dark"},
            prompts=[]
        )
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test StorageManager initialization and directory creation."""
        # Check that directories were created
        self.assertTrue(self.storage.users_dir.exists())
        self.assertTrue(self.storage.outputs_dir.exists())
        
        # Test with custom base path
        custom_dir = tempfile.mkdtemp()
        try:
            custom_storage = StorageManager(custom_dir)
            self.assertEqual(custom_storage.base_path, Path(custom_dir))
            self.assertTrue((Path(custom_dir) / "users").exists())
            self.assertTrue((Path(custom_dir) / "outputs").exists())
        finally:
            shutil.rmtree(custom_dir)
    
    def test_user_exists(self):
        """Test user existence checking."""
        # User should not exist initially
        self.assertFalse(self.storage.user_exists("testuser"))
        
        # Create user profile
        self.storage.save_user_profile(self.test_user)
        
        # User should now exist
        self.assertTrue(self.storage.user_exists("testuser"))
    
    def test_create_user_directory(self):
        """Test user directory creation."""
        # Create user directory
        result = self.storage.create_user_directory(self.test_user)
        self.assertTrue(result)
        
        # Check directory exists
        user_dir = self.storage._get_user_directory("testuser")
        self.assertTrue(user_dir.exists())
        
        # Test with invalid user data - create user with invalid data manually
        with self.assertRaises(StorageError):
            # Create user object bypassing validation
            invalid_user = object.__new__(User)
            invalid_user.nickname = ""
            invalid_user.password = "test"
            invalid_user.created = datetime.now()
            invalid_user.preferences = {}
            invalid_user.prompts = []
            self.storage.create_user_directory(invalid_user)
    
    def test_save_and_load_user_profile(self):
        """Test saving and loading user profiles."""
        # Save user profile
        result = self.storage.save_user_profile(self.test_user)
        self.assertTrue(result)
        
        # Load user profile
        loaded_user = self.storage.load_user_profile("testuser")
        self.assertIsNotNone(loaded_user)
        self.assertEqual(loaded_user.nickname, self.test_user.nickname)
        self.assertEqual(loaded_user.password, self.test_user.password)
        self.assertEqual(loaded_user.preferences, self.test_user.preferences)
        
        # Test loading non-existent user
        non_existent = self.storage.load_user_profile("nonexistent")
        self.assertIsNone(non_existent)
        
        # Test with invalid user data - create user with invalid data manually
        with self.assertRaises(StorageError):
            # Create user object bypassing validation
            invalid_user = object.__new__(User)
            invalid_user.nickname = ""
            invalid_user.password = "test"
            invalid_user.created = datetime.now()
            invalid_user.preferences = {}
            invalid_user.prompts = []
            self.storage.save_user_profile(invalid_user)
    
    def test_save_and_load_interaction(self):
        """Test saving and loading complete interactions."""
        # Create test interaction
        input_data = ProcessedInput(
            content="Test input content",
            input_type=InputType.TEXT,
            metadata={"source": "test"}
        )
        
        generated_content = GeneratedContent(
            supportive_statement="You are doing great!",
            poem="Roses are red, violets are blue",
            generation_metadata={"model": "test"}
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content
        )
        
        # Save interaction
        interaction_id = self.storage.save_interaction(self.test_user, interaction)
        self.assertEqual(interaction_id, interaction.id)
        
        # Check files were created
        interaction_dir = self.storage._get_interaction_directory("testuser", interaction.id)
        self.assertTrue(interaction_dir.exists())
        self.assertTrue((interaction_dir / "support.txt").exists())
        self.assertTrue((interaction_dir / "poem.txt").exists())
        self.assertTrue((interaction_dir / "meta.json").exists())
        
        # Load interaction
        loaded_interaction = self.storage.load_interaction("testuser", interaction.id)
        self.assertIsNotNone(loaded_interaction)
        self.assertEqual(loaded_interaction.id, interaction.id)
        self.assertEqual(loaded_interaction.input_data.content, input_data.content)
        self.assertEqual(loaded_interaction.generated_content.supportive_statement, 
                        generated_content.supportive_statement)
        
        # Test loading non-existent interaction
        non_existent = self.storage.load_interaction("testuser", "nonexistent")
        self.assertIsNone(non_existent)
    
    def test_save_interaction_with_audio(self):
        """Test saving interactions with audio files."""
        # Create temporary audio file
        audio_file_path = Path(self.test_dir) / "temp_audio.wav"
        with open(audio_file_path, 'wb') as f:
            f.write(b"fake audio data")
        
        # Create interaction with audio
        input_data = ProcessedInput(
            content="Test with audio",
            input_type=InputType.AUDIO
        )
        
        generated_content = GeneratedContent(
            supportive_statement="Great audio input!",
            poem="Audio poem here"
        )
        
        audio_file = AudioFile(
            file_path=str(audio_file_path),
            metadata={"type": "support"}
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content,
            audio_files=[audio_file]
        )
        
        # Save interaction
        self.storage.save_interaction(self.test_user, interaction)
        
        # Check audio file was copied
        interaction_dir = self.storage._get_interaction_directory("testuser", interaction.id)
        copied_audio = interaction_dir / "support.wav"
        self.assertTrue(copied_audio.exists())
        
        # Load and verify
        loaded_interaction = self.storage.load_interaction("testuser", interaction.id)
        self.assertEqual(len(loaded_interaction.audio_files), 1)
    
    def test_save_interaction_with_raw_data(self):
        """Test saving interactions with raw input data."""
        # Create interaction with raw drawing data
        input_data = ProcessedInput(
            content="Drawing description",
            input_type=InputType.DRAWING,
            raw_data=b"fake PNG data"
        )
        
        generated_content = GeneratedContent(
            supportive_statement="Nice drawing!",
            poem="Art is beautiful"
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content
        )
        
        # Save interaction
        self.storage.save_interaction(self.test_user, interaction)
        
        # Check raw data file was created
        interaction_dir = self.storage._get_interaction_directory("testuser", interaction.id)
        sketch_file = interaction_dir / "sketch.png"
        self.assertTrue(sketch_file.exists())
        
        # Load and verify raw data
        loaded_interaction = self.storage.load_interaction("testuser", interaction.id)
        self.assertEqual(loaded_interaction.input_data.raw_data, b"fake PNG data")
    
    def test_load_user_history(self):
        """Test loading complete user interaction history."""
        # Create multiple interactions
        interactions = []
        for i in range(3):
            input_data = ProcessedInput(
                content=f"Test input {i}",
                input_type=InputType.TEXT
            )
            
            generated_content = GeneratedContent(
                supportive_statement=f"Support {i}",
                poem=f"Poem {i}"
            )
            
            interaction = Interaction(
                input_data=input_data,
                generated_content=generated_content
            )
            interactions.append(interaction)
            
            # Save each interaction
            self.storage.save_interaction(self.test_user, interaction)
        
        # Load history
        history = self.storage.load_user_history(self.test_user)
        self.assertEqual(len(history), 3)
        
        # Check ordering (newest first)
        self.assertTrue(history[0].timestamp >= history[1].timestamp)
        self.assertTrue(history[1].timestamp >= history[2].timestamp)
    
    def test_delete_interaction(self):
        """Test deleting interactions and associated files."""
        # Create and save interaction
        input_data = ProcessedInput(
            content="Test for deletion",
            input_type=InputType.TEXT
        )
        
        generated_content = GeneratedContent(
            supportive_statement="To be deleted",
            poem="Gone soon"
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content
        )
        
        interaction_id = self.storage.save_interaction(self.test_user, interaction)
        
        # Verify interaction exists
        interaction_dir = self.storage._get_interaction_directory("testuser", interaction_id)
        self.assertTrue(interaction_dir.exists())
        
        # Delete interaction
        result = self.storage.delete_interaction("testuser", interaction_id)
        self.assertTrue(result)
        
        # Verify interaction directory is gone
        self.assertFalse(interaction_dir.exists())
        
        # Verify interaction is removed from user's prompt history
        updated_user = self.storage.load_user_profile("testuser")
        interaction_ids = [p.get("id") for p in updated_user.prompts]
        self.assertNotIn(interaction_id, interaction_ids)
    
    def test_get_storage_stats(self):
        """Test storage statistics calculation."""
        # Get stats for non-existent user
        stats = self.storage.get_storage_stats("nonexistent")
        self.assertEqual(stats["total_size"], 0)
        self.assertEqual(stats["interaction_count"], 0)
        
        # Create user and interaction
        self.storage.create_user_directory(self.test_user)
        
        input_data = ProcessedInput(
            content="Stats test",
            input_type=InputType.TEXT
        )
        
        generated_content = GeneratedContent(
            supportive_statement="Stats support",
            poem="Stats poem"
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content
        )
        
        self.storage.save_interaction(self.test_user, interaction)
        
        # Get stats
        stats = self.storage.get_storage_stats("testuser")
        self.assertGreater(stats["total_size"], 0)
        self.assertEqual(stats["interaction_count"], 1)
        self.assertGreater(stats["file_count"], 0)
        # Note: total_size_mb might be 0 for very small files, so we check total_size instead
        self.assertGreaterEqual(stats["total_size_mb"], 0)
    
    def test_error_handling(self):
        """Test error handling in storage operations."""
        # Test with invalid base path
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with self.assertRaises(StorageError):
                StorageManager("/invalid/path")
        
        # Test file operation errors
        with patch('builtins.open', side_effect=IOError("File error")):
            with self.assertRaises(StorageError):
                self.storage.save_user_profile(self.test_user)


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager utility class."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_ensure_directory(self):
        """Test directory creation utility."""
        test_path = Path(self.test_dir) / "new" / "nested" / "directory"
        
        # Directory should not exist initially
        self.assertFalse(test_path.exists())
        
        # Create directory
        result = FileManager.ensure_directory(test_path)
        self.assertTrue(result)
        self.assertTrue(test_path.exists())
        
        # Test with existing directory
        result = FileManager.ensure_directory(test_path)
        self.assertTrue(result)
    
    def test_safe_filename(self):
        """Test filename sanitization."""
        # Test normal filename
        safe = FileManager.safe_filename("normal_file.txt")
        self.assertEqual(safe, "normal_file.txt")
        
        # Test filename with problematic characters
        unsafe = "file<>:\"|?*.txt"
        safe = FileManager.safe_filename(unsafe)
        self.assertNotIn("<", safe)
        self.assertNotIn(">", safe)
        self.assertNotIn(":", safe)
        self.assertNotIn("|", safe)
        
        # Test empty filename
        safe = FileManager.safe_filename("")
        self.assertTrue(safe.startswith("file_"))
        
        # Test filename starting with dot
        safe = FileManager.safe_filename(".hidden")
        self.assertTrue(safe.startswith("file_"))
        
        # Test very long filename
        long_name = "a" * 300
        safe = FileManager.safe_filename(long_name)
        self.assertLessEqual(len(safe), 255)
    
    def test_get_file_size(self):
        """Test file size calculation."""
        # Test non-existent file
        non_existent = Path(self.test_dir) / "nonexistent.txt"
        size = FileManager.get_file_size(non_existent)
        self.assertEqual(size, 0)
        
        # Test existing file
        test_file = Path(self.test_dir) / "test.txt"
        test_content = "Hello, World!"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        size = FileManager.get_file_size(test_file)
        self.assertEqual(size, len(test_content.encode('utf-8')))
    
    def test_copy_file_safe(self):
        """Test safe file copying."""
        # Create source file
        src_file = Path(self.test_dir) / "source.txt"
        with open(src_file, 'w') as f:
            f.write("Test content")
        
        # Test successful copy
        dest_file = Path(self.test_dir) / "nested" / "destination.txt"
        result = FileManager.copy_file_safe(src_file, dest_file)
        self.assertTrue(result)
        self.assertTrue(dest_file.exists())
        
        # Verify content
        with open(dest_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Test content")
        
        # Test copy of non-existent file
        non_existent = Path(self.test_dir) / "nonexistent.txt"
        result = FileManager.copy_file_safe(non_existent, dest_file)
        self.assertFalse(result)


class TestHistoryManager(unittest.TestCase):
    """Test cases for HistoryManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(self.test_dir)
        self.history_manager = HistoryManager(self.storage)
        
        # Create test user
        self.test_user = User(
            nickname="historyuser",
            password="testpass123"
        )
        
        # Create test interactions
        self.interactions = []
        for i in range(5):
            input_data = ProcessedInput(
                content=f"Test input {i} with keyword search",
                input_type=InputType.TEXT
            )
            
            generated_content = GeneratedContent(
                supportive_statement=f"Support statement {i}",
                poem=f"Poem number {i}"
            )
            
            interaction = Interaction(
                input_data=input_data,
                generated_content=generated_content
            )
            self.interactions.append(interaction)
            
            # Save interaction
            self.storage.save_interaction(self.test_user, interaction)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_get_recent_interactions(self):
        """Test getting recent interactions with limit."""
        # Get recent interactions with default limit
        recent = self.history_manager.get_recent_interactions(self.test_user)
        self.assertLessEqual(len(recent), 10)
        self.assertEqual(len(recent), 5)  # We created 5 interactions
        
        # Test with custom limit
        recent_limited = self.history_manager.get_recent_interactions(self.test_user, limit=3)
        self.assertEqual(len(recent_limited), 3)
        
        # Verify ordering (newest first)
        for i in range(len(recent_limited) - 1):
            self.assertGreaterEqual(recent_limited[i].timestamp, recent_limited[i + 1].timestamp)
    
    def test_search_interactions(self):
        """Test searching interactions by content."""
        # Search for keyword that should match all interactions
        results = self.history_manager.search_interactions(self.test_user, "keyword")
        self.assertEqual(len(results), 5)
        
        # Search for specific number
        results = self.history_manager.search_interactions(self.test_user, "input 2")
        self.assertEqual(len(results), 1)
        self.assertIn("input 2", results[0].input_data.content)
        
        # Search in generated content
        results = self.history_manager.search_interactions(self.test_user, "Support statement")
        self.assertEqual(len(results), 5)
        
        # Search for non-existent content
        results = self.history_manager.search_interactions(self.test_user, "nonexistent")
        self.assertEqual(len(results), 0)
        
        # Case-insensitive search
        results = self.history_manager.search_interactions(self.test_user, "KEYWORD")
        self.assertEqual(len(results), 5)
    
    def test_get_interaction_summary(self):
        """Test getting interaction summary statistics."""
        summary = self.history_manager.get_interaction_summary(self.test_user)
        
        self.assertEqual(summary["total_interactions"], 5)
        self.assertEqual(summary["input_types"]["text"], 5)
        self.assertIsNotNone(summary["date_range"])
        self.assertIn("earliest", summary["date_range"])
        self.assertIn("latest", summary["date_range"])
        self.assertGreater(summary["avg_content_length"], 0)
        
        # Test with user who has no interactions
        empty_user = User(nickname="emptyuser", password="test")
        empty_summary = self.history_manager.get_interaction_summary(empty_user)
        
        self.assertEqual(empty_summary["total_interactions"], 0)
        self.assertEqual(empty_summary["input_types"], {})
        self.assertIsNone(empty_summary["date_range"])
        self.assertEqual(empty_summary["avg_content_length"], 0)


class TestStorageIntegration(unittest.TestCase):
    """Integration tests for complete storage workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from registration to interaction history."""
        # Create user
        user = User(
            nickname="integrationuser",
            password="securepass123",
            preferences={"theme": "light", "auto_save": True}
        )
        
        # Save user profile and create directory
        self.storage.create_user_directory(user)
        self.storage.save_user_profile(user)
        
        # Verify user exists
        self.assertTrue(self.storage.user_exists("integrationuser"))
        
        # Create multiple interactions with different input types
        input_types = [InputType.TEXT, InputType.AUDIO, InputType.DRAWING]
        
        for i, input_type in enumerate(input_types):
            input_data = ProcessedInput(
                content=f"Integration test {i}",
                input_type=input_type,
                metadata={"test": True}
            )
            
            if input_type == InputType.DRAWING:
                input_data.raw_data = b"fake image data"
            
            generated_content = GeneratedContent(
                supportive_statement=f"Integration support {i}",
                poem=f"Integration poem {i}",
                generation_metadata={"model": "test", "version": "1.0"}
            )
            
            interaction = Interaction(
                input_data=input_data,
                generated_content=generated_content
            )
            
            # Save interaction
            self.storage.save_interaction(user, interaction)
        
        # Load complete history
        history = self.storage.load_user_history(user)
        self.assertEqual(len(history), 3)
        
        # Verify different input types
        loaded_input_types = {h.input_data.input_type for h in history}
        self.assertEqual(loaded_input_types, set(input_types))
        
        # Test history manager
        history_manager = HistoryManager(self.storage)
        summary = history_manager.get_interaction_summary(user)
        
        self.assertEqual(summary["total_interactions"], 3)
        self.assertEqual(len(summary["input_types"]), 3)
        
        # Test storage stats
        stats = self.storage.get_storage_stats("integrationuser")
        self.assertGreater(stats["total_size"], 0)
        self.assertEqual(stats["interaction_count"], 3)
        
        # Test search functionality
        search_results = history_manager.search_interactions(user, "Integration")
        self.assertEqual(len(search_results), 3)
    
    def test_data_persistence_across_sessions(self):
        """Test that data persists across different storage manager instances."""
        # Create user and interaction with first storage instance
        user = User(nickname="persistuser", password="testpass")
        
        input_data = ProcessedInput(
            content="Persistence test",
            input_type=InputType.TEXT
        )
        
        generated_content = GeneratedContent(
            supportive_statement="Persistent support",
            poem="Persistent poem"
        )
        
        interaction = Interaction(
            input_data=input_data,
            generated_content=generated_content
        )
        
        # Save with first instance
        self.storage.create_user_directory(user)
        self.storage.save_user_profile(user)
        interaction_id = self.storage.save_interaction(user, interaction)
        
        # Create new storage instance (simulating app restart)
        new_storage = StorageManager(self.test_dir)
        
        # Verify data persists
        self.assertTrue(new_storage.user_exists("persistuser"))
        
        loaded_user = new_storage.load_user_profile("persistuser")
        self.assertIsNotNone(loaded_user)
        self.assertEqual(loaded_user.nickname, "persistuser")
        
        loaded_interaction = new_storage.load_interaction("persistuser", interaction_id)
        self.assertIsNotNone(loaded_interaction)
        self.assertEqual(loaded_interaction.input_data.content, "Persistence test")
        
        # Test history loading
        history = new_storage.load_user_history(loaded_user)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].id, interaction_id)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)