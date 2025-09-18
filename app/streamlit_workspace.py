"""
EchoVerse Companion Application - Streamlit UI
A local-first supportive companion application with multi-modal input processing,
AI-powered content generation, and audio processing capabilities.
"""

import streamlit as st
import sys
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import traceback
from datetime import datetime

# Add the app directory to the Python path for imports
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Import defensive system first
try:
    from defensive_system import (
        initialize_defensive_systems, get_defensive_logger, 
        get_notification_manager, get_degradation_manager,
        suppress_warnings
    )
    from logging_config import setup_application_logging, log_user_action
    from error_handlers import ErrorHandler, ErrorCategory, ErrorSeverity, error_boundary
    
    # Suppress common warnings
    suppress_warnings()
    
    # Initialize comprehensive logging
    app_logger = setup_application_logging()
    
    # Initialize defensive systems
    system_status = initialize_defensive_systems()
    
    app_logger.info("Defensive systems and logging initialized successfully")
    
except ImportError as e:
    st.error(f"Failed to import defensive system: {e}")
    st.stop()

# Import application modules with defensive handling
try:
    from auth_manager import UserManager, AuthenticationError
    from data_models import User, Interaction, GeneratedContent
    from storage_manager import StorageManager, HistoryManager
    from session_manager import SessionManager, SessionStateManager, SessionError
    from input_processor import InputProcessor
    from content_generator import ContentGenerator
    from audio_processor import AudioManager
    from performance_optimizer import (
        get_performance_optimizer, with_loading, with_progress, monitor_performance,
        LoadingIndicator, ProgressTracker, cache_result
    )
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.error("Please ensure all required dependencies are installed.")
    st.stop()


