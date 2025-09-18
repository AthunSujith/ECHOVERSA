"""
Unit tests for the authentication system.
Tests user registration, login, password validation, and session management.
"""

import unittest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import json

# Import the modules to test
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.auth_manager import (
    UserManager, SessionManager, PasswordManager, 
    AuthenticationError
)
from app.data_models import User
from app.storage_manager import StorageManager


class TestPasswordManager(unittest.TestCase):
    """Test password hashing and validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.password_manager = PasswordManager()
    
    def test_hash_password(self):
        """Test password hashing functionality."""
        password = "test_password_123"
        
        # Test hashing with auto-generated salt
        hashed1, salt1 = self.password_manager.hash_password(password)
        self.assertIsInstance(hashed1, str)
        self.assertIsInstance(salt1, str)
        self.assertNotEqual(hashed1, password)
        self.assertTrue(len(hashed1) > 0)
        self.assertTrue(len(salt1) > 0)
        
        # Test hashing with provided salt
        custom_salt = "custom_salt_123"
        hashed2, salt2 = self.password_manager.hash_password(password, custom_salt)
        self.assertEqual(salt2, custom_salt)
        self.assertNotEqual(hashed2, hashed1)  # Different salt should produce different hash
    
    def test_verify_password(self):
        """Test password verification."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        
        hashed, salt = self.password_manager.hash_password(password)
        
        # Test correct password
        self.assertTrue(self.password_manager.verify_password(password, hashed, salt))
        
        # Test wrong password
        self.assertFalse(self.password_manager.verify_password(wrong_password, hashed, salt))
        
        # Test with wrong salt
        wrong_salt = "wrong_salt"
        self.assertFalse(self.password_manager.verify_password(password, hashed, wrong_salt))
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Test strong password
        self.assertEqual([], self.password_manager.validate_password_strength("ValidPass123"))
        
        # Test too short password
        issues = self.password_manager.validate_password_strength("123")
        self.assertTrue(any("must be" in issue for issue in issues))
        
        # Test too long password
        long_password = "a" * 200
        issues = self.password_manager.validate_password_strength(long_password)
        self.assertTrue(any("must be" in issue for issue in issues))
        
        # Test weak but acceptable password
        issues = self.password_manager.validate_password_strength("simple")
        self.assertTrue(any("Consider using" in issue for issue in issues))


