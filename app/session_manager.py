"""
Session management and persistence system for EchoVerse companion application.
Handles automatic saving, session restoration, history caching, and data migration.
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import uuid
import logging

try:
    from .data_models import User, Interaction, GeneratedContent
    from .storage_manager import StorageManager, StorageError
except ImportError:
    from data_models import User, Interaction, GeneratedContent
    from storage_manager import StorageManager, StorageError


class SessionError(Exception):
    """Custom exception for session-related errors."""
    pass


class SessionManager:
    """
    Manages user sessions, automatic persistence, and data restoration.
    Provides caching and backup functionality for improved performance and reliability.
    """
    
    def __init__(self, storage_manager: StorageManager, base_path: str = "."):
        """
        Initialize the session manager.
        
        Args:
            storage_manager: StorageManager instance for data operations
            base_path: Base directory for session data
        """
        self.storage = storage_manager
        self.base_path = Path(base_path)
        self.sessions_dir = self.base_path / ".kiro" / "sessions"
        self.cache_dir = self.base_path / ".kiro" / "cache"
        self.backup_dir = self.base_path / ".kiro" / "backups"
        
        # Session state
        self.current_session_id: Optional[str] = None
        self.current_user: Optional[User] = None
        self.session_data: Dict[str, Any] = {}
        self.auto_save_enabled: bool = True
        self.auto_save_interval: int = 30  # seconds
        
        # Caching
        self.history_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl: int = 300  # 5 minutes
        
        # Auto-save thread
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()
        
        # Initialize directories
        self._ensure_directories()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _ensure_directories(self) -> None:
        """Create necessary directories for session management."""
        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise SessionError(f"Failed to create session directories: {e}")
    
    def start_session(self, user: User, session_token: Optional[str] = None) -> str:
        """
        Start a new user session with automatic persistence.
        
        Args:
            user: User object
            session_token: Optional existing session token
            
        Returns:
            str: Session ID
        """
        try:
            # Generate session ID if not provided
            if not session_token:
                session_token = str(uuid.uuid4())
            
            self.current_session_id = session_token
            self.current_user = user
            
            # Initialize session data
            self.session_data = {
                "session_id": session_token,
                "user_nickname": user.nickname,
                "start_time": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "workspace_state": {},
                "interaction_cache": [],
                "preferences": user.preferences.copy()
            }
            
            # Try to restore previous session state
            self._restore_session_state(user.nickname, session_token)
            
            # Start auto-save thread
            self._start_auto_save()
            
            # Load and cache user history
            self._load_and_cache_history(user)
            
            self.logger.info(f"Session started for user {user.nickname} with ID {session_token[:8]}...")
            
            return session_token
            
        except Exception as e:
            raise SessionError(f"Failed to start session: {e}")
    
    def end_session(self) -> bool:
        """
        End the current session and ensure all data is persisted.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.current_session_id or not self.current_user:
                return True
            
            # Stop auto-save thread
            self._stop_auto_save_thread()
            
            # Final save of session data
            self._save_session_data()
            
            # Create backup of session
            self._create_session_backup()
            
            # Clear session state
            session_id = self.current_session_id
            user_nickname = self.current_user.nickname
            
            self.current_session_id = None
            self.current_user = None
            self.session_data = {}
            
            self.logger.info(f"Session ended for user {user_nickname} with ID {session_id[:8]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
            return False
    
    def save_interaction_to_session(self, interaction: Interaction) -> bool:
        """
        Automatically save a completed interaction to the session and storage.
        Implements requirement 5.4: automatic history addition.
        
        Args:
            interaction: Completed interaction to save
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.current_user:
                raise SessionError("No active session")
            
            # Save interaction to persistent storage
            interaction_id = self.storage.save_interaction(self.current_user, interaction)
            
            # Add to session cache
            interaction_summary = {
                "id": interaction_id,
                "timestamp": interaction.timestamp.isoformat(),
                "input_type": interaction.input_data.input_type.value if interaction.input_data else "unknown",
                "preview": self._create_interaction_preview(interaction),
                "supportive_statement": interaction.generated_content.supportive_statement if interaction.generated_content else "",
                "poem": interaction.generated_content.poem if interaction.generated_content else "",
                "interaction_obj": interaction  # Keep full object for immediate access
            }
            
            # Add to session data
            if "interaction_cache" not in self.session_data:
                self.session_data["interaction_cache"] = []
            
            # Remove any existing entry with same ID and add new one at the beginning
            self.session_data["interaction_cache"] = [
                item for item in self.session_data["interaction_cache"] 
                if item.get("id") != interaction_id
            ]
            self.session_data["interaction_cache"].insert(0, interaction_summary)
            
            # Limit cache size (keep last 50 interactions in memory)
            self.session_data["interaction_cache"] = self.session_data["interaction_cache"][:50]
            
            # Update history cache
            if self.current_user.nickname in self.history_cache:
                self.history_cache[self.current_user.nickname].insert(0, interaction_summary)
                self.history_cache[self.current_user.nickname] = self.history_cache[self.current_user.nickname][:50]
            else:
                # Initialize cache if it doesn't exist
                self.history_cache[self.current_user.nickname] = [interaction_summary]
            
            # Update cache expiry
            self.cache_expiry[self.current_user.nickname] = datetime.now() + timedelta(seconds=self.cache_ttl)
            
            # Update last activity
            self.session_data["last_activity"] = datetime.now().isoformat()
            
            # Trigger immediate save and backup
            self._save_session_data()
            
            # Create periodic backup (every 10 interactions)
            interaction_count = len(self.session_data.get("interaction_cache", []))
            if interaction_count % 10 == 0:
                self.create_data_backup(self.current_user)
            
            self.logger.info(f"Interaction {interaction_id} automatically saved to session")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save interaction to session: {e}")
            return False
    
    def get_cached_history(self, user: User, force_refresh: bool = False, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get cached user history with automatic refresh if expired.
        Implements requirement 5.5: load complete interaction history on startup.
        
        Args:
            user: User object
            force_refresh: Force cache refresh
            limit: Maximum number of items to return (None for all)
            
        Returns:
            List of interaction summaries
        """
        try:
            cache_key = user.nickname
            now = datetime.now()
            
            # Check if cache exists and is valid
            if (not force_refresh and 
                cache_key in self.history_cache and 
                cache_key in self.cache_expiry and 
                now < self.cache_expiry[cache_key]):
                cached_history = self.history_cache[cache_key]
            else:
                # Load fresh history from storage
                self._load_and_cache_history(user)
                cached_history = self.history_cache.get(cache_key, [])
            
            # Apply limit if specified
            if limit is not None:
                return cached_history[:limit]
            
            return cached_history
            
        except Exception as e:
            self.logger.error(f"Failed to get cached history: {e}")
            return []
    
    def preload_history_cache(self, user: User, background: bool = True) -> bool:
        """
        Preload user history cache for improved performance.
        Can run in background thread to avoid blocking UI.
        
        Args:
            user: User object
            background: Whether to run in background thread
            
        Returns:
            bool: True if successful
        """
        def _preload():
            try:
                self._load_and_cache_history(user)
                self.logger.info(f"History cache preloaded for user {user.nickname}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to preload history cache: {e}")
                return False
        
        if background:
            import threading
            thread = threading.Thread(target=_preload, daemon=True)
            thread.start()
            return True
        else:
            return _preload()
    
    def get_history_statistics(self, user: User) -> Dict[str, Any]:
        """
        Get statistics about user's interaction history.
        
        Args:
            user: User object
            
        Returns:
            Dictionary containing history statistics
        """
        try:
            cached_history = self.get_cached_history(user)
            
            if not cached_history:
                return {
                    "total_interactions": 0,
                    "input_types": {},
                    "recent_activity": None,
                    "cache_status": "empty"
                }
            
            # Count input types
            input_types = {}
            for item in cached_history:
                input_type = item.get("input_type", "unknown")
                input_types[input_type] = input_types.get(input_type, 0) + 1
            
            # Get recent activity
            recent_activity = None
            if cached_history:
                recent_item = cached_history[0]  # Most recent
                recent_activity = {
                    "timestamp": recent_item.get("timestamp"),
                    "preview": recent_item.get("preview"),
                    "input_type": recent_item.get("input_type")
                }
            
            return {
                "total_interactions": len(cached_history),
                "input_types": input_types,
                "recent_activity": recent_activity,
                "cache_status": "loaded",
                "cache_expiry": self.cache_expiry.get(user.nickname, datetime.now()).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get history statistics: {e}")
            return {"error": str(e)}
    
    def restore_session_on_startup(self, user: User, session_token: str = None) -> Dict[str, Any]:
        """
        Restore session state when application starts.
        Implements requirement 6.4: ensure data persists for future sessions.
        
        Args:
            user: User object
            session_token: Session token to restore (if None, finds most recent)
            
        Returns:
            Dictionary containing restored session state
        """
        try:
            # If no session token provided, find the most recent session
            if not session_token:
                session_files = list(self.sessions_dir.glob(f"{user.nickname}_*.json"))
                if not session_files:
                    return {}
                
                # Sort by modification time (newest first)
                session_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                session_file = session_files[0]
                
                # Extract session token from filename
                session_token = session_file.stem.split('_', 1)[1]
            else:
                session_file = self.sessions_dir / f"{user.nickname}_{session_token}.json"
            
            if not session_file.exists():
                # No previous session to restore
                return {}
            
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Validate session data
            if session_data.get("user_nickname") != user.nickname:
                self.logger.warning(f"Session user mismatch for {user.nickname}")
                return {}
            
            # Check if session is not too old (7 days)
            start_time_str = session_data.get("start_time", "")
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                if datetime.now() - start_time > timedelta(days=7):
                    self.logger.info(f"Session too old for {user.nickname}, starting fresh")
                    return {}
            
            # Restore workspace state and interaction cache
            workspace_state = session_data.get("workspace_state", {})
            interaction_cache = session_data.get("interaction_cache", [])
            
            # Restore interaction cache to session
            if interaction_cache:
                self.session_data["interaction_cache"] = interaction_cache
                # Update history cache with session data
                self.history_cache[user.nickname] = interaction_cache
                self.cache_expiry[user.nickname] = datetime.now() + timedelta(seconds=self.cache_ttl)
            
            # Preload full history in background for better performance
            self.preload_history_cache(user, background=True)
            
            self.logger.info(f"Session restored for user {user.nickname} (token: {session_token[:8]}...)")
            
            return {
                "workspace_state": workspace_state,
                "session_token": session_token,
                "restored_interactions": len(interaction_cache),
                "last_activity": session_data.get("last_activity")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to restore session: {e}")
            return {}
    
    def get_available_sessions(self, user: User) -> List[Dict[str, Any]]:
        """
        Get list of available sessions for a user.
        
        Args:
            user: User object
            
        Returns:
            List of session information dictionaries
        """
        try:
            session_files = list(self.sessions_dir.glob(f"{user.nickname}_*.json"))
            sessions = []
            
            for session_file in session_files:
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # Extract session token from filename
                    session_token = session_file.stem.split('_', 1)[1]
                    
                    session_info = {
                        "session_token": session_token,
                        "start_time": session_data.get("start_time"),
                        "last_activity": session_data.get("last_activity"),
                        "interaction_count": len(session_data.get("interaction_cache", [])),
                        "file_size": session_file.stat().st_size,
                        "modified": datetime.fromtimestamp(session_file.stat().st_mtime).isoformat()
                    }
                    sessions.append(session_info)
                    
                except Exception as e:
                    self.logger.warning(f"Could not read session file {session_file}: {e}")
            
            # Sort by last activity (newest first)
            sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get available sessions: {e}")
            return []
    
    def update_workspace_state(self, state_updates: Dict[str, Any]) -> bool:
        """
        Update workspace state in the current session.
        
        Args:
            state_updates: Dictionary of state updates
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.current_session_id:
                return False
            
            if "workspace_state" not in self.session_data:
                self.session_data["workspace_state"] = {}
            
            self.session_data["workspace_state"].update(state_updates)
            self.session_data["last_activity"] = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update workspace state: {e}")
            return False
    
    def check_storage_availability(self) -> tuple[bool, str]:
        """
        Check if local storage is available and writable.
        Implements requirement 6.5: error handling for storage unavailability.
        
        Returns:
            tuple: (is_available, error_message)
        """
        try:
            # Test write access to base directories
            test_file = self.sessions_dir / "test_write.tmp"
            
            # Try to write a test file
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Try to read it back
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Clean up
            test_file.unlink()
            
            if content != "test":
                return False, "Storage read/write verification failed"
            
            # Check available disk space (warn if less than 100MB)
            import shutil
            free_space = shutil.disk_usage(self.base_path).free
            if free_space < 100 * 1024 * 1024:  # 100MB
                return False, f"Low disk space: {free_space // (1024*1024)}MB available"
            
            return True, ""
            
        except PermissionError:
            return False, "Permission denied: Cannot write to storage directory"
        except OSError as e:
            return False, f"Storage system error: {e}"
        except Exception as e:
            return False, f"Unknown storage error: {e}"
    
    def create_data_backup(self, user: User, backup_type: str = "manual") -> bool:
        """
        Create a backup of user data for migration/recovery purposes.
        
        Args:
            user: User object
            backup_type: Type of backup ("manual", "automatic", "migration")
            
        Returns:
            bool: True if successful
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{user.nickname}_backup_{backup_type}_{timestamp}.json"
            
            # Collect all user data
            backup_data = {
                "backup_timestamp": datetime.now().isoformat(),
                "backup_type": backup_type,
                "backup_version": "1.0",
                "user_profile": {
                    "nickname": user.nickname,
                    "created": user.created.isoformat(),
                    "preferences": user.preferences,
                    "prompts": user.prompts
                },
                "interactions": [],
                "storage_stats": self.storage.get_storage_stats(user.nickname),
                "session_info": {
                    "current_session_id": self.current_session_id,
                    "session_start": self.session_data.get("start_time"),
                    "last_activity": self.session_data.get("last_activity"),
                    "workspace_state": self.session_data.get("workspace_state", {})
                }
            }
            
            # Load all interactions
            try:
                interactions = self.storage.load_user_history(user)
                for interaction in interactions:
                    interaction_data = {
                        "id": interaction.id,
                        "timestamp": interaction.timestamp.isoformat(),
                        "input_data": {
                            "content": interaction.input_data.content if interaction.input_data else "",
                            "input_type": interaction.input_data.input_type.value if interaction.input_data else "unknown",
                            "metadata": interaction.input_data.metadata if interaction.input_data else {}
                        },
                        "generated_content": {
                            "supportive_statement": interaction.generated_content.supportive_statement if interaction.generated_content else "",
                            "poem": interaction.generated_content.poem if interaction.generated_content else "",
                            "generation_metadata": interaction.generated_content.generation_metadata if interaction.generated_content else {}
                        },
                        "file_paths": interaction.file_paths,
                        "audio_files": [
                            {
                                "file_path": af.file_path,
                                "format": af.format,
                                "metadata": af.metadata
                            } for af in interaction.audio_files
                        ]
                    }
                    backup_data["interactions"].append(interaction_data)
            except Exception as e:
                self.logger.warning(f"Could not backup interactions: {e}")
            
            # Save backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Data backup created: {backup_file} (type: {backup_type})")
            
            # Clean up old backups (keep last 5 of each type)
            self._cleanup_old_backups(user.nickname, backup_type)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create data backup: {e}")
            return False
    
    def _create_interaction_preview(self, interaction: Interaction) -> str:
        """Create a short preview text for an interaction."""
        if not interaction.input_data:
            return "Untitled interaction"
        
        content = interaction.input_data.content.strip()
        if len(content) <= 50:
            return content
        
        return content[:47] + "..."
    
    def _load_and_cache_history(self, user: User) -> None:
        """Load user history and cache it for performance."""
        try:
            # Load interactions from storage
            interactions = self.storage.load_user_history(user)
            
            # Convert to cache format
            cached_items = []
            for interaction in interactions:
                item = {
                    "id": interaction.id,
                    "timestamp": interaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "input_type": interaction.input_data.input_type.value if interaction.input_data else "unknown",
                    "preview": self._create_interaction_preview(interaction),
                    "supportive_statement": interaction.generated_content.supportive_statement if interaction.generated_content else "",
                    "poem": interaction.generated_content.poem if interaction.generated_content else "",
                    "interaction_obj": interaction
                }
                cached_items.append(item)
            
            # Update cache
            self.history_cache[user.nickname] = cached_items
            self.cache_expiry[user.nickname] = datetime.now() + timedelta(seconds=self.cache_ttl)
            
            self.logger.info(f"Loaded and cached {len(cached_items)} interactions for user {user.nickname}")
            
        except Exception as e:
            self.logger.error(f"Failed to load and cache history: {e}")
            self.history_cache[user.nickname] = []
    
    def persist_session_on_shutdown(self) -> bool:
        """
        Persist current session data on application shutdown.
        Ensures all data is saved before the application closes.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.current_session_id or not self.current_user:
                return True
            
            # Stop auto-save thread
            self._stop_auto_save_thread()
            
            # Final save of session data
            self._save_session_data()
            
            # Create shutdown backup
            self.create_data_backup(self.current_user, "shutdown")
            
            # Update session metadata
            self.session_data["shutdown_time"] = datetime.now().isoformat()
            self.session_data["clean_shutdown"] = True
            
            # Save final session state
            self._save_session_data()
            
            self.logger.info(f"Session persisted on shutdown for user {self.current_user.nickname}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to persist session on shutdown: {e}")
            return False
    
    def cleanup_expired_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up expired session files to free disk space.
        
        Args:
            max_age_days: Maximum age of sessions to keep
            
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            cleaned_count = 0
            
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    # Check file modification time
                    file_time = datetime.fromtimestamp(session_file.stat().st_mtime)
                    
                    if file_time < cutoff_time:
                        session_file.unlink()
                        cleaned_count += 1
                        
                except OSError:
                    pass  # Ignore errors when deleting files
            
            self.logger.info(f"Cleaned up {cleaned_count} expired session files")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    def _restore_session_state(self, nickname: str, session_token: str) -> None:
        """Restore session state from previous session."""
        try:
            session_file = self.sessions_dir / f"{nickname}_{session_token}.json"
            
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                # Merge with current session data
                self.session_data.update(saved_data)
                self.session_data["last_activity"] = datetime.now().isoformat()
                
        except Exception as e:
            self.logger.warning(f"Could not restore session state: {e}")
    
    def _save_session_data(self) -> None:
        """Save current session data to disk."""
        try:
            if not self.current_session_id or not self.current_user:
                return
            
            session_file = self.sessions_dir / f"{self.current_user.nickname}_{self.current_session_id}.json"
            
            # Create a copy without the full interaction objects to reduce file size
            save_data = self.session_data.copy()
            if "interaction_cache" in save_data:
                # Remove full interaction objects from saved data
                save_data["interaction_cache"] = [
                    {k: v for k, v in item.items() if k != "interaction_obj"}
                    for item in save_data["interaction_cache"]
                ]
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    def _start_auto_save(self) -> None:
        """Start the auto-save background thread."""
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            return
        
        self._stop_auto_save.clear()
        self._auto_save_thread = threading.Thread(target=self._auto_save_worker, daemon=True)
        self._auto_save_thread.start()
    
    def _stop_auto_save_thread(self) -> None:
        """Stop the auto-save background thread."""
        if self._auto_save_thread:
            self._stop_auto_save.set()
            self._auto_save_thread.join(timeout=5)
    
    def _auto_save_worker(self) -> None:
        """Background worker for automatic session saving."""
        while not self._stop_auto_save.wait(self.auto_save_interval):
            try:
                if self.auto_save_enabled and self.current_session_id:
                    self._save_session_data()
            except Exception as e:
                self.logger.error(f"Auto-save error: {e}")
    
    def _create_session_backup(self) -> None:
        """Create a backup of the current session."""
        try:
            if not self.current_user:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"session_{self.current_user.nickname}_{timestamp}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to create session backup: {e}")
    
    def migrate_user_data(self, backup_file_path: str, target_user: User) -> bool:
        """
        Migrate user data from a backup file to a target user account.
        Implements data migration functionality for requirement 6.4.
        
        Args:
            backup_file_path: Path to the backup file
            target_user: Target user to migrate data to
            
        Returns:
            bool: True if successful
        """
        try:
            backup_path = Path(backup_file_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_file_path}")
                return False
            
            # Load backup data
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Validate backup format
            if not self._validate_backup_format(backup_data):
                self.logger.error("Invalid backup file format")
                return False
            
            # Create migration backup of current user data
            self.create_data_backup(target_user, "pre_migration")
            
            # Migrate user preferences (merge with existing)
            if "user_profile" in backup_data:
                source_prefs = backup_data["user_profile"].get("preferences", {})
                target_user.preferences.update(source_prefs)
                self.storage.save_user_profile(target_user)
            
            # Migrate interactions
            migrated_count = 0
            if "interactions" in backup_data:
                for interaction_data in backup_data["interactions"]:
                    try:
                        # Reconstruct interaction object
                        interaction = self._reconstruct_interaction_from_backup(interaction_data)
                        if interaction:
                            # Save with new ID to avoid conflicts
                            interaction.id = str(uuid.uuid4())
                            self.storage.save_interaction(target_user, interaction)
                            migrated_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to migrate interaction {interaction_data.get('id', 'unknown')}: {e}")
            
            # Update cache
            self._load_and_cache_history(target_user)
            
            self.logger.info(f"Successfully migrated {migrated_count} interactions to user {target_user.nickname}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate user data: {e}")
            return False
    
    def _validate_backup_format(self, backup_data: Dict[str, Any]) -> bool:
        """Validate backup file format."""
        required_fields = ["backup_timestamp", "user_profile"]
        return all(field in backup_data for field in required_fields)
    
    def _reconstruct_interaction_from_backup(self, interaction_data: Dict[str, Any]) -> Optional[Interaction]:
        """Reconstruct an Interaction object from backup data."""
        try:
            # Import with fallback for different import contexts
            try:
                from .data_models import InputType, ProcessedInput, GeneratedContent
            except ImportError:
                from data_models import InputType, ProcessedInput, GeneratedContent
            
            # Create interaction
            interaction = Interaction(
                id=interaction_data["id"],
                timestamp=datetime.fromisoformat(interaction_data["timestamp"])
            )
            
            # Reconstruct input data
            if "input_data" in interaction_data:
                input_data = interaction_data["input_data"]
                interaction.input_data = ProcessedInput(
                    content=input_data["content"],
                    input_type=InputType(input_data["input_type"]),
                    metadata=input_data.get("metadata", {}),
                    raw_data=None  # Raw data not preserved in backup
                )
            
            # Reconstruct generated content
            if "generated_content" in interaction_data:
                content_data = interaction_data["generated_content"]
                interaction.generated_content = GeneratedContent(
                    supportive_statement=content_data["supportive_statement"],
                    poem=content_data["poem"],
                    generation_metadata=content_data.get("generation_metadata", {})
                )
            
            # Set file paths (files themselves need to be manually copied)
            interaction.file_paths = interaction_data.get("file_paths", {})
            
            return interaction
            
        except Exception as e:
            self.logger.error(f"Failed to reconstruct interaction from backup: {e}")
            return None
    
    def _cleanup_old_backups(self, nickname: str, backup_type: str = None) -> None:
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            # Find backup files for this user
            if backup_type:
                backup_files = list(self.backup_dir.glob(f"{nickname}_backup_{backup_type}_*.json"))
            else:
                backup_files = list(self.backup_dir.glob(f"{nickname}_backup_*.json"))
                backup_files.extend(self.backup_dir.glob(f"session_{nickname}_*.json"))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the 5 most recent backups
            for old_backup in backup_files[5:]:
                try:
                    old_backup.unlink()
                except OSError:
                    pass  # Ignore errors when deleting old backups
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")


class SessionStateManager:
    """
    Helper class for managing Streamlit session state with persistence.
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize with a session manager.
        
        Args:
            session_manager: SessionManager instance
        """
        self.session_manager = session_manager
    
    def save_state_to_session(self, state_dict: Dict[str, Any]) -> bool:
        """
        Save Streamlit session state to persistent session.
        
        Args:
            state_dict: Dictionary of state to save
            
        Returns:
            bool: True if successful
        """
        try:
            # Filter out non-serializable items
            serializable_state = {}
            for key, value in state_dict.items():
                try:
                    json.dumps(value, default=str)  # Test serializability
                    serializable_state[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable items
                    continue
            
            return self.session_manager.update_workspace_state({
                "streamlit_state": serializable_state,
                "state_timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save state to session: {e}")
            return False
    
    def restore_state_from_session(self) -> Dict[str, Any]:
        """
        Restore Streamlit session state from persistent session.
        
        Returns:
            Dictionary of restored state
        """
        try:
            if not self.session_manager.session_data:
                return {}
            
            workspace_state = self.session_manager.session_data.get("workspace_state", {})
            streamlit_state = workspace_state.get("streamlit_state", {})
            
            return streamlit_state
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to restore state from session: {e}")
            return {}