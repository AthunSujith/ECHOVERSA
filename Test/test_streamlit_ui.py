"""
Unit tests for Streamlit UI foundation.
Tests authentication, form validation, and session management.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

from streamlit_workspace import StreamlitApp
from auth_manager import UserManager
from data_models import User


class TestStreamlitApp(unittest.TestCase):
    """Test cases for StreamlitApp class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Streamlit session state
        self.mock_session_state = {
            'authenticated': False,
            'session_token': None,
            'current_user': None,
            'show_signup': False,
            'error_message': '',
            'success_message': ''
        }
        
        # Create app instance with mocked dependencies
        with patch('streamlit_workspace.st') as mock_st:
            mock_st.session_state = self.mock_session_state
            self.app = StreamlitApp()
    
    def test_validate_login_form_valid(self):
        """Test login form validation with valid inputs."""
        is_valid, error_msg = self.app.validate_login_form("testuser", "password123")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_login_form_empty_nickname(self):
        """Test login form validation with empty nickname."""
        is_valid, error_msg = self.app.validate_login_form("", "password123")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Please enter your nickname.")
    
    def test_validate_login_form_empty_password(self):
        """Test login form validation with empty password."""
        is_valid, error_msg = self.app.validate_login_form("testuser", "")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Please enter your password.")
    
    def test_validate_login_form_short_nickname(self):
        """Test login form validation with short nickname."""
        is_valid, error_msg = self.app.validate_login_form("a", "password123")
        self.assertFalse(is_valid)
        self.assertEqual(error_msg, "Nickname must be at least 2 characters long.")
    
    def test_validate_signup_form_valid(self):
        """Test signup form validation with valid inputs."""
        is_valid, error_msg = self.app.validate_signup_form("testuser", "password123", "password123")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_signup_form_empty_nickname(self):
        """Test signup form validation with empty nickname."""