class StreamlitApp:
    """Main Streamlit application class."""
    
    def __init__(self):
        """Initialize the Streamlit application with defensive systems."""
        self.setup_page_config()
        self.initialize_session_state()
        
        # Initialize defensive system components
        self.logger = get_defensive_logger("streamlit_app")
        self.notification_manager = get_notification_manager()
        self.degradation_manager = get_degradation_manager()
        
        # Initialize application components with error handling
        try:
            # Initialize performance optimizer first
            self.performance_optimizer = get_performance_optimizer()
            
            self.user_manager = UserManager()
            self.storage_manager = StorageManager()
            self.history_manager = HistoryManager(self.storage_manager)
            
            # Initialize session management
            self.session_manager = SessionManager(self.storage_manager)
            self.session_state_manager = SessionStateManager(self.session_manager)
            
            self.input_processor = InputProcessor()
            
            # Initialize content generation and audio processing
            self.content_generator = ContentGenerator()
            self.audio_manager = AudioManager()
            
            # Check storage availability on startup
            self._check_storage_availability()
            
            self.logger.logger.info("Application components initialized successfully")
            
        except Exception as e:
            self.logger.logger.error(f"Failed to initialize application components: {e}")
            st.error(f"Application initialization failed: {e}")
            st.error("Please check the logs and ensure all dependencies are properly installed.")
            st.stop()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="EchoVerse Companion",
            page_icon="🎵",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        # Authentication state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
        if 'current_user' not in st.session_state:
            st.session_state.current_user = None
        
        # Session persistence state
        if 'session_restored' not in st.session_state:
            st.session_state.session_restored = False
        if 'storage_available' not in st.session_state:
            st.session_state.storage_available = True
        if 'storage_error_message' not in st.session_state:
            st.session_state.storage_error_message = ""
        
        # UI state
        if 'show_signup' not in st.session_state:
            st.session_state.show_signup = False
        if 'error_message' not in st.session_state:
            st.session_state.error_message = ""
        if 'success_message' not in st.session_state:
            st.session_state.success_message = ""
        if 'login_in_progress' not in st.session_state:
            st.session_state.login_in_progress = False
        if 'login_just_completed' not in st.session_state:
            st.session_state.login_just_completed = False
    
    def show_error(self, message: str):
        """Display error message to user."""
        st.session_state.error_message = message
    
    def show_success(self, message: str):
        """Display success message to user."""
        st.session_state.success_message = message
    
    def clear_messages(self):
        """Clear all messages."""
        st.session_state.error_message = ""
        st.session_state.success_message = ""
    
    def _check_storage_availability(self):
        """
        Check storage availability and update session state.
        Implements requirement 6.5: error handling for storage unavailability.
        """
        try:
            is_available, error_message = self.session_manager.check_storage_availability()
            st.session_state.storage_available = is_available
            st.session_state.storage_error_message = error_message
            
            if not is_available:
                self.logger.logger.error(f"Storage unavailable: {error_message}")
            
        except Exception as e:
            st.session_state.storage_available = False
            st.session_state.storage_error_message = f"Storage check failed: {e}"
            self.logger.logger.error(f"Storage availability check failed: {e}")
    
    def display_messages(self):
        """Display any pending messages."""
        if st.session_state.error_message:
            # Don't show session expiration error if user is authenticated
            if ("session has expired" in st.session_state.error_message.lower() and 
                st.session_state.get('authenticated', False)):
                # Clear the session expiration error for authenticated users
                st.session_state.error_message = ""
            else:
                st.error(st.session_state.error_message)
        if st.session_state.success_message:
            st.success(st.session_state.success_message)
    
    def validate_login_form(self, nickname: str, password: str) -> tuple[bool, str]:
        """
        Validate login form inputs.
        
        Args:
            nickname: User's nickname
            password: User's password
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not nickname.strip():
            return False, "Please enter your nickname."
        if not password:
            return False, "Please enter your password."
        if len(nickname.strip()) < 2:
            return False, "Nickname must be at least 2 characters long."
        return True, ""
    
    def validate_signup_form(self, nickname: str, password: str, confirm_password: str) -> tuple[bool, str]:
        """
        Validate signup form inputs.
        
        Args:
            nickname: User's chosen nickname
            password: User's password
            confirm_password: Password confirmation
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not nickname.strip():
            return False, "Please enter a nickname."
        if not password:
            return False, "Please enter a password."
        if not confirm_password:
            return False, "Please confirm your password."
        
        nickname = nickname.strip()
        
        # Validate nickname format
        if len(nickname) < 2 or len(nickname) > 50:
            return False, "Nickname must be between 2 and 50 characters long."
        
        # Check for valid characters (alphanumeric, underscore, hyphen)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', nickname):
            return False, "Nickname can only contain letters, numbers, underscores, and hyphens."
        
        # Validate password
        if len(password) < 4:
            return False, "Password must be at least 4 characters long."
        if len(password) > 128:
            return False, "Password is too long (maximum 128 characters)."
        
        # Check password confirmation
        if password != confirm_password:
            return False, "Passwords do not match."
        
        return True, ""
    
    @error_boundary("authentication", fallback_value=None)
    def handle_login(self, nickname: str, password: str):
        """
        Handle user login attempt with comprehensive error handling.
        
        Args:
            nickname: User's nickname
            password: User's password
        """
        error_handler = ErrorHandler("authentication")
        
        try:
            # Set login in progress flag to prevent authentication check interference
            st.session_state.login_in_progress = True
            
            # Clear previous messages
            self.clear_messages()
            
            # Validate form inputs
            is_valid, error_msg = self.validate_login_form(nickname, password)
            if not is_valid:
                st.session_state.login_in_progress = False
                self.show_error(error_msg)
                log_user_action(app_logger, nickname, "login_validation_failed", {"reason": error_msg})
                return
            
            # Show loading indicator during login
            with LoadingIndicator("Authenticating user...", show_spinner=True):
                # Attempt login with timing
                start_time = time.time()
                session_token, message = self.user_manager.login_user(nickname.strip(), password)
                login_duration = time.time() - start_time
            
            if session_token:
                # Login successful
                current_user = self.user_manager.get_current_user(session_token)
                
                st.session_state.authenticated = True
                st.session_state.session_token = session_token
                st.session_state.current_user = current_user
                
                # Explicitly clear any error messages from previous session checks
                st.session_state.error_message = ""
                
                # Start session management and restore previous state
                try:
                    self.session_manager.start_session(current_user, session_token)
                    
                    # Restore previous workspace state if available
                    if not st.session_state.session_restored:
                        with LoadingIndicator("Restoring your session...", show_spinner=False):
                            restored_data = self.session_manager.restore_session_on_startup(current_user, session_token)
                            if restored_data and restored_data.get("workspace_state"):
                                # Apply restored state to Streamlit session
                                workspace_state = restored_data["workspace_state"]
                                streamlit_state = workspace_state.get("streamlit_state", {})
                                for key, value in streamlit_state.items():
                                    if key not in st.session_state:
                                        st.session_state[key] = value
                                
                                # Show restoration info
                                restored_count = restored_data.get("restored_interactions", 0)
                                last_activity = restored_data.get("last_activity", "")
                                
                                if restored_count > 0:
                                    self.show_success(f"Welcome back, {nickname}! Restored {restored_count} interactions from your previous session.")
                                else:
                                    self.show_success(f"Welcome back, {nickname}! Your session has been restored.")
                            else:
                                self.show_success(f"Welcome back, {nickname}!")
                            
                            st.session_state.session_restored = True
                            
                            # Preload history cache and user data for better performance
                            self.session_manager.preload_history_cache(current_user, background=True)
                            self.performance_optimizer.preload_user_data(current_user, background=True)
                    
                except SessionError as e:
                    self.logger.logger.error(f"Session management error: {e}")
                    self.show_success(f"Welcome back, {nickname}! (Session management unavailable)")
                
                # Log successful login
                log_user_action(app_logger, nickname, "login_success", {
                    "duration": f"{login_duration:.3f}s",
                    "session_token": session_token[:8] + "..."
                })
                
                # Clear login in progress flag and set login success flag
                st.session_state.login_in_progress = False
                st.session_state.login_just_completed = True
            else:
                # Login failed
                st.session_state.login_in_progress = False
                self.show_error(message)
                log_user_action(app_logger, nickname, "login_failed", {"reason": message})
                
                # Handle specific authentication errors
                if "not found" in message.lower():
                    error_handler.handle_error(
                        error=Exception("User not found"),
                        category=ErrorCategory.AUTHENTICATION,
                        severity=ErrorSeverity.LOW,
                        user_message="Username not found. Please check your username or sign up for a new account."
                    )
                elif "password" in message.lower():
                    error_handler.handle_error(
                        error=Exception("Invalid password"),
                        category=ErrorCategory.AUTHENTICATION,
                        severity=ErrorSeverity.LOW,
                        user_message="Incorrect password. Please try again."
                    )
                
        except Exception as e:
            # Clear login in progress flag on exception
            st.session_state.login_in_progress = False
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context={"username": nickname, "operation": "login"},
                user_message="Login system temporarily unavailable. Please try again in a moment."
            )
            self.show_error("Login failed due to a system error. Please try again.")
    
    def handle_signup(self, nickname: str, password: str, confirm_password: str):
        """
        Handle user registration attempt.
        
        Args:
            nickname: User's chosen nickname
            password: User's password
            confirm_password: Password confirmation
        """
        try:
            # Clear previous messages
            self.clear_messages()
            
            # Validate form inputs
            is_valid, error_msg = self.validate_signup_form(nickname, password, confirm_password)
            if not is_valid:
                self.show_error(error_msg)
                return
            
            # Attempt registration
            success, message = self.user_manager.register_user(nickname.strip(), password)
            
            if success:
                # Registration successful
                self.show_success(message)
                self.show_success("You can now log in with your new account.")
                # Switch back to login form
                st.session_state.show_signup = False
                st.rerun()
            else:
                # Registration failed
                self.show_error(message)
                
        except Exception as e:
            self.show_error(f"Registration failed: {str(e)}")
    
    def handle_logout(self):
        """Handle user logout with comprehensive session persistence."""
        try:
            # Save current workspace state before logout
            if st.session_state.authenticated and st.session_state.current_user:
                try:
                    # Save current Streamlit session state
                    current_state = {
                        key: value for key, value in st.session_state.items()
                        if key not in ['authenticated', 'session_token', 'current_user', 'error_message', 'success_message']
                    }
                    self.session_state_manager.save_state_to_session(current_state)
                    
                    # Create final backup before logout
                    self.session_manager.create_data_backup(st.session_state.current_user, "logout")
                    
                    # End session management with persistence
                    self.session_manager.persist_session_on_shutdown()
                    self.session_manager.end_session()
                    
                except Exception as e:
                    self.logger.logger.error(f"Error saving session state during logout: {e}")
            
            # Logout from user manager
            if st.session_state.session_token:
                self.user_manager.logout_user(st.session_state.session_token)
            
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.session_token = None
            st.session_state.current_user = None
            st.session_state.session_restored = False
            self.clear_messages()
            
            self.show_success("You have been logged out successfully. Your session and data have been saved.")
            st.rerun()
            
        except Exception as e:
            self.show_error(f"Logout failed: {str(e)}")
    
    def handle_application_shutdown(self):
        """Handle application shutdown with comprehensive data persistence."""
        try:
            if st.session_state.authenticated and st.session_state.current_user:
                # Save current state
                current_state = {
                    key: value for key, value in st.session_state.items()
                    if key not in ['authenticated', 'session_token', 'current_user']
                }
                self.session_state_manager.save_state_to_session(current_state)
                
                # Create shutdown backup
                self.session_manager.create_data_backup(st.session_state.current_user, "shutdown")
                
                # Persist session
                self.session_manager.persist_session_on_shutdown()
                
                # Clean up old sessions (keep last 30 days)
                self.session_manager.cleanup_expired_sessions(max_age_days=30)
                
                self.logger.logger.info(f"Application shutdown completed for user {st.session_state.current_user.nickname}")
                
        except Exception as e:
            self.logger.logger.error(f"Error during application shutdown: {e}")
    
    def render_login_page(self):
        """Render the login/signup page."""
        st.title("🎵 EchoVerse Companion")
        st.markdown("### Your Personal AI Companion for Emotional Support")
        
        # Display messages
        self.display_messages()
        
        # Create two columns for better layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Toggle between login and signup
            if st.session_state.show_signup:
                st.subheader("Create New Account")
                
                with st.form("signup_form", clear_on_submit=False):
                    nickname = st.text_input(
                        "Choose a Nickname",
                        placeholder="Enter a unique nickname",
                        help="2-50 characters, letters, numbers, underscores, and hyphens only"
                    )
                    password = st.text_input(
                        "Create Password",
                        type="password",
                        placeholder="Enter a secure password",
                        help="Minimum 4 characters"
                    )
                    confirm_password = st.text_input(
                        "Confirm Password",
                        type="password",
                        placeholder="Re-enter your password"
                    )
                    
                    col_signup, col_back = st.columns(2)
                    with col_signup:
                        signup_clicked = st.form_submit_button("Create Account", type="primary")
                    with col_back:
                        back_clicked = st.form_submit_button("Back to Login")
                    
                    if signup_clicked:
                        self.handle_signup(nickname, password, confirm_password)
                    
                    if back_clicked:
                        st.session_state.show_signup = False
                        self.clear_messages()
                        st.rerun()
            
            else:
                st.subheader("Welcome Back")
                
                with st.form("login_form", clear_on_submit=False):
                    nickname = st.text_input(
                        "Nickname",
                        placeholder="Enter your nickname"
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Enter your password"
                    )
                    
                    col_login, col_signup = st.columns(2)
                    with col_login:
                        login_clicked = st.form_submit_button("Log In", type="primary")
                    with col_signup:
                        signup_clicked = st.form_submit_button("Sign Up")
                    
                    if login_clicked:
                        self.handle_login(nickname, password)
                    
                    if signup_clicked:
                        st.session_state.show_signup = True
                        self.clear_messages()
                        st.rerun()
        
        # Add some information about the app
        st.markdown("---")
        st.markdown("""
        **EchoVerse Features:**
        - 🔒 **Privacy First**: All your data stays on your device
        - 💬 **Multi-Modal Input**: Text, audio, and drawings
        - 🤖 **AI Support**: Personalized supportive responses and poems
        - 🎵 **Audio Generation**: Text-to-speech with optional music remixes
        - 📚 **History Tracking**: Keep track of your emotional journey
        """)
    
    def render_workspace(self):
        """Render the main workspace interface with two-panel layout."""
        # Initialize workspace session state
        self.initialize_workspace_state()
        
        # Header with user info and logout
        self.render_workspace_header()
        
        # Display messages
        self.display_messages()
        
        # Main two-panel layout
        self.render_two_panel_layout()
    
    def initialize_workspace_state(self):
        """Initialize workspace-specific session state variables."""
        # Navigation state
        if 'selected_interaction' not in st.session_state:
            st.session_state.selected_interaction = None
        if 'workspace_view' not in st.session_state:
            st.session_state.workspace_view = 'new_interaction'  # 'new_interaction' or 'view_interaction'
        
        # Input state
        if 'current_input_type' not in st.session_state:
            st.session_state.current_input_type = 'text'
        if 'input_text' not in st.session_state:
            st.session_state.input_text = ""
        
        # Output state
        if 'current_output' not in st.session_state:
            st.session_state.current_output = None
        if 'show_debug_info' not in st.session_state:
            st.session_state.show_debug_info = False
        
        # Processing state
        if 'current_processed_input' not in st.session_state:
            st.session_state.current_processed_input = None
    
    def render_workspace_header(self):
        """Render the workspace header with user info and controls."""
        header_col1, header_col2, header_col3, header_col4 = st.columns([3, 1, 1, 1])
        
        with header_col1:
            st.title("🎵 EchoVerse Workspace")
            if st.session_state.current_user:
                st.markdown(f"Welcome back, **{st.session_state.current_user.nickname}**!")
        
        with header_col2:
            # System status indicator
            self.render_system_status_indicator()
        
        with header_col3:
            # Workspace view toggle
            if st.button("🏠 New Chat", help="Start a new interaction"):
                st.session_state.workspace_view = 'new_interaction'
                st.session_state.selected_interaction = None
                st.session_state.current_output = None
                st.rerun()
        
        with header_col4:
            # Debug toggle and logout
            debug_col, logout_col = st.columns([1, 1])
            with debug_col:
                if st.button("🔧", help="Toggle debug info"):
                    st.session_state.show_debug_info = not st.session_state.get('show_debug_info', False)
                    st.rerun()
            with logout_col:
                if st.button("Logout", type="secondary"):
                    self.handle_logout()
        
        # Display system notifications
        self.render_system_notifications()
        
        # Display performance metrics in debug mode
        if st.session_state.get('show_debug_info', False):
            self.render_performance_metrics()
    
    def render_two_panel_layout(self):
        """Render the main two-panel layout (history left, workspace right)."""
        # Create two columns with custom CSS for better styling
        self.apply_workspace_styling()
        
        # Two-panel layout: history (30%) and workspace (70%)
        history_col, workspace_col = st.columns([3, 7], gap="medium")
        
        with history_col:
            self.render_history_panel()
        
        with workspace_col:
            self.render_workspace_panel()
    
    def apply_workspace_styling(self):
        """Apply enhanced CSS styling for the workspace with improved UX."""
        # Load enhanced CSS from file if available, otherwise use embedded CSS
        try:
            css_file = Path(__file__).parent / "enhanced_styles.css"
            if css_file.exists():
                with open(css_file, 'r', encoding='utf-8') as f:
                    enhanced_css = f.read()
                st.markdown(enhanced_css, unsafe_allow_html=True)
                return
        except Exception:
            pass
        
        # Fallback to embedded enhanced CSS
        st.markdown("""
        <style>
        /* Enhanced workspace styling with better visual hierarchy */
        .workspace-panel {
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 12px;
            padding: 24px;
            margin: 12px 0;
            border: 1px solid #e9ecef;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
        }
        
        .workspace-panel:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.12);
            transform: translateY(-2px);
        }
        
        /* Enhanced history panel with better scrolling */
        .history-panel {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            border: 1px solid #dee2e6;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        /* Custom scrollbar for history panel */
        .history-panel::-webkit-scrollbar {
            width: 8px;
        }
        
        .history-panel::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .history-panel::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 4px;
            transition: background 0.3s ease;
        }
        
        .history-panel::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Enhanced history items with better interaction feedback */
        .history-item {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            position: relative;
            overflow: hidden;
        }
        
        .history-item:hover {
            background: linear-gradient(135deg, #e9f4ff 0%, #f0f8ff 100%);
            transform: translateX(4px) translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,123,255,0.15);
            border-left-color: #0056b3;
        }
        
        .history-item.selected {
            background: linear-gradient(135deg, #cce5ff 0%, #e6f3ff 100%);
            border-left-color: #0056b3;
            box-shadow: 0 4px 16px rgba(0,123,255,0.25);
            transform: translateX(6px);
        }
        
        /* Enhanced output area with better content presentation */
        .output-area {
            background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #e1e5e9;
            min-height: 200px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            position: relative;
        }
        
        .output-area::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #007bff, #28a745, #ffc107, #dc3545);
            border-radius: 12px 12px 0 0;
        }
        
        /* Enhanced input area with better focus states */
        .input-area {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 12px;
            padding: 24px;
            border: 2px solid #e9ecef;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .input-area:focus-within {
            border-color: #007bff;
            box-shadow: 0 4px 16px rgba(0,123,255,0.15);
            transform: translateY(-2px);
        }
        
        /* Enhanced buttons with better interaction feedback */
        .stButton > button {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 8px rgba(0,123,255,0.3);
            position: relative;
            overflow: hidden;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,123,255,0.4);
        }
        
        .stButton > button:active {
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(0,123,255,0.3);
        }
        
        /* Enhanced loading indicators */
        .loading-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 10px;
            border: 1px solid #e9ecef;
            margin: 16px 0;
        }
        
        /* Enhanced notifications */
        .notification {
            border-radius: 10px;
            padding: 16px;
            margin: 12px 0;
            border-left: 4px solid;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Enhanced form inputs */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #e9ecef;
            padding: 12px 16px;
            transition: all 0.3s ease;
            font-size: 16px;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #007bff;
            box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
            outline: none;
        }
        
        /* Responsive design improvements */
        @media (max-width: 768px) {
            .workspace-panel, .history-panel {
                margin: 8px 0;
                padding: 16px;
            }
            
            .output-area, .input-area {
                padding: 16px;
                margin: 16px 0;
            }
            
            .history-item {
                padding: 12px;
                margin: 8px 0;
            }
        }
        
        /* Animation for smooth transitions */
        * {
            transition: color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
        }
        
        /* Focus indicators for accessibility */
        button:focus, input:focus, textarea:focus, select:focus {
            outline: 2px solid #007bff;
            outline-offset: 2px;
        }
                padding: 10px;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    def render_history_panel(self):
        """Render the left history panel with optimized loading and caching."""
        st.markdown('<div class="history-panel">', unsafe_allow_html=True)
        
        st.subheader("📚 Your Journey")
        
        # Check if user is authenticated
        if not st.session_state.current_user:
            st.info("Please log in to view your interaction history.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        try:
            # Load user history with caching and loading indicator
            with LoadingIndicator("Loading your history...", show_spinner=False):
                history_items = self.load_user_history_cached()
            
            if not history_items:
                st.info("No interactions yet. Start by sharing your thoughts!")
                st.markdown('</div>', unsafe_allow_html=True)
                return
            
            # Show history count and stats with performance metrics
            stats = self.get_history_stats_cached(history_items)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Interactions", len(history_items))
            with col2:
                st.metric("This Week", stats.get('this_week', 0))
            
            # Add search functionality with debounced search
            search_query = st.text_input(
                "🔍 Search your history", 
                placeholder="Search interactions...",
                key="history_search"
            )
            
            # Filter history based on search with caching
            if search_query:
                with st.spinner("Searching..."):
                    filtered_items = self.search_history_cached(history_items, search_query)
            else:
                filtered_items = history_items
            
            # Display filtered results count
            if search_query and len(filtered_items) != len(history_items):
                st.markdown(f"*Found {len(filtered_items)} matching interactions*")
            
            # Mind map visualization toggle with lazy loading
            if len(history_items) > 1:
                show_mindmap = st.checkbox("🧠 Show Mind Map", value=False)
                if show_mindmap:
                    with LoadingIndicator("Generating mind map...", show_spinner=True):
                        self.render_mind_map_visualization(filtered_items)
            
            # History list with pagination
            st.markdown("### Recent Interactions")
            
            # Pagination for large histories
            items_per_page = 10
            total_pages = (len(filtered_items) + items_per_page - 1) // items_per_page
            
            if total_pages > 1:
                page = st.selectbox("Page", range(1, total_pages + 1), index=0)
                start_idx = (page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_items = filtered_items[start_idx:end_idx]
                
                # Show pagination info
                st.markdown(f"*Showing {start_idx + 1}-{min(end_idx, len(filtered_items))} of {len(filtered_items)} interactions*")
            else:
                page_items = filtered_items[:items_per_page]
            
            # Display history items with optimized rendering
            for i, item in enumerate(page_items):
                self.render_history_item_optimized(item, i)
        
        except Exception as e:
            st.error(f"Error loading history: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    @monitor_performance("load_user_history_cached")
    def load_user_history_cached(self):
        """Load user history with caching for better performance."""
        cache_key = f"user_history_{st.session_state.current_user.nickname}"
        
        # Try to get from performance optimizer cache
        cached_history = self.performance_optimizer.cache.get(cache_key)
        if cached_history is not None:
            return cached_history
        
        # Load from storage and cache the result
        history_items = self.get_user_history_preview()
        self.performance_optimizer.cache.set(cache_key, history_items, ttl_override=300)  # 5 minutes
        
        return history_items
    
    @cache_result("history_stats_{args}", ttl=600)
    def get_history_stats_cached(self, history_items):
        """Get cached history statistics."""
        if not history_items:
            return {'this_week': 0, 'total': 0}
        
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        
        this_week_count = 0
        for item in history_items:
            try:
                item_date = datetime.fromisoformat(item.get('timestamp', ''))
                if item_date >= week_ago:
                    this_week_count += 1
            except (ValueError, TypeError):
                continue
        
        return {
            'this_week': this_week_count,
            'total': len(history_items)
        }
    
    @cache_result("search_history_{args}", ttl=60)
    def search_history_cached(self, history_items, query):
        """Cached history search with optimized filtering."""
        if not query or not history_items:
            return history_items
        
        query_lower = query.lower()
        filtered_items = []
        
        for item in history_items:
            # Search in multiple fields
            searchable_text = ' '.join([
                item.get('preview', ''),
                item.get('supportive_statement', ''),
                item.get('poem', ''),
                item.get('input_type', '')
            ]).lower()
            
            if query_lower in searchable_text:
                filtered_items.append(item)
        
        return filtered_items
    
    def render_history_item_optimized(self, item, index):
        """Optimized rendering of history items with lazy loading."""
        is_selected = (st.session_state.selected_interaction == item.get('id'))
        
        # Input type icon
        input_type_icons = {
            'text': '📝',
            'audio': '🎤', 
            'drawing': '🎨'
        }
        icon = input_type_icons.get(item.get('input_type', 'text'), '💬')
        
        # Use container for better performance
        with st.container():
            col1, col2, col3 = st.columns([1, 7, 1])
            
            with col1:
                st.markdown(f"<div style='font-size: 1.2em; text-align: center;'>{icon}</div>", 
                          unsafe_allow_html=True)
            
            with col2:
                button_key = f"history_item_{index}_{item.get('id', '')}"
                button_type = "primary" if is_selected else "secondary"
                
                # Truncate preview for better performance
                preview = item.get('preview', 'Untitled')
                if len(preview) > 50:
                    preview = preview[:47] + "..."
                
                if st.button(
                    preview,
                    key=button_key,
                    help=f"Created: {item.get('timestamp', 'Unknown')} | Type: {item.get('input_type', 'unknown')}",
                    width="stretch",
                    type=button_type
                ):
                    with LoadingIndicator("Loading interaction...", show_spinner=True):
                        self.load_interaction_from_history(item)
            
            with col3:
                # Show relative time
                try:
                    from datetime import datetime
                    item_time = datetime.fromisoformat(item.get('timestamp', ''))
                    now = datetime.now()
                    diff = now - item_time
                    
                    if diff.days > 0:
                        time_str = f"{diff.days}d"
                    elif diff.seconds > 3600:
                        time_str = f"{diff.seconds // 3600}h"
                    else:
                        time_str = f"{diff.seconds // 60}m"
                    
                    st.markdown(f"<small style='color: #666;'>{time_str}</small>", 
                              unsafe_allow_html=True)
                except:
                    st.markdown("<small style='color: #666;'>-</small>", 
                              unsafe_allow_html=True)

    def load_interaction_from_history(self, history_item):
        """Load a specific interaction from history into the workspace."""
        try:
            # Set selected interaction
            st.session_state.selected_interaction = history_item.get('id')
            st.session_state.workspace_view = 'view_interaction'
            
            # Load full interaction data if available
            if 'interaction_obj' in history_item:
                interaction = history_item['interaction_obj']
                
                # Convert interaction to output format for display
                output_data = {
                    'id': interaction.id,
                    'timestamp': interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'input_type': interaction.input_data.input_type.value if interaction.input_data else 'unknown',
                    'input_content': interaction.input_data.content if interaction.input_data else '',
                    'supportive_statement': interaction.generated_content.supportive_statement if interaction.generated_content else '',
                    'poem': interaction.generated_content.poem if interaction.generated_content else '',
                    'audio_files': [
                        {
                            'type': audio.metadata.get('type', 'unknown'),
                            'path': audio.file_path,
                            'duration': audio.duration
                        } for audio in interaction.audio_files
                    ],
                    'file_paths': interaction.file_paths
                }
                
                st.session_state.current_output = output_data
            else:
                # Fallback to history item data
                st.session_state.current_output = history_item
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error loading interaction: {str(e)}")
    
    def render_mind_map_visualization(self, history_items):
        """Render mind map visualization of user prompts."""
        st.markdown("---")
        st.markdown("**🗺️ Mind Map Visualization**")
        
        if not history_items:
            st.info("No interactions to visualize yet.")
            return
        
        # Toggle for mind map view
        show_mindmap = st.checkbox("Show Mind Map", key="show_mindmap")
        
        if show_mindmap:
            try:
                # Create a simple text-based mind map visualization
                self.render_text_mind_map(history_items)
                
                # Add option for interactive visualization
                if st.button("🔄 Refresh Mind Map", help="Update the mind map with latest interactions"):
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error rendering mind map: {str(e)}")
    
    def render_text_mind_map(self, history_items):
        """Render a text-based mind map of interactions."""
        try:
            # Group interactions by input type
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
            
            # Display the mind map
            st.markdown(mindmap_text)
            
            # Add summary statistics
            total_interactions = len(history_items)
            if total_interactions > 0:
                # Calculate some basic stats
                recent_date = max(item.get('timestamp', '') for item in history_items)
                oldest_date = min(item.get('timestamp', '') for item in history_items)
                
                st.markdown("**📊 Summary:**")
                st.markdown(f"- Total interactions: {total_interactions}")
                st.markdown(f"- Most recent: {recent_date}")
                st.markdown(f"- First interaction: {oldest_date}")
                
                # Show distribution by type
                type_counts = {}
                for item in history_items:
                    input_type = item.get('input_type', 'unknown')
                    type_counts[input_type] = type_counts.get(input_type, 0) + 1
                
                st.markdown("- Input type distribution:")
                for input_type, count in type_counts.items():
                    percentage = (count / total_interactions) * 100
                    st.markdown(f"  - {input_type.title()}: {count} ({percentage:.1f}%)")
                    
        except Exception as e:
            st.error(f"Error creating mind map: {str(e)}")
    
    def render_workspace_panel(self):
        """Render the right workspace panel with output area above input area."""
        st.markdown('<div class="workspace-panel">', unsafe_allow_html=True)
        
        # Output area (top)
        self.render_output_area()
        
        # Input area (bottom)
        self.render_input_area()
        
        # Debug info (collapsible)
        self.render_debug_section()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_system_status_indicator(self):
        """Render system status indicator in header"""
        try:
            active_issues = self.degradation_manager.active_issues
            
            if not active_issues:
                st.markdown("🟢 **System Healthy**")
            else:
                critical_issues = [i for i in active_issues if i.severity.value in ['critical', 'high']]
                if critical_issues:
                    st.markdown("🔴 **System Issues**")
                else:
                    st.markdown("🟡 **Limited Mode**")
            
            # Show details in expander
            if active_issues:
                with st.expander("System Status Details", expanded=False):
                    for issue in active_issues:
                        severity_icon = {
                            'critical': '🚨',
                            'high': '⚠️',
                            'medium': '⚠️',
                            'low': 'ℹ️',
                            'info': 'ℹ️'
                        }.get(issue.severity.value, 'ℹ️')
                        
                        st.markdown(f"{severity_icon} **{issue.component}**: {issue.message}")
                        if issue.details:
                            st.markdown(f"   {issue.details}")
                        if issue.suggested_action:
                            st.markdown(f"   💡 {issue.suggested_action}")
        
        except Exception as e:
            st.markdown("❓ **Status Unknown**")
            self.logger.logger.error(f"Failed to render system status: {e}")
    
    def render_system_notifications(self):
        """Render system notifications for degraded functionality"""
        try:
            notifications = self.degradation_manager.get_user_notifications()
            
            if notifications:
                # Group notifications by severity
                critical_notifications = []
                warning_notifications = []
                info_notifications = []
                
                for notification in notifications:
                    if "🚨" in notification:
                        critical_notifications.append(notification)
                    elif "⚠️" in notification:
                        warning_notifications.append(notification)
                    else:
                        info_notifications.append(notification)
                
                # Display critical notifications as errors
                for notification in critical_notifications:
                    st.error(notification.replace("🚨 ", ""))
                
                # Display warnings
                for notification in warning_notifications:
                    st.warning(notification.replace("⚠️ ", ""))
                
                # Display info notifications
                for notification in info_notifications:
                    st.info(notification.replace("ℹ️ ", ""))
        
        except Exception as e:
            self.logger.logger.error(f"Failed to render system notifications: {e}")
    
    def render_performance_metrics(self):
        """Render performance metrics dashboard for debugging."""
        if not st.session_state.get('show_debug_info', False):
            return
        
        with st.expander("🔧 Performance Metrics", expanded=False):
            try:
                # Get performance report
                perf_report = self.performance_optimizer.get_performance_report()
                
                # Display metrics in columns
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.subheader("Operations")
                    ops = perf_report.get('operations', {})
                    st.metric("Total Operations", ops.get('total_operations', 0))
                    st.metric("Avg Duration", f"{ops.get('avg_duration', 0):.3f}s")
                    st.metric("Success Rate", f"{ops.get('success_rate', 0):.1%}")
                
                with col2:
                    st.subheader("Cache Performance")
                    main_cache = perf_report.get('cache', {}).get('main_cache', {})
                    st.metric("Cache Size", main_cache.get('size', 0))
                    st.metric("Hit Rate", f"{main_cache.get('hit_rate', 0):.1%}")
                    st.metric("Hit Count", main_cache.get('hit_count', 0))
                
                with col3:
                    st.subheader("Memory Usage")
                    memory = perf_report.get('memory', {})
                    if 'rss' in memory:
                        st.metric("Memory (RSS)", f"{memory['rss'] / 1024 / 1024:.1f} MB")
                        st.metric("Memory %", f"{memory.get('percent', 0):.1f}%")
                    else:
                        st.metric("Objects", memory.get('objects', 0))
                
                # Cache controls
                st.subheader("Cache Controls")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Clear Main Cache"):
                        self.performance_optimizer.cache.clear()
                        st.success("Main cache cleared")
                        st.rerun()
                
                with col2:
                    if st.button("Clear File Cache"):
                        self.performance_optimizer.file_cache.clear()
                        st.success("File cache cleared")
                        st.rerun()
                
                with col3:
                    if st.button("Force Memory Cleanup"):
                        result = self.performance_optimizer.memory_optimizer.optimize_memory(force_gc=True)
                        st.success(f"Cleaned {result.get('objects_collected', 0)} objects")
                        st.rerun()
                
                # Performance history chart (if available)
                if hasattr(self.performance_optimizer, 'metrics') and self.performance_optimizer.metrics:
                    st.subheader("Recent Operations")
                    
                    # Create a simple chart of recent operation durations
                    recent_metrics = self.performance_optimizer.metrics[-20:]  # Last 20 operations
                    
                    if recent_metrics:
                        try:
                            import pandas as pd
                            
                            df = pd.DataFrame([
                                {
                                    'Operation': m.operation_name,
                                    'Duration': m.duration or 0,
                                    'Success': m.success,
                                    'Time': m.start_time
                                }
                                for m in recent_metrics
                            ])
                            
                            st.line_chart(df.set_index('Time')['Duration'])
                            
                            # Show recent operations table
                            st.dataframe(
                                df[['Operation', 'Duration', 'Success']].tail(10),
                                width="stretch"
                            )
                        except ImportError:
                            st.info("Install pandas to see performance charts")
                
            except Exception as e:
                st.error(f"Error displaying performance metrics: {e}")
    
    def render_output_area(self):
        """Render the output area above the input area."""
        st.markdown('<div class="output-area">', unsafe_allow_html=True)
        
        if st.session_state.workspace_view == 'view_interaction' and st.session_state.current_output:
            # Display loaded interaction
            self.render_interaction_content()
            
        elif st.session_state.workspace_view == 'new_interaction':
            # New interaction - show welcome message
            st.subheader("✨ Ready to Create")
            st.markdown("""
            Welcome to your personal AI companion! Share your thoughts through:
            - **Text**: Type your feelings or questions
            - **Audio**: Upload or record voice messages  
            - **Drawings**: Express yourself visually
            
            Your AI companion will respond with supportive messages and creative poems.
            """)
            
            # Show generated content
            if st.session_state.current_output:
                st.markdown("---")
                st.subheader("📝 Your Generated Content")
                # Display the actual content instead of placeholder
                self.render_interaction_content()
            else:
                st.markdown("---")
                st.subheader("📝 Your Generated Content")
                st.info("Generated content will appear here after processing your input.")
        
        else:
            # Default state
            st.subheader("💭 Your Space")
            st.markdown("Select an interaction from history or start a new conversation below.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_interaction_content(self):
        """Render the content of a loaded interaction with enhanced display and audio players."""
        try:
            output_data = st.session_state.current_output
            
            # Header with interaction info and controls
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.subheader("📝 Interaction Details")
            
            with col2:
                if st.button("🔄 Reload", help="Reload this interaction"):
                    self.reload_current_interaction()
            
            with col3:
                if st.button("📥 Download All", help="Download all generated content"):
                    self.download_interaction_content(output_data)
            
            with col4:
                if st.button("❌ Close", help="Return to new interaction"):
                    st.session_state.workspace_view = 'new_interaction'
                    st.session_state.selected_interaction = None
                    st.session_state.current_output = None
                    st.rerun()
            
            # Display interaction metadata with enhanced styling
            metadata_col1, metadata_col2 = st.columns(2)
            
            with metadata_col1:
                if output_data.get('timestamp'):
                    st.markdown(f"**📅 Created:** {output_data.get('timestamp')}")
                
                if output_data.get('input_type'):
                    type_icons = {'text': '📝', 'audio': '🎤', 'drawing': '🎨'}
                    icon = type_icons.get(output_data.get('input_type'), '💬')
                    st.markdown(f"**{icon} Input Type:** {output_data.get('input_type', 'unknown').title()}")
            
            with metadata_col2:
                # Show content statistics
                if output_data.get('supportive_statement'):
                    support_words = len(output_data.get('supportive_statement', '').split())
                    st.markdown(f"**📊 Support:** {support_words} words")
                
                if output_data.get('poem'):
                    poem_lines = len(output_data.get('poem', '').split('\n'))
                    st.markdown(f"**🎭 Poem:** {poem_lines} lines")
            
            st.markdown("---")
            
            # Display original input with enhanced formatting
            if output_data.get('input_content'):
                st.markdown("### 💭 Your Original Input")
                
                # Create a styled container for the input
                input_container = st.container()
                with input_container:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #f8f9fa;
                            border-left: 4px solid #007bff;
                            padding: 15px;
                            border-radius: 5px;
                            margin: 10px 0;
                            font-style: italic;
                        ">
                            {output_data.get('input_content')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Add download link for input
                if st.button("📥 Download Input Text", key="download_input"):
                    self.download_text_content(
                        output_data.get('input_content', ''),
                        f"input_{output_data.get('id', 'unknown')}.txt"
                    )
                
                st.markdown("---")
            
            # Enhanced supportive statement display
            if output_data.get('supportive_statement'):
                st.markdown("### 💝 Supportive Message")
                
                # Create styled container for supportive statement
                support_container = st.container()
                with support_container:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #e8f5e8;
                            border-left: 4px solid #28a745;
                            padding: 20px;
                            border-radius: 8px;
                            margin: 15px 0;
                            font-size: 1.1em;
                            line-height: 1.6;
                        ">
                            {output_data.get('supportive_statement')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Download and audio controls for supportive statement
                support_col1, support_col2 = st.columns(2)
                
                with support_col1:
                    if st.button("📥 Download Support Text", key="download_support"):
                        self.download_text_content(
                            output_data.get('supportive_statement', ''),
                            f"support_{output_data.get('id', 'unknown')}.txt"
                        )
                
                with support_col2:
                    # Look for support audio file
                    support_audio = self.find_audio_file(output_data, 'support')
                    if support_audio:
                        if st.button("🎵 Play Support Audio", key="play_support"):
                            st.session_state.current_playing_audio = support_audio
                            st.rerun()
                
                st.markdown("")
            
            # Enhanced poem display
            if output_data.get('poem'):
                st.markdown("### 🎭 Creative Poem")
                
                # Create styled container for poem
                poem_container = st.container()
                with poem_container:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #fff8e1;
                            border-left: 4px solid #ffc107;
                            padding: 20px;
                            border-radius: 8px;
                            margin: 15px 0;
                            font-family: 'Georgia', serif;
                            white-space: pre-line;
                            font-size: 1.05em;
                            line-height: 1.8;
                        ">
                            {output_data.get('poem')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Download and audio controls for poem
                poem_col1, poem_col2 = st.columns(2)
                
                with poem_col1:
                    if st.button("📥 Download Poem Text", key="download_poem"):
                        self.download_text_content(
                            output_data.get('poem', ''),
                            f"poem_{output_data.get('id', 'unknown')}.txt"
                        )
                
                with poem_col2:
                    # Look for poem audio file
                    poem_audio = self.find_audio_file(output_data, 'poem')
                    if poem_audio:
                        if st.button("🎵 Play Poem Audio", key="play_poem"):
                            st.session_state.current_playing_audio = poem_audio
                            st.rerun()
                
                st.markdown("")
            
            # Enhanced audio players section
            self.render_audio_players_section(output_data)
            
            # File information and downloads
            self.render_file_downloads_section(output_data)
                    
        except Exception as e:
            st.error(f"Error displaying interaction content: {str(e)}")
            if st.session_state.get('show_debug_info', False):
                st.exception(e)
    
    def render_audio_players_section(self, output_data):
        """Render enhanced audio players section with controls and download options."""
        try:
            st.markdown("### 🎵 Audio Content")
            
            # Initialize audio session state
            if 'current_playing_audio' not in st.session_state:
                st.session_state.current_playing_audio = None
            if 'audio_player_settings' not in st.session_state:
                st.session_state.audio_player_settings = {
                    'show_waveform': False,
                    'auto_play_next': False,
                    'loop_audio': False
                }
            
            audio_files = output_data.get('audio_files', [])
            
            if not audio_files:
                st.info("🎵 Audio files will be available after content generation with TTS processing")
                return
            
            # Audio player controls
            audio_controls_col1, audio_controls_col2, audio_controls_col3 = st.columns(3)
            
            with audio_controls_col1:
                show_waveform = st.checkbox(
                    "📊 Show Waveform", 
                    value=st.session_state.audio_player_settings['show_waveform'],
                    help="Display audio waveform visualization"
                )
                st.session_state.audio_player_settings['show_waveform'] = show_waveform
            
            with audio_controls_col2:
                auto_play = st.checkbox(
                    "▶️ Auto-play Next", 
                    value=st.session_state.audio_player_settings['auto_play_next'],
                    help="Automatically play next audio file"
                )
                st.session_state.audio_player_settings['auto_play_next'] = auto_play
            
            with audio_controls_col3:
                loop_audio = st.checkbox(
                    "🔄 Loop Audio", 
                    value=st.session_state.audio_player_settings['loop_audio'],
                    help="Loop current audio file"
                )
                st.session_state.audio_player_settings['loop_audio'] = loop_audio
            
            st.markdown("---")
            
            # Organize audio files by type
            audio_by_type = {}
            for audio_info in audio_files:
                audio_type = audio_info.get('type', 'unknown')
                if audio_type not in audio_by_type:
                    audio_by_type[audio_type] = []
                audio_by_type[audio_type].append(audio_info)
            
            # Display audio players by type
            for audio_type, audio_list in audio_by_type.items():
                self.render_audio_type_section(audio_type, audio_list, output_data)
            
            # Remix audio player (special handling)
            remix_audio = self.find_audio_file(output_data, 'remix')
            if remix_audio:
                self.render_remix_audio_player(remix_audio, output_data)
            
            # Bulk audio download
            if len(audio_files) > 1:
                st.markdown("---")
                if st.button("📥 Download All Audio Files", width="stretch"):
                    self.download_all_audio_files(audio_files, output_data)
                    
        except Exception as e:
            st.error(f"Error rendering audio players: {str(e)}")
    
    def render_audio_type_section(self, audio_type, audio_list, output_data):
        """Render audio player section for a specific audio type."""
        try:
            # Audio type icons and descriptions
            type_info = {
                'support': {'icon': '💝', 'title': 'Supportive Message Audio', 'color': '#28a745'},
                'poem': {'icon': '🎭', 'title': 'Poem Audio', 'color': '#ffc107'},
                'remix': {'icon': '🎵', 'title': 'Audio Remix', 'color': '#6f42c1'},
                'original': {'icon': '🎤', 'title': 'Original Audio', 'color': '#007bff'},
                'unknown': {'icon': '🔊', 'title': 'Audio Content', 'color': '#6c757d'}
            }
            
            info = type_info.get(audio_type, type_info['unknown'])
            
            # Skip remix here - it gets special handling
            if audio_type == 'remix':
                return
            
            st.markdown(f"#### {info['icon']} {info['title']}")
            
            for i, audio_info in enumerate(audio_list):
                audio_path = audio_info.get('path', '')
                duration = audio_info.get('duration', 0)
                
                if not audio_path:
                    continue
                
                # Create container for each audio file
                audio_container = st.container()
                with audio_container:
                    # Audio file info
                    audio_col1, audio_col2, audio_col3 = st.columns([2, 1, 1])
                    
                    with audio_col1:
                        # Try to display audio player
                        full_path = self.get_full_audio_path(audio_path)
                        if full_path and full_path.exists():
                            st.audio(str(full_path), format='audio/wav')
                        else:
                            st.warning(f"Audio file not found: {audio_path}")
                    
                    with audio_col2:
                        # Audio info
                        if duration > 0:
                            duration_str = f"{duration:.1f}s"
                        else:
                            duration_str = "Unknown"
                        
                        st.markdown(f"**Duration:** {duration_str}")
                        
                        # File size if available
                        if full_path and full_path.exists():
                            file_size_mb = full_path.stat().st_size / (1024 * 1024)
                            st.markdown(f"**Size:** {file_size_mb:.1f}MB")
                    
                    with audio_col3:
                        # Download button
                        if st.button(
                            f"📥 Download", 
                            key=f"download_{audio_type}_{i}",
                            help=f"Download {audio_type} audio file"
                        ):
                            self.download_audio_file(audio_info, output_data)
                
                # Waveform visualization (if enabled)
                if st.session_state.audio_player_settings.get('show_waveform', False):
                    self.render_audio_waveform(full_path, audio_type)
                
                st.markdown("---")
                
        except Exception as e:
            st.error(f"Error rendering {audio_type} audio section: {str(e)}")
    
    def render_remix_audio_player(self, remix_audio, output_data):
        """Render special remix audio player with background music controls."""
        try:
            st.markdown("#### 🎵 Audio Remix with Background Music")
            
            remix_path = remix_audio.get('path', '')
            if not remix_path:
                st.info("🎵 Remix audio will be available after audio processing with background music")
                return
            
            # Remix audio container with enhanced styling
            remix_container = st.container()
            with remix_container:
                st.markdown(
                    """
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px;
                        border-radius: 10px;
                        margin: 15px 0;
                        color: white;
                    ">
                        <h5 style="color: white; margin-bottom: 15px;">🎵 Enhanced Audio Experience</h5>
                        <p style="color: #f8f9fa; margin-bottom: 0;">
                            This remix combines your supportive content with carefully selected background music 
                            for a more immersive and calming experience.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Remix audio player
                full_path = self.get_full_audio_path(remix_path)
                if full_path and full_path.exists():
                    st.audio(str(full_path), format='audio/wav')
                    
                    # Remix controls
                    remix_col1, remix_col2, remix_col3 = st.columns(3)
                    
                    with remix_col1:
                        duration = remix_audio.get('duration', 0)
                        duration_str = f"{duration:.1f}s" if duration > 0 else "Unknown"
                        st.markdown(f"**🕐 Duration:** {duration_str}")
                    
                    with remix_col2:
                        # File size
                        file_size_mb = full_path.stat().st_size / (1024 * 1024)
                        st.markdown(f"**📊 Size:** {file_size_mb:.1f}MB")
                    
                    with remix_col3:
                        # Download remix
                        if st.button("📥 Download Remix", key="download_remix"):
                            self.download_audio_file(remix_audio, output_data)
                    
                    # Remix settings (if available in metadata)
                    remix_metadata = remix_audio.get('metadata', {})
                    if remix_metadata:
                        with st.expander("🎛️ Remix Settings"):
                            st.json(remix_metadata)
                
                else:
                    st.warning(f"Remix audio file not found: {remix_path}")
            
            st.markdown("---")
            
        except Exception as e:
            st.error(f"Error rendering remix audio player: {str(e)}")
    
    def render_file_downloads_section(self, output_data):
        """Render file downloads section with organized download options."""
        try:
            file_paths = output_data.get('file_paths', {})
            
            if not file_paths:
                return
            
            st.markdown("### 📁 File Downloads")
            
            # Organize files by type
            file_categories = {
                'Text Files': [],
                'Audio Files': [],
                'Image Files': [],
                'Other Files': []
            }
            
            for file_type, file_path in file_paths.items():
                if not file_path:
                    continue
                
                # Categorize files
                if file_type.endswith('.txt') or 'text' in file_type.lower():
                    file_categories['Text Files'].append((file_type, file_path))
                elif file_type.endswith(('.wav', '.mp3', '.ogg', '.m4a')) or 'audio' in file_type.lower():
                    file_categories['Audio Files'].append((file_type, file_path))
                elif file_type.endswith(('.png', '.jpg', '.jpeg', '.gif')) or 'image' in file_type.lower():
                    file_categories['Image Files'].append((file_type, file_path))
                else:
                    file_categories['Other Files'].append((file_type, file_path))
            
            # Display file categories
            for category, files in file_categories.items():
                if not files:
                    continue
                
                st.markdown(f"#### {category}")
                
                for file_type, file_path in files:
                    file_col1, file_col2, file_col3 = st.columns([2, 1, 1])
                    
                    with file_col1:
                        st.markdown(f"**{file_type}**")
                        st.markdown(f"`{file_path}`")
                    
                    with file_col2:
                        # File info
                        full_path = self.get_full_file_path(file_path)
                        if full_path and full_path.exists():
                            file_size = full_path.stat().st_size
                            if file_size < 1024:
                                size_str = f"{file_size} B"
                            elif file_size < 1024 * 1024:
                                size_str = f"{file_size / 1024:.1f} KB"
                            else:
                                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                            
                            st.markdown(f"**Size:** {size_str}")
                        else:
                            st.markdown("**Status:** Not found")
                    
                    with file_col3:
                        # Download button
                        if st.button(
                            "📥 Download", 
                            key=f"download_file_{file_type}",
                            help=f"Download {file_type}"
                        ):
                            self.download_file_by_path(file_path, file_type)
                
                st.markdown("---")
            
            # Bulk download option
            total_files = sum(len(files) for files in file_categories.values())
            if total_files > 1:
                if st.button("📦 Download All Files", width="stretch"):
                    self.download_all_interaction_files(output_data)
                    
        except Exception as e:
            st.error(f"Error rendering file downloads section: {str(e)}")
    
    def reload_current_interaction(self):
        """Reload the current interaction from storage."""
        try:
            if not st.session_state.selected_interaction:
                st.warning("No interaction selected to reload")
                return
            
            if not hasattr(self, 'storage_manager'):
                self.storage_manager = StorageManager()
            
            # Reload interaction from storage
            interaction = self.storage_manager.load_interaction(
                st.session_state.current_user.nickname,
                st.session_state.selected_interaction
            )
            
            if interaction:
                # Convert to output format
                output_data = {
                    'id': interaction.id,
                    'timestamp': interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'input_type': interaction.input_data.input_type.value if interaction.input_data else 'unknown',
                    'input_content': interaction.input_data.content if interaction.input_data else '',
                    'supportive_statement': interaction.generated_content.supportive_statement if interaction.generated_content else '',
                    'poem': interaction.generated_content.poem if interaction.generated_content else '',
                    'audio_files': [
                        {
                            'type': audio.metadata.get('type', 'unknown'),
                            'path': audio.file_path,
                            'duration': audio.duration
                        } for audio in interaction.audio_files
                    ],
                    'file_paths': interaction.file_paths
                }
                
                st.session_state.current_output = output_data
                st.success("Interaction reloaded successfully!")
                st.rerun()
            else:
                st.error("Could not reload interaction - it may have been deleted")
                
        except Exception as e:
            st.error(f"Error reloading interaction: {str(e)}")
    
    def render_input_area(self):
        """Render the input area at the bottom of the workspace."""
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        
        st.subheader("💬 Share Your Thoughts")
        
        # Input type selection with enhanced styling
        st.markdown("**Choose your input method:**")
        input_type_col1, input_type_col2, input_type_col3 = st.columns(3)
        
        with input_type_col1:
            text_selected = st.session_state.current_input_type == 'text'
            if st.button("📝 Text Input", width="stretch", 
                        type="primary" if text_selected else "secondary",
                        help="Type your thoughts and feelings"):
                st.session_state.current_input_type = 'text'
                st.rerun()
        
        with input_type_col2:
            audio_selected = st.session_state.current_input_type == 'audio'
            if st.button("🎤 Audio Upload", width="stretch",
                        type="primary" if audio_selected else "secondary",
                        help="Upload an audio file (WAV, MP3, OGG, M4A)"):
                st.session_state.current_input_type = 'audio'
                st.rerun()
        
        with input_type_col3:
            drawing_selected = st.session_state.current_input_type == 'drawing'
            if st.button("🎨 Drawing Canvas", width="stretch",
                        type="primary" if drawing_selected else "secondary",
                        help="Create a drawing to express yourself"):
                st.session_state.current_input_type = 'drawing'
                st.rerun()
        
        st.markdown("---")
        
        # Render input interface based on selected type
        if st.session_state.current_input_type == 'text':
            self.render_text_input()
        elif st.session_state.current_input_type == 'audio':
            self.render_audio_input()
        elif st.session_state.current_input_type == 'drawing':
            self.render_drawing_input()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_text_input(self):
        """Render enhanced text input interface with validation."""
        st.markdown("**💭 Express yourself through text:**")
        
        # Text area for input with enhanced features
        user_input = st.text_area(
            "Share your thoughts, feelings, or questions...",
            value=st.session_state.input_text,
            height=150,
            placeholder="What's on your mind today? Share your thoughts, feelings, experiences, or ask questions...",
            label_visibility="collapsed",
            help="Type anything that's on your mind. Your AI companion will respond with supportive messages and creative poems."
        )
        
        # Update session state
        st.session_state.input_text = user_input
        
        # Input validation and character count
        char_count = len(user_input.strip())
        max_chars = 2000  # Reasonable limit for text input
        
        col_info, col_count = st.columns([3, 1])
        with col_info:
            if char_count == 0:
                st.info("💡 Tip: Share your thoughts, feelings, or ask questions for personalized support.")
            elif char_count < 10:
                st.warning("⚠️ Please write at least a few words for better AI responses.")
            elif char_count > max_chars:
                st.error(f"❌ Text is too long. Please keep it under {max_chars} characters.")
            else:
                st.success("✅ Ready to generate supportive content!")
        
        with col_count:
            color = "red" if char_count > max_chars else "green" if char_count >= 10 else "orange"
            st.markdown(f"<div style='text-align: right; color: {color};'>{char_count}/{max_chars}</div>", 
                       unsafe_allow_html=True)
        
        # Submit button with enhanced validation
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            is_valid = 10 <= char_count <= max_chars
            button_text = "✨ Generate Support" if is_valid else "✨ Generate"
            
            if st.button(button_text, type="primary", width="stretch", 
                        disabled=not is_valid,
                        help="Generate supportive messages and poems based on your input"):
                self.handle_text_input_submission(user_input)
        
        # Additional text input options
        if user_input.strip():
            st.markdown("---")
            col_clear, col_example = st.columns(2)
            
            with col_clear:
                if st.button("🗑️ Clear Text", width="stretch"):
                    st.session_state.input_text = ""
                    st.rerun()
            
            with col_example:
                if st.button("💡 Show Examples", width="stretch"):
                    self.show_text_input_examples()
    
    def render_audio_input(self):
        """Render enhanced audio input interface with validation."""
        st.markdown("**🎤 Share through audio:**")
        
        # Audio file uploader with enhanced validation
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'ogg', 'm4a', 'flac', 'aac'],
            label_visibility="collapsed",
            help="Upload audio files in WAV, MP3, OGG, M4A, FLAC, or AAC format. Maximum file size: 25MB"
        )
        
        if uploaded_file:
            # File validation
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            max_size_mb = 25
            
            # Display file information
            col_info, col_size = st.columns([3, 1])
            with col_info:
                st.info(f"📁 **{uploaded_file.name}** ({uploaded_file.type})")
            with col_size:
                size_color = "red" if file_size_mb > max_size_mb else "green"
                st.markdown(f"<div style='text-align: right; color: {size_color};'>{file_size_mb:.1f}MB</div>", 
                           unsafe_allow_html=True)
            
            # Audio player
            st.audio(uploaded_file)
            
            # Validation messages
            if file_size_mb > max_size_mb:
                st.error(f"❌ File too large. Please upload files smaller than {max_size_mb}MB.")
            elif file_size_mb < 0.01:  # Less than 10KB
                st.warning("⚠️ File seems very small. Please ensure it contains audio content.")
            else:
                st.success("✅ Audio file ready for processing!")
                
                # Transcription info
                st.info("🔤 Audio will be optionally transcribed using Whisper for better AI understanding.")
            
            # Submit button
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                is_valid = 0.01 <= file_size_mb <= max_size_mb
                if st.button("🎵 Process Audio", type="primary", width="stretch", 
                            disabled=not is_valid,
                            help="Process audio file and generate supportive content"):
                    self.handle_audio_input_submission(uploaded_file)
        
        else:
            # Instructions when no file is uploaded
            st.markdown("""
            **📋 Audio Input Instructions:**
            - Upload audio files in common formats (WAV, MP3, OGG, M4A, FLAC, AAC)
            - Maximum file size: 25MB
            - Audio will be optionally transcribed for better AI understanding
            - Speak naturally about your thoughts, feelings, or questions
            """)
        
        # Future features info
        st.markdown("---")
        st.info("🎤 **Coming Soon:** Live recording directly in the browser!")
    
    def render_drawing_input(self):
        """Render drawing input interface with canvas."""
        st.markdown("**🎨 Express yourself through art:**")
        
        # Initialize drawing session state
        if 'canvas_data' not in st.session_state:
            st.session_state.canvas_data = None
        if 'canvas_key' not in st.session_state:
            st.session_state.canvas_key = 0
        
        # Try to import streamlit-drawable-canvas
        try:
            from streamlit_drawable_canvas import st_canvas
            canvas_available = True
        except ImportError:
            canvas_available = False
        
        if canvas_available:
            # Canvas configuration
            col_config1, col_config2, col_config3 = st.columns(3)
            
            with col_config1:
                stroke_width = st.slider("Brush Size", 1, 25, 3)
                stroke_color = st.color_picker("Brush Color", "#000000")
            
            with col_config2:
                bg_color = st.color_picker("Background", "#FFFFFF")
                drawing_mode = st.selectbox("Tool", ["freedraw", "line", "rect", "circle"])
            
            with col_config3:
                canvas_width = st.slider("Canvas Width", 200, 800, 400)
                canvas_height = st.slider("Canvas Height", 200, 600, 400)
            
            # Drawing canvas
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_color=bg_color,
                background_image=None,
                update_streamlit=True,
                width=canvas_width,
                height=canvas_height,
                drawing_mode=drawing_mode,
                point_display_radius=0,
                key=f"canvas_{st.session_state.canvas_key}",
            )
            
            # Store canvas data
            if canvas_result.image_data is not None:
                st.session_state.canvas_data = canvas_result
                
                # Show canvas info
                if canvas_result.json_data is not None:
                    objects = canvas_result.json_data.get("objects", [])
                    if objects:
                        st.success(f"✅ Drawing ready! ({len(objects)} elements drawn)")
                    else:
                        st.info("💡 Start drawing on the canvas above to express your thoughts visually.")
            
            # Canvas controls
            col_clear, col_process = st.columns(2)
            
            with col_clear:
                if st.button("🗑️ Clear Canvas", width="stretch"):
                    st.session_state.canvas_key += 1
                    st.session_state.canvas_data = None
                    st.rerun()
            
            with col_process:
                has_drawing = (st.session_state.canvas_data is not None and 
                             st.session_state.canvas_data.json_data is not None and
                             len(st.session_state.canvas_data.json_data.get("objects", [])) > 0)
                
                if st.button("🎨 Process Drawing", type="primary", width="stretch", 
                            disabled=not has_drawing,
                            help="Generate supportive content based on your drawing"):
                    self.handle_drawing_input_submission(st.session_state.canvas_data)
        
        else:
            # Fallback when streamlit-drawable-canvas is not available
            st.warning("🎨 **Drawing Canvas Not Available**")
            st.markdown("""
            The drawing canvas requires the `streamlit-drawable-canvas` package.
            
            **To enable drawing functionality:**
            1. Install the package: `pip install streamlit-drawable-canvas`
            2. Restart the application
            
            **Alternative options:**
            - Upload a hand-drawn image using the file uploader below
            - Use the text or audio input methods instead
            """)
            
            # File uploader as alternative
            st.markdown("**📁 Upload a drawing instead:**")
            uploaded_image = st.file_uploader(
                "Choose an image file",
                type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
                label_visibility="collapsed",
                help="Upload a drawing or sketch in PNG, JPG, JPEG, GIF, or BMP format"
            )
            
            if uploaded_image:
                # Display uploaded image
                st.image(uploaded_image, caption=f"Uploaded: {uploaded_image.name}", use_column_width=True)
                
                # File validation
                file_size_mb = len(uploaded_image.getvalue()) / (1024 * 1024)
                max_size_mb = 10
                
                if file_size_mb > max_size_mb:
                    st.error(f"❌ Image too large. Please upload files smaller than {max_size_mb}MB.")
                else:
                    st.success("✅ Image ready for processing!")
                    
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col2:
                        if st.button("🖼️ Process Image", type="primary", width="stretch",
                                    help="Generate supportive content based on your uploaded image"):
                            self.handle_image_upload_submission(uploaded_image)
        
        # Drawing tips
        st.markdown("---")
        st.info("""
        **🎨 Drawing Tips:**
        - Express your emotions through colors and shapes
        - Don't worry about artistic skill - it's about expression
        - Abstract drawings are perfectly fine
        - Your AI companion will interpret your visual expression
        """)
    
    def render_debug_section(self):
        """Render collapsible debug information section."""
        if st.checkbox("🔧 Show Debug Info", value=st.session_state.show_debug_info):
            st.session_state.show_debug_info = True
            
            st.subheader("Debug Information")
            
            debug_info = {
                "Authentication": {
                    "authenticated": st.session_state.authenticated,
                    "user_nickname": st.session_state.current_user.nickname if st.session_state.current_user else None,
                    "session_active": st.session_state.session_token is not None
                },
                "Workspace State": {
                    "workspace_view": st.session_state.workspace_view,
                    "selected_interaction": st.session_state.selected_interaction,
                    "current_input_type": st.session_state.current_input_type,
                    "has_current_output": st.session_state.current_output is not None
                },
                "Input State": {
                    "input_text_length": len(st.session_state.input_text),
                    "input_text_preview": st.session_state.input_text[:50] + "..." if len(st.session_state.input_text) > 50 else st.session_state.input_text
                }
            }
            
            st.json(debug_info)
        else:
            st.session_state.show_debug_info = False
    
    def get_user_history_preview(self, limit: int = 50):
        """Get a preview of user interaction history using cached session data for better performance."""
        try:
            if not st.session_state.current_user:
                return []
            
            # Try to get cached history from session manager first
            try:
                cached_history = self.session_manager.get_cached_history(
                    st.session_state.current_user, 
                    limit=limit
                )
                
                if cached_history:
                    # Convert cached format to UI format if needed
                    history_items = []
                    for item in cached_history:
                        # Check if item is already in UI format
                        if 'preview' in item and 'interaction_obj' in item:
                            history_items.append(item)
                        else:
                            # Convert from cache format to UI format
                            ui_item = {
                                'id': item.get('id', ''),
                                'timestamp': item.get('timestamp', ''),
                                'input_type': item.get('input_type', 'unknown'),
                                'preview': item.get('preview', 'Untitled interaction'),
                                'supportive_statement': item.get('supportive_statement', ''),
                                'poem': item.get('poem', ''),
                                'interaction_obj': item.get('interaction_obj')
                            }
                            history_items.append(ui_item)
                    
                    return history_items
                    
            except Exception as cache_error:
                self.logger.logger.warning(f"Failed to get cached history: {cache_error}")
            
            # Fallback to direct storage access
            # Initialize storage manager if not already done
            if not hasattr(self, 'storage_manager'):
                self.storage_manager = StorageManager()
            
            # Load user's interaction history
            interactions = self.storage_manager.load_user_history(st.session_state.current_user)
            
            # Apply limit
            if limit:
                interactions = interactions[:limit]
            
            # Convert to preview format for UI
            history_items = []
            for interaction in interactions:
                # Create preview text from input content
                preview_text = "Untitled"
                if interaction.input_data and interaction.input_data.content:
                    content = interaction.input_data.content.strip()
                    # Truncate to first 50 characters for preview
                    preview_text = content[:50] + "..." if len(content) > 50 else content
                
                # Format timestamp
                timestamp_str = interaction.timestamp.strftime("%Y-%m-%d %H:%M")
                
                history_item = {
                    'id': interaction.id,
                    'preview': preview_text,
                    'timestamp': timestamp_str,
                    'input_type': interaction.input_data.input_type.value if interaction.input_data else 'unknown',
                    'supportive_statement': interaction.generated_content.supportive_statement if interaction.generated_content else '',
                    'poem': interaction.generated_content.poem if interaction.generated_content else '',
                    'interaction_obj': interaction  # Store full object for detailed view
                }
                history_items.append(history_item)
            
            return history_items
            
        except Exception as e:
            st.error(f"Error loading history: {str(e)}")
            return []
    
    def handle_text_input_submission(self, user_input: str):
        """Handle text input submission with complete processing pipeline and defensive error handling."""
        try:
            # Clear any previous notifications for this session
            if 'processing_notifications' not in st.session_state:
                st.session_state.processing_notifications = []
            # Clear previous messages
            self.clear_messages()
            
            if not user_input.strip():
                self.show_error("Please enter some text before submitting.")
                return
            
            # Show processing message
            preview = user_input[:50] + ('...' if len(user_input) > 50 else '')
            self.show_success(f"Processing your input: '{preview}'")
            
            # Process through complete pipeline
            interaction = self.process_complete_pipeline(
                user_input.strip(),
                input_type='text',
                metadata={"source": "streamlit_ui", "timestamp": datetime.now().isoformat()}
            )
            
            if interaction:
                # Display the generated content
                self.display_generated_interaction(interaction)
                
                # Clear input
                st.session_state.input_text = ""
                st.rerun()
            else:
                self.show_error("Failed to process your input. Please try again.")
            
        except Exception as e:
            self.show_error(f"Error processing text input: {str(e)}")
            # Show detailed error for debugging
            if st.session_state.show_debug_info:
                st.exception(e)
    
    def handle_audio_input_submission(self, audio_file):
        """Handle audio input submission with complete processing pipeline."""
        try:
            # Clear previous messages
            self.clear_messages()
            
            # Show processing message
            file_size_mb = len(audio_file.getvalue()) / (1024 * 1024)
            self.show_success(f"Processing audio file: {audio_file.name} ({file_size_mb:.1f}MB)")
            
            # Get audio data
            audio_data = audio_file.getvalue()
            
            # Process through complete pipeline
            interaction = self.process_complete_pipeline(
                audio_data,
                input_type='audio',
                metadata={
                    "source": "streamlit_ui", 
                    "timestamp": datetime.now().isoformat(),
                    "filename": audio_file.name,
                    "file_type": audio_file.type,
                    "file_size_mb": file_size_mb
                }
            )
            
            if interaction:
                # Display the generated content
                self.display_generated_interaction(interaction)
                st.rerun()
            else:
                self.show_error("Failed to process your audio. Please try again.")
            
        except Exception as e:
            self.show_error(f"Error processing audio input: {str(e)}")
            # Show detailed error for debugging
            if st.session_state.show_debug_info:
                st.exception(e)
    
    def show_text_input_examples(self):
        """Show example text inputs to help users."""
        st.markdown("**💡 Example prompts to get you started:**")
        
        examples = [
            "I'm feeling overwhelmed with work and need some encouragement",
            "I had a great day today and want to share my happiness",
            "I'm worried about an upcoming presentation and feeling anxious",
            "I accomplished something I'm proud of and want to celebrate",
            "I'm going through a difficult time and need some support",
            "I'm feeling grateful for the people in my life",
            "I'm struggling with self-doubt and need motivation",
            "I want to reflect on my personal growth journey"
        ]
        
        for i, example in enumerate(examples):
            if st.button(f"📝 {example}", key=f"example_{i}", width="stretch"):
                st.session_state.input_text = example
                st.rerun()
    
    def handle_drawing_input_submission(self, canvas_data):
        """Handle drawing input submission with complete processing pipeline."""
        try:
            # Clear previous messages
            self.clear_messages()
            
            if not canvas_data or canvas_data.image_data is None:
                self.show_error("No drawing data found. Please create a drawing first.")
                return
            
            # Show processing message
            objects_count = len(canvas_data.json_data.get("objects", [])) if canvas_data.json_data else 0
            self.show_success(f"Processing your drawing with {objects_count} elements...")
            
            # Prepare canvas data for processing
            canvas_dict = {
                "width": canvas_data.image_data.shape[1] if canvas_data.image_data is not None else 400,
                "height": canvas_data.image_data.shape[0] if canvas_data.image_data is not None else 400,
                "strokes": canvas_data.json_data.get("objects", []) if canvas_data.json_data else [],
                "background_color": "white"
            }
            
            # Process through complete pipeline
            interaction = self.process_complete_pipeline(
                canvas_dict,
                input_type='drawing',
                metadata={
                    "source": "streamlit_ui",
                    "timestamp": datetime.now().isoformat(),
                    "canvas_objects": objects_count,
                    "canvas_dimensions": f"{canvas_dict['width']}x{canvas_dict['height']}"
                }
            )
            
            if interaction:
                # Display the generated content
                self.display_generated_interaction(interaction)
                st.rerun()
            else:
                self.show_error("Failed to process your drawing. Please try again.")
            
        except Exception as e:
            self.show_error(f"Error processing drawing input: {str(e)}")
            # Show detailed error for debugging
            if st.session_state.show_debug_info:
                st.exception(e)
    
    def handle_image_upload_submission(self, uploaded_image):
        """Handle uploaded image submission with complete processing pipeline."""
        try:
            # Clear previous messages
            self.clear_messages()
            
            # Show processing message
            file_size_mb = len(uploaded_image.getvalue()) / (1024 * 1024)
            self.show_success(f"Processing uploaded image: {uploaded_image.name} ({file_size_mb:.1f}MB)")
            
            # Convert uploaded file to base64 for processing
            import base64
            image_data = uploaded_image.getvalue()
            base64_data = base64.b64encode(image_data).decode()
            
            # Add data URL prefix based on file type
            mime_type = uploaded_image.type or "image/png"
            base64_with_prefix = f"data:{mime_type};base64,{base64_data}"
            
            # Process through complete pipeline
            interaction = self.process_complete_pipeline(
                base64_with_prefix,
                input_type='drawing',
                metadata={
                    "source": "streamlit_ui",
                    "timestamp": datetime.now().isoformat(),
                    "upload_method": "file_upload",
                    "original_filename": uploaded_image.name,
                    "file_type": uploaded_image.type,
                    "file_size_mb": file_size_mb
                }
            )
            
            if interaction:
                # Display the generated content
                self.display_generated_interaction(interaction)
                st.rerun()
            else:
                self.show_error("Failed to process your image. Please try again.")
            
        except Exception as e:
            self.show_error(f"Error processing uploaded image: {str(e)}")
            # Show detailed error for debugging
            if st.session_state.show_debug_info:
                st.exception(e)
    
    def process_complete_pipeline(self, input_data, input_type='text', metadata=None):
        """
        Process input through the complete pipeline: input → content generation → audio processing → storage.
        
        Args:
            input_data: Raw input data (text, audio bytes, or canvas data)
            input_type: Type of input ('text', 'audio', 'drawing')
            metadata: Optional metadata dictionary
            
        Returns:
            Interaction object if successful, None if failed
        """
        processed_input = None
        generated_content = None
        audio_files = []
        
        try:
            # Validate inputs
            if not input_data:
                raise ValueError("No input data provided")
            
            if input_type not in ['text', 'audio', 'drawing']:
                raise ValueError(f"Unsupported input type: {input_type}")
            
            metadata = metadata or {}
            
            # Create progress tracker for the entire process
            total_steps = 4  # Input processing, content generation, audio processing, saving
            progress = ProgressTracker(total_steps, "Processing your request")
            
            # Step 1: Process input with error handling
            progress.update(1, "Processing your input...")
            with LoadingIndicator("🔄 Processing your input...", show_spinner=True):
                try:
                    if input_type == 'text':
                        if not isinstance(input_data, str) or not input_data.strip():
                            raise ValueError("Text input cannot be empty")
                        processed_input = self.input_processor.process_text_input(input_data, metadata)
                    elif input_type == 'audio':
                        if not input_data or len(input_data) == 0:
                            raise ValueError("Audio data cannot be empty")
                        processed_input = self.input_processor.process_audio_input(input_data, metadata.get('filename'), metadata)
                    elif input_type == 'drawing':
                        processed_input = self.input_processor.process_drawing_input(input_data, metadata)
                    
                    if not processed_input or not processed_input.content:
                        raise RuntimeError("Input processing failed - no content generated")
                    
                    content_length = len(processed_input.content)
                    st.success(f"✅ Input processed successfully ({content_length} characters)")
                    
                except Exception as input_error:
                    progress.complete(f"Error: {str(input_error)}")
                    self.logger.error(f"Input processing failed: {input_error}")
                    raise RuntimeError(f"Input processing failed: {str(input_error)}")
            
            # Step 2: Generate content with fallback handling
            progress.update(2, "Generating supportive content...")
            with LoadingIndicator("🤖 Generating supportive content...", show_spinner=True):
                try:
                    generated_content = self.content_generator.generate_support_and_poem(processed_input)
                    
                    if not generated_content:
                        raise RuntimeError("Content generation returned None")
                    
                    if not generated_content.supportive_statement and not generated_content.poem:
                        raise RuntimeError("Content generation produced empty results")
                    
                    generator_name = generated_content.generation_metadata.get('generator', 'unknown')
                    st.success(f"✅ Content generated using {generator_name}")
                    
                    # Log generation details
                    self.logger.info(f"Content generated: support={len(generated_content.supportive_statement)} chars, poem={len(generated_content.poem)} chars")
                    
                except Exception as content_error:
                    progress.complete(f"Error: {str(content_error)}")
                    self.logger.error(f"Content generation failed: {content_error}")
                    raise RuntimeError(f"Content generation failed: {str(content_error)}")
            
            # Step 3: Process audio (TTS and remixing) with graceful degradation
            progress.update(3, "Converting to speech...")
            with LoadingIndicator("🎵 Converting to speech...", show_spinner=True):
                try:
                    # Check if audio processing is available
                    audio_capabilities = self.audio_manager.is_audio_processing_available()
                    
                    if not audio_capabilities.get('any_tts', False):
                        st.warning("⚠️ No TTS engines available, skipping audio generation")
                    else:
                        # Generate speech for supportive statement
                        if generated_content.supportive_statement:
                            try:
                                support_audio_result = self.audio_manager.process_text_to_audio(
                                    generated_content.supportive_statement,
                                    voice_settings={'rate': 150, 'volume': 0.8},
                                    create_remix=False
                                )
                                
                                if support_audio_result.get('speech'):
                                    support_audio = support_audio_result['speech']
                                    support_audio.metadata['type'] = 'support'
                                    audio_files.append(support_audio)
                                    self.logger.info("Support audio generated successfully")
                            except Exception as support_audio_error:
                                self.logger.warning(f"Support audio generation failed: {support_audio_error}")
                        
                        # Generate speech for poem
                        if generated_content.poem:
                            try:
                                poem_audio_result = self.audio_manager.process_text_to_audio(
                                    generated_content.poem,
                                    voice_settings={'rate': 140, 'volume': 0.8},
                                    create_remix=False
                                )
                                
                                if poem_audio_result.get('speech'):
                                    poem_audio = poem_audio_result['speech']
                                    poem_audio.metadata['type'] = 'poem'
                                    audio_files.append(poem_audio)
                                    self.logger.info("Poem audio generated successfully")
                            except Exception as poem_audio_error:
                                self.logger.warning(f"Poem audio generation failed: {poem_audio_error}")
                        
                        # Try to create remix if background music is available
                        if audio_files and audio_capabilities.get('pydub_mixing', False):
                            try:
                                from audio_processor import get_default_background_music_path
                                bg_music_path = get_default_background_music_path()
                                
                                if bg_music_path and generated_content.supportive_statement:
                                    remix_result = self.audio_manager.process_text_to_audio(
                                        generated_content.supportive_statement,
                                        voice_settings={'rate': 150, 'volume': 0.8},
                                        background_music_path=bg_music_path,
                                        create_remix=True
                                    )
                                    
                                    if remix_result.get('remix'):
                                        remix_audio = remix_result['remix']
                                        remix_audio.metadata['type'] = 'remix'
                                        audio_files.append(remix_audio)
                                        self.logger.info("Remix audio generated successfully")
                            except Exception as remix_error:
                                self.logger.warning(f"Remix creation failed: {remix_error}")
                    
                    audio_count = len(audio_files)
                    if audio_count > 0:
                        st.success(f"✅ Generated {audio_count} audio file(s)")
                    else:
                        st.info("ℹ️ Continuing with text-only content")
                        
                except Exception as audio_error:
                    self.logger.error(f"Audio processing failed: {audio_error}")
                    st.warning("⚠️ Audio processing failed, continuing with text only")
            
            # Step 4: Create interaction object with validation
            try:
                interaction = Interaction(
                    input_data=processed_input,
                    generated_content=generated_content,
                    audio_files=audio_files
                )
                
                # Validate interaction object
                if not interaction.input_data or not interaction.generated_content:
                    raise RuntimeError("Invalid interaction object created")
                
                # Debug: Log successful interaction creation
                self.logger.info(f"✅ Interaction object created successfully")
                self.logger.info(f"   - Input: {interaction.input_data.content[:50] if interaction.input_data else 'None'}...")
                self.logger.info(f"   - Support: {interaction.generated_content.supportive_statement[:50] if interaction.generated_content else 'None'}...")
                self.logger.info(f"   - Poem: {interaction.generated_content.poem[:50] if interaction.generated_content else 'None'}...")
                self.logger.info(f"   - Audio files: {len(audio_files)}")
                
            except Exception as interaction_error:
                self.logger.error(f"Interaction creation failed: {interaction_error}")
                raise RuntimeError(f"Failed to create interaction: {str(interaction_error)}")
            
            # Step 4: Save to storage and session with error handling
            progress.update(4, "Saving interaction...")
            with LoadingIndicator("💾 Saving interaction...", show_spinner=True):
                try:
                    if not st.session_state.current_user:
                        raise RuntimeError("No authenticated user found")
                    
                    # Debug logging before save
                    self.logger.info(f"Attempting to save interaction for user: {st.session_state.current_user.nickname}")
                    self.logger.info(f"Interaction has content: {bool(interaction.generated_content)}")
                    self.logger.info(f"Interaction has input: {bool(interaction.input_data)}")
                    
                    interaction_id = self.storage_manager.save_interaction(
                        st.session_state.current_user,
                        interaction
                    )
                    
                    self.logger.info(f"Save interaction returned ID: {interaction_id}")
                    
                    if interaction_id:
                        interaction.id = interaction_id
                        
                        # Automatically save to session management system
                        try:
                            session_saved = self.session_manager.save_interaction_to_session(interaction)
                            if session_saved:
                                st.success(f"✅ Interaction saved and added to history (ID: {interaction_id[:8]}...)")
                                self.logger.info(f"Interaction saved with ID: {interaction_id} and added to session")
                            else:
                                st.success(f"✅ Interaction saved (ID: {interaction_id[:8]}...)")
                                self.logger.warning("Interaction saved but session update failed")
                        except Exception as session_error:
                            self.logger.error(f"Session save failed: {session_error}")
                            st.success(f"✅ Interaction saved (ID: {interaction_id[:8]}...)")
                        
                        # Invalidate history cache to force refresh
                        cache_key = f"user_history_{st.session_state.current_user.nickname}"
                        self.performance_optimizer.cache.invalidate(cache_key)
                        
                    else:
                        st.warning("⚠️ Failed to save interaction, but content is available in session")
                        self.logger.warning("Storage save failed but interaction is available")
                        
                except Exception as storage_error:
                    progress.complete(f"Error saving: {str(storage_error)}")
                    self.logger.error(f"Storage failed: {storage_error}")
                    st.warning("⚠️ Failed to save interaction, but content is available in session")
            
            # Complete the progress tracker
            progress.complete("Processing complete!")
            
            # CRITICAL: Always display content even if storage fails
            if interaction and interaction.generated_content:
                self.logger.info("🎯 Forcing content display regardless of storage status")
                
                # Create display data
                display_data = {
                    'id': interaction.id or 'temp_' + str(int(time.time())),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'input_type': interaction.input_data.input_type.value if interaction.input_data else 'text',
                    'input_content': interaction.input_data.content if interaction.input_data else '',
                    'supportive_statement': interaction.generated_content.supportive_statement,
                    'poem': interaction.generated_content.poem,
                    'audio_files': [
                        {
                            'type': audio.metadata.get('type', 'unknown'),
                            'path': audio.file_path,
                            'duration': audio.duration
                        } for audio in audio_files
                    ],
                    'file_paths': getattr(interaction, 'file_paths', {})
                }
                
                # Force set current output
                st.session_state.current_output = display_data
                st.session_state.workspace_view = 'view_interaction'
                
                self.logger.info("✅ Content display data set in session state")
            
            # Force memory cleanup after processing
            self.performance_optimizer.optimize_memory()
            
            return interaction
            
        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {e}")
            
            # Provide user-friendly error messages based on error type
            if "Input processing failed" in str(e):
                self.show_error("❌ Unable to process your input. Please check the format and try again.")
            elif "Content generation failed" in str(e):
                self.show_error("❌ Unable to generate supportive content. Please try again or check your internet connection.")
            elif "No authenticated user" in str(e):
                self.show_error("❌ Authentication error. Please log in again.")
            else:
                self.show_error(f"❌ Processing failed: {str(e)}")
            
            # Show detailed error for debugging
            if st.session_state.get('show_debug_info', False):
                st.exception(e)
            
            # Cleanup any partial resources
            try:
                if audio_files:
                    self.audio_manager.cleanup_temp_files(audio_files)
            except Exception as cleanup_error:
                self.logger.warning(f"Cleanup failed: {cleanup_error}")
            
            return None
    
    def display_generated_interaction(self, interaction):
        """
        Display the results of a generated interaction in the output area.
        
        Args:
            interaction: Interaction object with generated content
        """
        try:
            # Convert interaction to output format for display
            output_data = {
                'id': interaction.id,
                'timestamp': interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S") if interaction.timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'input_type': interaction.input_data.input_type.value if interaction.input_data else 'unknown',
                'input_content': interaction.input_data.content if interaction.input_data else '',
                'supportive_statement': interaction.generated_content.supportive_statement if interaction.generated_content else '',
                'poem': interaction.generated_content.poem if interaction.generated_content else '',
                'audio_files': [
                    {
                        'type': audio.metadata.get('type', 'unknown'),
                        'path': audio.file_path,
                        'duration': audio.duration
                    } for audio in interaction.audio_files
                ],
                'file_paths': interaction.file_paths if hasattr(interaction, 'file_paths') else {}
            }
            
            # Set current output and switch to view mode
            st.session_state.current_output = output_data
            st.session_state.workspace_view = 'view_interaction'
            st.session_state.selected_interaction = interaction.id
            
            # Show success message
            self.show_success("🎉 Your supportive content is ready! Check the output area above.")
            
        except Exception as e:
            self.logger.error(f"Error displaying interaction: {e}")
            self.show_error(f"Error displaying results: {str(e)}")
    
    def find_audio_file(self, output_data, audio_type):
        """Find audio file of specific type in output data."""
        try:
            audio_files = output_data.get('audio_files', [])
            for audio_info in audio_files:
                if audio_info.get('type') == audio_type:
                    return audio_info
            return None
        except Exception:
            return None
    
    def get_full_audio_path(self, audio_path):
        """Get full path for audio file."""
        try:
            if not hasattr(self, 'storage_manager'):
                self.storage_manager = StorageManager()
            
            # Handle both absolute and relative paths
            if Path(audio_path).is_absolute():
                return Path(audio_path)
            else:
                return self.storage_manager.base_path / audio_path
        except Exception:
            return None
    
    def get_full_file_path(self, file_path):
        """Get full path for any file."""
        try:
            if not hasattr(self, 'storage_manager'):
                self.storage_manager = StorageManager()
            
            # Handle both absolute and relative paths
            if Path(file_path).is_absolute():
                return Path(file_path)
            else:
                return self.storage_manager.base_path / file_path
        except Exception:
            return None
    
    def download_text_content(self, content, filename):
        """Provide download link for text content."""
        try:
            # Create download button using Streamlit's download_button
            st.download_button(
                label=f"📥 {filename}",
                data=content,
                file_name=filename,
                mime="text/plain",
                help=f"Download {filename}"
            )
        except Exception as e:
            st.error(f"Error creating download for {filename}: {str(e)}")
    
    def download_audio_file(self, audio_info, output_data):
        """Provide download link for audio file."""
        try:
            audio_path = audio_info.get('path', '')
            if not audio_path:
                st.error("Audio file path not found")
                return
            
            full_path = self.get_full_audio_path(audio_path)
            if not full_path or not full_path.exists():
                st.error(f"Audio file not found: {audio_path}")
                return
            
            # Read audio file
            with open(full_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Determine filename and mime type
            filename = full_path.name
            if filename.endswith('.wav'):
                mime_type = 'audio/wav'
            elif filename.endswith('.mp3'):
                mime_type = 'audio/mpeg'
            elif filename.endswith('.ogg'):
                mime_type = 'audio/ogg'
            else:
                mime_type = 'audio/wav'  # Default
            
            # Create download button
            st.download_button(
                label=f"📥 {filename}",
                data=audio_data,
                file_name=filename,
                mime=mime_type,
                help=f"Download {filename}"
            )
            
        except Exception as e:
            st.error(f"Error downloading audio file: {str(e)}")
    
    def download_file_by_path(self, file_path, file_type):
        """Download file by path."""
        try:
            full_path = self.get_full_file_path(file_path)
            if not full_path or not full_path.exists():
                st.error(f"File not found: {file_path}")
                return
            
            # Determine mime type
            suffix = full_path.suffix.lower()
            mime_types = {
                '.txt': 'text/plain',
                '.json': 'application/json',
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.ogg': 'audio/ogg',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif'
            }
            mime_type = mime_types.get(suffix, 'application/octet-stream')
            
            # Read file
            if mime_type.startswith('text/') or mime_type == 'application/json':
                with open(full_path, 'r', encoding='utf-8') as f:
                    file_data = f.read()
            else:
                with open(full_path, 'rb') as f:
                    file_data = f.read()
            
            # Create download button
            st.download_button(
                label=f"📥 {full_path.name}",
                data=file_data,
                file_name=full_path.name,
                mime=mime_type,
                help=f"Download {file_type}"
            )
            
        except Exception as e:
            st.error(f"Error downloading file: {str(e)}")
    
    def download_interaction_content(self, output_data):
        """Download all content from an interaction as a ZIP file."""
        try:
            import zipfile
            import io
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add text content
                if output_data.get('input_content'):
                    zip_file.writestr(
                        f"input_{output_data.get('id', 'unknown')}.txt",
                        output_data.get('input_content')
                    )
                
                if output_data.get('supportive_statement'):
                    zip_file.writestr(
                        f"support_{output_data.get('id', 'unknown')}.txt",
                        output_data.get('supportive_statement')
                    )
                
                if output_data.get('poem'):
                    zip_file.writestr(
                        f"poem_{output_data.get('id', 'unknown')}.txt",
                        output_data.get('poem')
                    )
                
                # Add audio files
                audio_files = output_data.get('audio_files', [])
                for audio_info in audio_files:
                    audio_path = audio_info.get('path', '')
                    if audio_path:
                        full_path = self.get_full_audio_path(audio_path)
                        if full_path and full_path.exists():
                            zip_file.write(full_path, full_path.name)
                
                # Add other files
                file_paths = output_data.get('file_paths', {})
                for file_type, file_path in file_paths.items():
                    if file_path:
                        full_path = self.get_full_file_path(file_path)
                        if full_path and full_path.exists():
                            zip_file.write(full_path, full_path.name)
            
            zip_buffer.seek(0)
            
            # Create download button for ZIP
            interaction_id = output_data.get('id', 'unknown')
            zip_filename = f"echoverse_interaction_{interaction_id}.zip"
            
            st.download_button(
                label="📦 Download Complete Interaction",
                data=zip_buffer.getvalue(),
                file_name=zip_filename,
                mime="application/zip",
                help="Download all content from this interaction as a ZIP file"
            )
            
        except Exception as e:
            st.error(f"Error creating interaction download: {str(e)}")
    
    def download_all_audio_files(self, audio_files, output_data):
        """Download all audio files as a ZIP."""
        try:
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for audio_info in audio_files:
                    audio_path = audio_info.get('path', '')
                    if audio_path:
                        full_path = self.get_full_audio_path(audio_path)
                        if full_path and full_path.exists():
                            zip_file.write(full_path, full_path.name)
            
            zip_buffer.seek(0)
            
            interaction_id = output_data.get('id', 'unknown')
            zip_filename = f"echoverse_audio_{interaction_id}.zip"
            
            st.download_button(
                label="📦 Download All Audio",
                data=zip_buffer.getvalue(),
                file_name=zip_filename,
                mime="application/zip",
                help="Download all audio files as a ZIP"
            )
            
        except Exception as e:
            st.error(f"Error creating audio download: {str(e)}")
    
    def download_all_interaction_files(self, output_data):
        """Download all files from interaction."""
        # This is the same as download_interaction_content
        self.download_interaction_content(output_data)
    
    def render_audio_waveform(self, audio_path, audio_type):
        """Render audio waveform visualization (placeholder for future implementation)."""
        try:
            if not audio_path or not audio_path.exists():
                return
            
            # Placeholder for waveform visualization
            # This would require additional libraries like librosa, matplotlib, etc.
            st.info(f"🌊 Waveform visualization for {audio_type} audio (feature coming soon)")
            
            # Future implementation could include:
            # - Load audio with librosa
            # - Generate waveform plot with matplotlib
            # - Display with st.pyplot()
            
        except Exception as e:
            st.warning(f"Could not render waveform: {str(e)}")
    
    def check_authentication(self):
        """Check if user is still authenticated and update session state."""
        # Skip authentication check if login is in progress or just completed
        if (st.session_state.get('login_in_progress', False) or 
            st.session_state.get('login_just_completed', False)):
            return
        
        # If we have all required authentication components, we're authenticated
        if (st.session_state.get('session_token') and 
            st.session_state.get('current_user')):
            st.session_state.authenticated = True
            # Clear any session expiration errors for authenticated users
            if st.session_state.get('error_message') and "session has expired" in st.session_state.error_message.lower():
                st.session_state.error_message = ""
    
    def run(self):
        """Main application entry point with comprehensive error handling."""
        try:
            # Initialize error handling
            self._setup_error_handling()
            
            # Check authentication status
            self.check_authentication()
            
            # Check if user is authenticated (simple check)
            has_session = st.session_state.get('session_token') is not None
            has_user = st.session_state.get('current_user') is not None
            is_authenticated = st.session_state.get('authenticated', False)
            login_completed = st.session_state.get('login_just_completed', False)
            
            # If login just completed, force a rerun to refresh the page
            if login_completed:
                st.session_state.login_just_completed = False
                st.rerun()
            
            # Route to appropriate page - use simple logic
            if has_session and has_user:
                # Force authenticated state if we have session and user
                st.session_state.authenticated = True
                self.render_workspace()
            else:
                self.render_login_page()
                
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            self._handle_application_error(e)
    
    def _setup_error_handling(self):
        """Setup comprehensive error handling and logging."""
        try:
            # Configure logging if not already done
            if not hasattr(self, 'logger') or not self.logger:
                self.logger = logging.getLogger(__name__)
                
            # Initialize error tracking in session state
            if 'error_count' not in st.session_state:
                st.session_state.error_count = 0
            if 'last_error_time' not in st.session_state:
                st.session_state.last_error_time = None
                
        except Exception as e:
            # Fallback error handling
            st.error(f"Failed to setup error handling: {e}")
    
    def _handle_application_error(self, error: Exception):
        """Handle application-level errors with user-friendly messages and recovery options."""
        try:
            # Increment error count
            st.session_state.error_count = st.session_state.get('error_count', 0) + 1
            st.session_state.last_error_time = datetime.now()
            
            # Show user-friendly error message
            st.error("🚨 **Application Error**")
            st.error("Something went wrong. Don't worry - your data is safe!")
            
            # Provide error details
            error_type = type(error).__name__
            error_message = str(error)
            
            st.markdown(f"**Error Type:** {error_type}")
            st.markdown(f"**Error Message:** {error_message}")
            
            # Show recovery options
            st.markdown("### 🔧 Recovery Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Refresh Page", type="primary"):
                    st.rerun()
            
            with col2:
                if st.button("🏠 Go to Login"):
                    # Clear session state and redirect to login
                    for key in list(st.session_state.keys()):
                        if key not in ['error_count', 'last_error_time']:
                            del st.session_state[key]
                    st.rerun()
            
            with col3:
                if st.button("📊 Show Debug Info"):
                    st.session_state.show_debug_info = True
                    st.rerun()
            
            # Show debug information if requested
            if st.session_state.get('show_debug_info', False):
                st.markdown("### 🐛 Debug Information")
                
                with st.expander("Error Details", expanded=True):
                    st.code(traceback.format_exc())
                
                with st.expander("Session State"):
                    st.json({k: str(v) for k, v in st.session_state.items()})
                
                with st.expander("System Information"):
                    import platform
                    import sys
                    
                    system_info = {
                        "Python Version": sys.version,
                        "Platform": platform.platform(),
                        "Streamlit Version": st.__version__,
                        "Error Count": st.session_state.get('error_count', 0),
                        "Last Error": str(st.session_state.get('last_error_time', 'None'))
                    }
                    st.json(system_info)
                
                # Option to hide debug info
                if st.button("❌ Hide Debug Info"):
                    st.session_state.show_debug_info = False
                    st.rerun()
            
            # Show warning if too many errors
            if st.session_state.get('error_count', 0) > 3:
                st.warning("⚠️ **Multiple errors detected.** Consider refreshing the page or restarting the application.")
                
        except Exception as nested_error:
            # Fallback error handling for error handler itself
            st.error("Critical error in error handler:")
            st.error(str(nested_error))
            st.code(traceback.format_exc())


def main():
    """Main function to run the Streamlit app."""
    try:
        app = StreamlitApp()
        app.run()
    except Exception as e:
        st.error(f"Failed to start application: {e}")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()