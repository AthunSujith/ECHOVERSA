"""
Authentication system for EchoVerse companion application.
Handles user registration, login, password validation, and session management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

try:
    from .data_models import User, validate_nickname, validate_password
    from .storage_manager import StorageManager, StorageError
except ImportError:
    from data_models import User, validate_nickname, validate_password
    from storage_manager import StorageManager, StorageError


class AuthenticationError(Exception):
    """Custom exception for authentication-related errors."""
    pass


class SessionManager:
    """Manages user sessions and authentication state."""
    
    def __init__(self):
        """Initialize session manager."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = timedelta(hours=24)  # 24 hour session timeout
    
    def create_session(self, user: User) -> str:
        """
        Create a new session for a user.
        
        Args:
            user: User object
            
        Returns:
            str: Session token
        """
        session_token = secrets.token_urlsafe(32)
        session_data = {
            "user": user,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "expires_at": datetime.now() + self.session_timeout
        }
        
        self.active_sessions[session_token] = session_data
        return session_token
    
    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by token.
        
        Args:
            session_token: Session token
            
        Returns:
            Session data dictionary or None if invalid/expired
        """
        if session_token not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_token]
        
        # Check if session has expired
        if datetime.now() > session_data["expires_at"]:
            self.invalidate_session(session_token)
            return None
        
        # Update last activity
        session_data["last_activity"] = datetime.now()
        return session_data
    
    def get_user_from_session(self, session_token: str) -> Optional[User]:
        """
        Get user from session token.
        
        Args:
            session_token: Session token
            
        Returns:
            User object or None if invalid session
        """
        session_data = self.get_session(session_token)
        return session_data["user"] if session_data else None
    
    def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate a session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            bool: True if session was found and invalidated
        """
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        current_time = datetime.now()
        expired_tokens = [
            token for token, data in self.active_sessions.items()
            if current_time > data["expires_at"]
        ]
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        return len(expired_tokens)
    
    def extend_session(self, session_token: str) -> bool:
        """
        Extend session expiration time.
        
        Args:
            session_token: Session token to extend
            
        Returns:
            bool: True if session was extended
        """
        if session_token in self.active_sessions:
            session_data = self.active_sessions[session_token]
            session_data["expires_at"] = datetime.now() + self.session_timeout
            session_data["last_activity"] = datetime.now()
            return True
        return False