class TestSessionManager(unittest.TestCase):
    """Test session management functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
        self.test_user = User(
            nickname="testuser",
            password="hashed_password",
            created=datetime.now()
        )
    
    def test_create_session(self):
        """Test session creation."""
        token = self.session_manager.create_session(self.test_user)
        
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        self.assertIn(token, self.session_manager.active_sessions)
        
        session_data = self.session_manager.active_sessions[token]
        self.assertEqual(session_data["user"], self.test_user)
        self.assertIsInstance(session_data["created_at"], datetime)
        self.assertIsInstance(session_data["expires_at"], datetime)
    
    def test_get_session(self):
        """Test session retrieval."""
        token = self.session_manager.create_session(self.test_user)
        
        # Test valid session
        session_data = self.session_manager.get_session(token)
        self.assertIsNotNone(session_data)
        self.assertEqual(session_data["user"], self.test_user)
        
        # Test invalid session
        invalid_session = self.session_manager.get_session("invalid_token")
        self.assertIsNone(invalid_session)
    
    def test_get_user_from_session(self):
        """Test getting user from session token."""
        token = self.session_manager.create_session(self.test_user)
        
        # Test valid session
        user = self.session_manager.get_user_from_session(token)
        self.assertEqual(user, self.test_user)
        
        # Test invalid session
        user = self.session_manager.get_user_from_session("invalid_token")
        self.assertIsNone(user)
    
    def test_invalidate_session(self):
        """Test session invalidation."""
        token = self.session_manager.create_session(self.test_user)
        
        # Verify session exists
        self.assertIsNotNone(self.session_manager.get_session(token))
        
        # Invalidate session
        result = self.session_manager.invalidate_session(token)
        self.assertTrue(result)
        
        # Verify session is gone
        self.assertIsNone(self.session_manager.get_session(token))
        
        # Test invalidating non-existent session
        result = self.session_manager.invalidate_session("invalid_token")
        self.assertFalse(result)
    
    def test_session_expiration(self):
        """Test session expiration handling."""
        # Create session with short timeout
        original_timeout = self.session_manager.session_timeout
        self.session_manager.session_timeout = timedelta(seconds=1)
        
        token = self.session_manager.create_session(self.test_user)
        
        # Session should be valid initially
        self.assertIsNotNone(self.session_manager.get_session(token))
        
        # Manually expire the session
        session_data = self.session_manager.active_sessions[token]
        session_data["expires_at"] = datetime.now() - timedelta(seconds=1)
        
        # Session should now be invalid and cleaned up
        self.assertIsNone(self.session_manager.get_session(token))
        self.assertNotIn(token, self.session_manager.active_sessions)
        
        # Restore original timeout
        self.session_manager.session_timeout = original_timeout
    
    def test_extend_session(self):
        """Test session extension."""
        token = self.session_manager.create_session(self.test_user)
        
        original_expiry = self.session_manager.active_sessions[token]["expires_at"]
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        # Extend session
        result = self.session_manager.extend_session(token)
        self.assertTrue(result)
        
        new_expiry = self.session_manager.active_sessions[token]["expires_at"]
        self.assertGreater(new_expiry, original_expiry)
        
        # Test extending invalid session
        result = self.session_manager.extend_session("invalid_token")
        self.assertFalse(result)
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        # Create multiple sessions
        token1 = self.session_manager.create_session(self.test_user)
        token2 = self.session_manager.create_session(self.test_user)
        
        # Expire one session
        session_data = self.session_manager.active_sessions[token1]
        session_data["expires_at"] = datetime.now() - timedelta(seconds=1)
        
        # Cleanup expired sessions
        cleaned_count = self.session_manager.cleanup_expired_sessions()
        
        self.assertEqual(cleaned_count, 1)
        self.assertNotIn(token1, self.session_manager.active_sessions)
        self.assertIn(token2, self.session_manager.active_sessions)


class TestUserManager(unittest.TestCase):
    """Test user management functionality."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_manager = StorageManager(self.temp_dir)
        self.user_manager = UserManager(self.storage_manager)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_register_user_success(self):
        """Test successful user registration."""
        nickname = "testuser"
        password = "testpass123"
        
        success, message = self.user_manager.register_user(nickname, password)
        
        self.assertTrue(success)
        self.assertIn("successfully", message.lower())
        self.assertTrue(self.storage_manager.user_exists(nickname))
        
        # Verify user file was created
        user_profile_path = self.storage_manager._get_user_profile_path(nickname)
        self.assertTrue(user_profile_path.exists())
        
        # Verify user directory was created
        user_dir = self.storage_manager._get_user_directory(nickname)
        self.assertTrue(user_dir.exists())
    
    def test_register_user_invalid_nickname(self):
        """Test user registration with invalid nickname."""
        invalid_nicknames = ["", "a", "a" * 60, "user@name", "user name"]
        
        for nickname in invalid_nicknames:
            success, message = self.user_manager.register_user(nickname, "validpass")
            self.assertFalse(success)
            self.assertIn("nickname", message.lower())
    
    def test_register_user_invalid_password(self):
        """Test user registration with invalid password."""
        invalid_passwords = ["", "123", "a" * 200]
        
        for password in invalid_passwords:
            success, message = self.user_manager.register_user("validuser", password)
            self.assertFalse(success)
            self.assertIn("password", message.lower())
    
    def test_register_user_duplicate(self):
        """Test registration with duplicate nickname."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user first time
        success1, _ = self.user_manager.register_user(nickname, password)
        self.assertTrue(success1)
        
        # Try to register same user again
        success2, message2 = self.user_manager.register_user(nickname, password)
        self.assertFalse(success2)
        self.assertIn("already exists", message2.lower())
    
    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user first
        self.user_manager.register_user(nickname, password)
        
        # Authenticate user
        user, message = self.user_manager.authenticate_user(nickname, password)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.nickname, nickname)
        self.assertIn("successful", message.lower())
    
    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        user, message = self.user_manager.authenticate_user("nonexistent", "password")
        
        self.assertIsNone(user)
        self.assertIn("not found", message.lower())
    
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        nickname = "testuser"
        password = "testpass123"
        wrong_password = "wrongpass"
        
        # Register user first
        self.user_manager.register_user(nickname, password)
        
        # Try to authenticate with wrong password
        user, message = self.user_manager.authenticate_user(nickname, wrong_password)
        
        self.assertIsNone(user)
        self.assertIn("password", message.lower())
    
    def test_login_user_success(self):
        """Test successful user login."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user first
        self.user_manager.register_user(nickname, password)
        
        # Login user
        session_token, message = self.user_manager.login_user(nickname, password)
        
        self.assertIsNotNone(session_token)
        self.assertIsInstance(session_token, str)
        self.assertTrue(len(session_token) > 0)
        self.assertIn("successful", message.lower())
    
    def test_login_user_failure(self):
        """Test failed user login."""
        session_token, message = self.user_manager.login_user("nonexistent", "password")
        
        self.assertIsNone(session_token)
        self.assertIn("not found", message.lower())
    
    def test_logout_user(self):
        """Test user logout."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Verify user is logged in
        self.assertTrue(self.user_manager.is_user_logged_in(session_token))
        
        # Logout user
        result = self.user_manager.logout_user(session_token)
        self.assertTrue(result)
        
        # Verify user is logged out
        self.assertFalse(self.user_manager.is_user_logged_in(session_token))
    
    def test_get_current_user(self):
        """Test getting current user from session."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Get current user
        user = self.user_manager.get_current_user(session_token)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.nickname, nickname)
        
        # Test with invalid session
        user = self.user_manager.get_current_user("invalid_token")
        self.assertIsNone(user)
    
    def test_update_user_preferences(self):
        """Test updating user preferences."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Update preferences
        new_preferences = {
            "ui_theme": "dark",
            "auto_remix": True,
            "voice_settings": {"speed": 1.2}
        }
        
        success, message = self.user_manager.update_user_preferences(session_token, new_preferences)
        
        self.assertTrue(success)
        self.assertIn("updated", message.lower())
        
        # Verify preferences were updated
        user = self.user_manager.get_current_user(session_token)
        self.assertEqual(user.preferences["ui_theme"], "dark")
        self.assertEqual(user.preferences["auto_remix"], True)
        self.assertEqual(user.preferences["voice_settings"]["speed"], 1.2)
        
        # Verify password salt is preserved
        self.assertIn("password_salt", user.preferences)
    
    def test_change_password(self):
        """Test changing user password."""
        nickname = "testuser"
        old_password = "oldpass123"
        new_password = "newpass456"
        
        # Register and login user
        self.user_manager.register_user(nickname, old_password)
        session_token, _ = self.user_manager.login_user(nickname, old_password)
        
        # Change password
        success, message = self.user_manager.change_password(session_token, old_password, new_password)
        
        self.assertTrue(success)
        self.assertIn("changed", message.lower())
        
        # Verify old password no longer works
        user, _ = self.user_manager.authenticate_user(nickname, old_password)
        self.assertIsNone(user)
        
        # Verify new password works
        user, _ = self.user_manager.authenticate_user(nickname, new_password)
        self.assertIsNotNone(user)
    
    def test_change_password_wrong_current(self):
        """Test changing password with wrong current password."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Try to change password with wrong current password
        success, message = self.user_manager.change_password(session_token, "wrongpass", "newpass")
        
        self.assertFalse(success)
        self.assertIn("incorrect", message.lower())
    
    def test_get_user_info(self):
        """Test getting user information."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Get user info
        user_info = self.user_manager.get_user_info(session_token)
        
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["nickname"], nickname)
        self.assertIn("created", user_info)
        self.assertIn("total_prompts", user_info)
        self.assertIn("preferences", user_info)
        
        # Verify sensitive data is not included
        self.assertNotIn("password_salt", user_info["preferences"])
    
    def test_list_users(self):
        """Test listing all users."""
        # Register multiple users
        users = ["user1", "user2", "user3"]
        for user in users:
            self.user_manager.register_user(user, "password123")
        
        # List users
        user_list = self.user_manager.list_users()
        
        self.assertEqual(len(user_list), 3)
        for user in users:
            self.assertIn(user, user_list)
    
    def test_session_extension(self):
        """Test session extension functionality."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register and login user
        self.user_manager.register_user(nickname, password)
        session_token, _ = self.user_manager.login_user(nickname, password)
        
        # Get original session info
        original_info = self.user_manager.get_session_info(session_token)
        self.assertIsNotNone(original_info)
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        # Extend session
        result = self.user_manager.extend_user_session(session_token)
        self.assertTrue(result)
        
        # Verify session was extended
        new_info = self.user_manager.get_session_info(session_token)
        self.assertIsNotNone(new_info)
        self.assertGreater(new_info["expires_at"], original_info["expires_at"])
    
    def test_cleanup_sessions(self):
        """Test session cleanup functionality."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user
        self.user_manager.register_user(nickname, password)
        
        # Create multiple sessions
        session1, _ = self.user_manager.login_user(nickname, password)
        session2, _ = self.user_manager.login_user(nickname, password)
        
        # Manually expire one session
        session_data = self.user_manager.session_manager.active_sessions[session1]
        session_data["expires_at"] = datetime.now() - timedelta(seconds=1)
        
        # Cleanup sessions
        cleaned_count = self.user_manager.cleanup_sessions()
        
        self.assertEqual(cleaned_count, 1)
        self.assertIsNone(self.user_manager.get_current_user(session1))
        self.assertIsNotNone(self.user_manager.get_current_user(session2))


class TestAuthenticationIntegration(unittest.TestCase):
    """Integration tests for the complete authentication flow."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_manager = StorageManager(self.temp_dir)
        self.user_manager = UserManager(self.storage_manager)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_user_lifecycle(self):
        """Test complete user lifecycle from registration to deletion."""
        nickname = "testuser"
        password = "testpass123"
        new_password = "newpass456"
        
        # 1. Register user
        success, message = self.user_manager.register_user(nickname, password)
        self.assertTrue(success)
        
        # 2. Login user
        session_token, message = self.user_manager.login_user(nickname, password)
        self.assertIsNotNone(session_token)
        
        # 3. Update preferences
        preferences = {"ui_theme": "dark", "auto_remix": True}
        success, message = self.user_manager.update_user_preferences(session_token, preferences)
        self.assertTrue(success)
        
        # 4. Change password
        success, message = self.user_manager.change_password(session_token, password, new_password)
        self.assertTrue(success)
        
        # 5. Logout
        success = self.user_manager.logout_user(session_token)
        self.assertTrue(success)
        
        # 6. Login with new password
        session_token2, message = self.user_manager.login_user(nickname, new_password)
        self.assertIsNotNone(session_token2)
        
        # 7. Verify preferences persisted
        user_info = self.user_manager.get_user_info(session_token2)
        self.assertEqual(user_info["preferences"]["ui_theme"], "dark")
        self.assertEqual(user_info["preferences"]["auto_remix"], True)
        
        # 8. Delete user (admin override)
        success, message = self.user_manager.delete_user(nickname, admin_override=True)
        self.assertTrue(success)
        
        # 9. Verify user is gone
        self.assertFalse(self.storage_manager.user_exists(nickname))
        self.assertIsNone(self.user_manager.get_current_user(session_token2))
    
    def test_concurrent_sessions(self):
        """Test multiple concurrent sessions for the same user."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user
        self.user_manager.register_user(nickname, password)
        
        # Create multiple sessions
        session1, _ = self.user_manager.login_user(nickname, password)
        session2, _ = self.user_manager.login_user(nickname, password)
        session3, _ = self.user_manager.login_user(nickname, password)
        
        # All sessions should be valid
        self.assertIsNotNone(self.user_manager.get_current_user(session1))
        self.assertIsNotNone(self.user_manager.get_current_user(session2))
        self.assertIsNotNone(self.user_manager.get_current_user(session3))
        
        # Logout one session
        self.user_manager.logout_user(session2)
        
        # Other sessions should still be valid
        self.assertIsNotNone(self.user_manager.get_current_user(session1))
        self.assertIsNone(self.user_manager.get_current_user(session2))
        self.assertIsNotNone(self.user_manager.get_current_user(session3))
    
    def test_password_security(self):
        """Test password security features."""
        nickname = "testuser"
        password = "testpass123"
        
        # Register user
        self.user_manager.register_user(nickname, password)
        
        # Load user profile directly to check password storage
        user = self.storage_manager.load_user_profile(nickname)
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password, password)
        self.assertTrue(len(user.password) > len(password))
        
        # Salt should be stored in preferences
        self.assertIn("password_salt", user.preferences)
        self.assertTrue(len(user.preferences["password_salt"]) > 0)
        
        # Verify authentication still works
        auth_user, message = self.user_manager.authenticate_user(nickname, password)
        self.assertIsNotNone(auth_user)


if __name__ == '__main__':
    unittest.main()