class PasswordManager:
    """Handles password hashing and validation."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password with salt.
        
        Args:
            password: Plain text password
            salt: Optional salt (generates new one if not provided)
            
        Returns:
            tuple: (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                   salt.encode('utf-8'), 100000)
        return hashed.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Stored hashed password
            salt: Salt used for hashing
            
        Returns:
            bool: True if password matches
        """
        try:
            computed_hash, _ = PasswordManager.hash_password(password, salt)
            return secrets.compare_digest(computed_hash, hashed_password)
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """
        Validate password strength and return list of issues.
        
        Args:
            password: Password to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        if not validate_password(password):
            issues.append("Password must be between 4 and 128 characters")
        
        if len(password) < 6:
            issues.append("Password should be at least 6 characters for better security")
        
        # Check for basic complexity (optional recommendations)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        complexity_score = sum([has_upper, has_lower, has_digit])
        
        if complexity_score < 2 and len(password) < 8:
            issues.append("Consider using a mix of uppercase, lowercase, and numbers")
        
        return issues


class UserManager:
    """
    Manages user authentication, registration, and profile operations.
    """
    
    def __init__(self, storage_manager: Optional[StorageManager] = None):
        """
        Initialize the user manager.
        
        Args:
            storage_manager: StorageManager instance (creates new one if None)
        """
        self.storage = storage_manager or StorageManager()
        self.session_manager = SessionManager()
        self.password_manager = PasswordManager()
    
    def register_user(self, nickname: str, password: str) -> tuple[bool, str]:
        """
        Register a new user.
        
        Args:
            nickname: User's chosen nickname
            password: User's password
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Validate nickname
            if not validate_nickname(nickname):
                return False, "Invalid nickname format. Use 2-50 alphanumeric characters, underscores, or hyphens."
            
            # Check if user already exists
            if self.storage.user_exists(nickname):
                return False, "A user with this nickname already exists."
            
            # Validate password
            password_issues = self.password_manager.validate_password_strength(password)
            if any("must be" in issue for issue in password_issues):
                return False, password_issues[0]
            
            # Hash password
            hashed_password, salt = self.password_manager.hash_password(password)
            
            # Create user object
            user = User(
                nickname=nickname,
                password=hashed_password,  # Store hashed password
                created=datetime.now(),
                preferences={
                    "password_salt": salt,  # Store salt in preferences
                    "voice_settings": {},
                    "ui_theme": "default",
                    "auto_remix": False
                },
                prompts=[]
            )
            
            # Create user directory and save profile
            self.storage.create_user_directory(user)
            success = self.storage.save_user_profile(user)
            
            if success:
                message = "User registered successfully."
                if password_issues:
                    message += f" Note: {'; '.join(password_issues)}"
                return True, message
            else:
                return False, "Failed to save user profile."
                
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def authenticate_user(self, nickname: str, password: str) -> tuple[Optional[User], str]:
        """
        Authenticate a user with nickname and password.
        
        Args:
            nickname: User's nickname
            password: User's password
            
        Returns:
            tuple: (User object if successful, message)
        """
        try:
            # Load user profile
            user = self.storage.load_user_profile(nickname)
            if not user:
                return None, "User not found."
            
            # Get salt from preferences
            salt = user.preferences.get("password_salt")
            if not salt:
                # Legacy user without salt - need to handle this case
                # For now, we'll treat this as invalid
                return None, "Invalid user profile format."
            
            # Verify password
            if self.password_manager.verify_password(password, user.password, salt):
                return user, "Authentication successful."
            else:
                return None, "Invalid password."
                
        except Exception as e:
            return None, f"Authentication failed: {str(e)}"
    
    def login_user(self, nickname: str, password: str) -> tuple[Optional[str], str]:
        """
        Login a user and create a session.
        
        Args:
            nickname: User's nickname
            password: User's password
            
        Returns:
            tuple: (session_token if successful, message)
        """
        user, message = self.authenticate_user(nickname, password)
        
        if user:
            session_token = self.session_manager.create_session(user)
            return session_token, message
        else:
            return None, message
    
    def logout_user(self, session_token: str) -> bool:
        """
        Logout a user by invalidating their session.
        
        Args:
            session_token: User's session token
            
        Returns:
            bool: True if logout successful
        """
        return self.session_manager.invalidate_session(session_token)
    
    def get_current_user(self, session_token: str) -> Optional[User]:
        """
        Get the currently logged-in user from session token.
        
        Args:
            session_token: Session token
            
        Returns:
            User object if valid session, None otherwise
        """
        session_data = self.session_manager.get_session(session_token)
        if session_data:
            return session_data["user"]
        return None
    
    def is_user_logged_in(self, session_token: str) -> bool:
        """
        Check if a user is currently logged in.
        
        Args:
            session_token: Session token to check
            
        Returns:
            bool: True if user is logged in
        """
        return self.get_current_user(session_token) is not None
    
    def update_user_preferences(self, session_token: str, preferences: Dict[str, Any]) -> tuple[bool, str]:
        """
        Update user preferences.
        
        Args:
            session_token: User's session token
            preferences: Dictionary of preferences to update
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = self.get_current_user(session_token)
            if not user:
                return False, "User not logged in."
            
            # Update preferences (preserve password_salt)
            salt = user.preferences.get("password_salt")
            user.preferences.update(preferences)
            if salt:
                user.preferences["password_salt"] = salt
            
            # Save updated profile
            success = self.storage.save_user_profile(user)
            return success, "Preferences updated successfully." if success else "Failed to update preferences."
            
        except Exception as e:
            return False, f"Failed to update preferences: {str(e)}"
    
    def change_password(self, session_token: str, current_password: str, new_password: str) -> tuple[bool, str]:
        """
        Change user's password.
        
        Args:
            session_token: User's session token
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = self.get_current_user(session_token)
            if not user:
                return False, "User not logged in."
            
            # Verify current password
            salt = user.preferences.get("password_salt")
            if not salt or not self.password_manager.verify_password(current_password, user.password, salt):
                return False, "Current password is incorrect."
            
            # Validate new password
            password_issues = self.password_manager.validate_password_strength(new_password)
            if any("must be" in issue for issue in password_issues):
                return False, password_issues[0]
            
            # Hash new password with new salt
            hashed_password, new_salt = self.password_manager.hash_password(new_password)
            
            # Update user
            user.password = hashed_password
            user.preferences["password_salt"] = new_salt
            
            # Save updated profile
            success = self.storage.save_user_profile(user)
            
            if success:
                message = "Password changed successfully."
                if password_issues:
                    message += f" Note: {'; '.join(password_issues)}"
                return True, message
            else:
                return False, "Failed to save new password."
                
        except Exception as e:
            return False, f"Failed to change password: {str(e)}"
    
    def get_user_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information (safe for display).
        
        Args:
            session_token: User's session token
            
        Returns:
            Dictionary with user info or None if not logged in
        """
        user = self.get_current_user(session_token)
        if not user:
            return None
        
        return {
            "nickname": user.nickname,
            "created": user.created.isoformat(),
            "total_prompts": len(user.prompts),
            "preferences": {k: v for k, v in user.preferences.items() 
                          if k != "password_salt"}  # Exclude sensitive data
        }
    
    def cleanup_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        return self.session_manager.cleanup_expired_sessions()
    
    def extend_user_session(self, session_token: str) -> bool:
        """
        Extend user's session expiration.
        
        Args:
            session_token: Session token to extend
            
        Returns:
            bool: True if session was extended
        """
        return self.session_manager.extend_session(session_token)
    
    def get_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_token: Session token
            
        Returns:
            Dictionary with session info or None if invalid
        """
        session_data = self.session_manager.get_session(session_token)
        if not session_data:
            return None
        
        return {
            "created_at": session_data["created_at"].isoformat(),
            "last_activity": session_data["last_activity"].isoformat(),
            "expires_at": session_data["expires_at"].isoformat(),
            "user_nickname": session_data["user"].nickname
        }
    
    def list_users(self) -> List[str]:
        """
        List all registered user nicknames (admin function).
        
        Returns:
            List of user nicknames
        """
        try:
            users_dir = self.storage.users_dir
            user_files = users_dir.glob("*.json")
            return [f.stem for f in user_files if f.is_file()]
        except Exception:
            return []
    
    def delete_user(self, nickname: str, admin_override: bool = False) -> tuple[bool, str]:
        """
        Delete a user account and all associated data.
        
        Args:
            nickname: User's nickname
            admin_override: Whether this is an admin override (bypasses some checks)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not admin_override:
                return False, "User deletion requires admin privileges."
            
            # Check if user exists
            if not self.storage.user_exists(nickname):
                return False, "User not found."
            
            # Remove user profile file
            profile_path = self.storage._get_user_profile_path(nickname)
            if profile_path.exists():
                profile_path.unlink()
            
            # Remove user directory and all interactions
            user_dir = self.storage._get_user_directory(nickname)
            if user_dir.exists():
                import shutil
                shutil.rmtree(user_dir)
            
            # Invalidate any active sessions for this user
            sessions_to_remove = []
            for token, session_data in self.session_manager.active_sessions.items():
                if session_data["user"].nickname == nickname:
                    sessions_to_remove.append(token)
            
            for token in sessions_to_remove:
                self.session_manager.invalidate_session(token)
            
            return True, "User account deleted successfully."
            
        except Exception as e:
            return False, f"Failed to delete user: {str(e)}"