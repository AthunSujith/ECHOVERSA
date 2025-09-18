"""
Local storage and file management system for EchoVerse companion application.
Handles user data persistence, interaction storage, and file operations.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid

try:
    from .data_models import (
        User, Interaction, ProcessedInput, GeneratedContent, AudioFile,
        validate_user_data_integrity, validate_interaction_data_integrity,
        validate_file_path
    )
    from .performance_optimizer import (
        get_performance_optimizer, monitor_performance, cache_result,
        LoadingIndicator, ProgressTracker
    )
except ImportError:
    from data_models import (
        User, Interaction, ProcessedInput, GeneratedContent, AudioFile,
        validate_user_data_integrity, validate_interaction_data_integrity,
        validate_file_path
    )
    from performance_optimizer import (
        get_performance_optimizer, monitor_performance, cache_result,
        LoadingIndicator, ProgressTracker
    )


class StorageError(Exception):
    """Custom exception for storage-related errors."""
    pass


class StorageManager:
    """
    Manages all local file operations and data persistence for the application.
    Handles user profiles, interaction history, and generated content storage.
    """
    
    def __init__(self, base_path: str = "."):
        """
        Initialize the storage manager with base directory paths.
        
        Args:
            base_path: Base directory for the application (default: current directory)
        """
        self.base_path = Path(base_path)
        self.users_dir = self.base_path / "users"
        self.outputs_dir = self.base_path / "outputs"
        
        # Initialize performance optimizer for file operations
        self.performance_optimizer = get_performance_optimizer()
        
        # File operation batching
        self.pending_operations = []
        self.batch_size = 10
        
        # Ensure base directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        try:
            self.users_dir.mkdir(exist_ok=True)
            self.outputs_dir.mkdir(exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create base directories: {e}")
    
    def _get_user_profile_path(self, nickname: str) -> Path:
        """Get the path to a user's profile JSON file inside their folder."""
        return self.users_dir / nickname / f"{nickname}.json"
    
    def _get_user_directory(self, nickname: str) -> Path:
        """Get the path to a user's main directory."""
        return self.users_dir / nickname
    
    def _get_interaction_directory(self, nickname: str, interaction_id: str) -> Path:
        """Get the path to a specific interaction directory."""
        return self._get_user_directory(nickname) / interaction_id
    
    def user_exists(self, nickname: str) -> bool:
        """
        Check if a user profile exists.
        
        Args:
            nickname: The user's nickname
            
        Returns:
            bool: True if user exists, False otherwise
        """
        user_dir = self._get_user_directory(nickname)
        user_file = self._get_user_profile_path(nickname)
        return user_dir.exists() and user_file.exists()
    
    def create_user_directory(self, user: User) -> bool:
        """
        Create directory structure for a new user with their JSON file.
        
        Args:
            user: User object containing profile information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate user data
            errors = validate_user_data_integrity(user)
            if errors:
                raise StorageError(f"User data validation failed: {', '.join(errors)}")
            
            # Create user directory
            user_dir = self._get_user_directory(user.nickname)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize user data structure with interactions array
            user.prompts = []  # This will now store complete interactions
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to create user directory: {e}")
    
    def save_user_profile(self, user: User) -> bool:
        """
        Save user profile to JSON file.
        
        Args:
            user: User object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate user data
            errors = validate_user_data_integrity(user)
            if errors:
                raise StorageError(f"User data validation failed: {', '.join(errors)}")
            
            # Prepare user data for JSON serialization
            user_data = {
                "nickname": user.nickname,
                "password": user.password,
                "created": user.created.isoformat(),
                "preferences": user.preferences,
                "prompts": user.prompts
            }
            
            # Save to JSON file
            profile_path = self._get_user_profile_path(user.nickname)
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to save user profile: {e}")
    
    def load_user_profile(self, nickname: str) -> Optional[User]:
        """
        Load user profile from JSON file.
        
        Args:
            nickname: The user's nickname
            
        Returns:
            User object if found, None otherwise
        """
        try:
            profile_path = self._get_user_profile_path(nickname)
            
            if not profile_path.exists():
                return None
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            
            # Convert ISO string back to datetime
            created = datetime.fromisoformat(user_data['created'])
            
            user = User(
                nickname=user_data['nickname'],
                password=user_data['password'],
                created=created,
                preferences=user_data.get('preferences', {}),
                prompts=user_data.get('prompts', [])
            )
            
            return user
            
        except Exception as e:
            raise StorageError(f"Failed to load user profile: {e}")
    
    @monitor_performance("save_interaction")
    def save_interaction(self, user: User, interaction: Interaction) -> str:
        """
        Save a complete interaction directly in the user's JSON file.
        
        Args:
            user: User object
            interaction: Interaction object to save
            
        Returns:
            str: The interaction ID
        """
        try:
            # Validate interaction data
            errors = validate_interaction_data_integrity(interaction)
            if errors:
                raise StorageError(f"Interaction data validation failed: {', '.join(errors)}")
            
            # Ensure user directory exists
            user_dir = self._get_user_directory(user.nickname)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Create complete interaction data with all information
            interaction_data = {
                "id": interaction.id,
                "timestamp": interaction.timestamp.isoformat(),
                "input": {
                    "content": interaction.input_data.content if interaction.input_data else "",
                    "type": interaction.input_data.input_type.value if interaction.input_data else "text",
                    "metadata": interaction.input_data.metadata if interaction.input_data else {}
                },
                "output": {
                    "supportive_statement": interaction.generated_content.supportive_statement if interaction.generated_content else "",
                    "poem": interaction.generated_content.poem if interaction.generated_content else "",
                    "generation_metadata": interaction.generated_content.metadata if interaction.generated_content else {}
                },
                "audio_files": [
                    {
                        "type": audio.metadata.get("type", "unknown"),
                        "duration": audio.duration,
                        "file_path": audio.file_path,
                        "metadata": audio.metadata
                    } for audio in interaction.audio_files
                ],
                "created_at": datetime.now().isoformat(),
                "file_paths": getattr(interaction, 'file_paths', {})
            }
            
            # Add to user's prompts list (avoid duplicates)
            if not hasattr(user, 'prompts') or user.prompts is None:
                user.prompts = []
            
            # Remove any existing interaction with same ID
            user.prompts = [p for p in user.prompts if p.get("id") != interaction.id]
            
            # Add the complete interaction data
            user.prompts.append(interaction_data)
            
            # Sort by timestamp (newest first)
            user.prompts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Save updated user profile with all interactions
            self.save_user_profile(user)
            
            return interaction.id
            
        except Exception as e:
            raise StorageError(f"Failed to save interaction: {e}")
    
    @monitor_performance("load_interaction")
    @cache_result("interaction_{args[0]}_{args[1]}", ttl=300)
    def load_interaction(self, nickname: str, interaction_id: str) -> Optional[Interaction]:
        """
        Load a complete interaction from storage.
        
        Args:
            nickname: User's nickname
            interaction_id: ID of the interaction to load
            
        Returns:
            Interaction object if found, None otherwise
        """
        try:
            interaction_dir = self._get_interaction_directory(nickname, interaction_id)
            meta_path = interaction_dir / "meta.json"
            
            if not meta_path.exists():
                return None
            
            # Load metadata
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Reconstruct interaction object
            interaction = Interaction(
                id=metadata["id"],
                timestamp=datetime.fromisoformat(metadata["timestamp"])
            )
            
            # Load input data
            if metadata.get("input"):
                try:
                    from .data_models import InputType
                except ImportError:
                    from data_models import InputType
                input_type = InputType(metadata["input"]["type"])
                
                # Load raw data if exists
                raw_data = None
                if metadata["input"].get("raw_file"):
                    raw_path = self.base_path / metadata["input"]["raw_file"]
                    if raw_path.exists():
                        with open(raw_path, 'rb') as f:
                            raw_data = f.read()
                elif metadata.get("output", {}).get("sketch_file"):
                    # Check for sketch file in output section (legacy compatibility)
                    sketch_path = self.base_path / metadata["output"]["sketch_file"]
                    if sketch_path.exists():
                        with open(sketch_path, 'rb') as f:
                            raw_data = f.read()
                
                interaction.input_data = ProcessedInput(
                    content=metadata["input"]["content"],
                    input_type=input_type,
                    metadata=metadata["input"].get("metadata", {}),
                    raw_data=raw_data
                )
            
            # Load generated content
            if metadata.get("output"):
                support_text = ""
                poem_text = ""
                
                # Load support text using optimized reading
                if metadata["output"].get("support_file"):
                    support_path = self.base_path / metadata["output"]["support_file"]
                    if support_path.exists():
                        support_text = self._read_file_optimized(support_path) or ""
                
                # Load poem text using optimized reading
                if metadata["output"].get("poem_file"):
                    poem_path = self.base_path / metadata["output"]["poem_file"]
                    if poem_path.exists():
                        poem_text = self._read_file_optimized(poem_path) or ""
                
                if support_text or poem_text:
                    interaction.generated_content = GeneratedContent(
                        supportive_statement=support_text,
                        poem=poem_text,
                        generation_metadata=metadata.get("generation_meta", {})
                    )
            
            # Load audio files
            if metadata.get("output"):
                for audio_key in ["support_audio", "poem_audio", "remix_audio"]:
                    if metadata["output"].get(audio_key):
                        audio_path = self.base_path / metadata["output"][audio_key]
                        if audio_path.exists():
                            audio_file = AudioFile(
                                file_path=str(audio_path),
                                format="wav",
                                metadata={"type": audio_key.replace("_audio", "")}
                            )
                            interaction.audio_files.append(audio_file)
            
            # Set file paths
            interaction.file_paths = metadata.get("output", {})
            
            return interaction
            
        except Exception as e:
            raise StorageError(f"Failed to load interaction: {e}")
    
    @monitor_performance("load_user_history")
    def load_user_history(self, user: User) -> List[Interaction]:
        """
        Load complete interaction history for a user.
        
        Args:
            user: User object
            
        Returns:
            List of Interaction objects
        """
        try:
            interactions = []
            
            # Create progress tracker for loading history
            total_prompts = len(user.prompts)
            if total_prompts > 5:  # Only show progress for larger histories
                progress = ProgressTracker(total_prompts, "Loading interaction history")
                
                for i, prompt_meta in enumerate(user.prompts):
                    progress.update(i + 1, f"Loading interaction {i + 1}/{total_prompts}")
                    interaction_id = prompt_meta.get("id")
                    if interaction_id:
                        interaction = self.load_interaction(user.nickname, interaction_id)
                        if interaction:
                            interactions.append(interaction)
                
                progress.complete("History loaded")
            else:
                # Load without progress tracking for small histories
                for prompt_meta in user.prompts:
                    interaction_id = prompt_meta.get("id")
                    if interaction_id:
                        interaction = self.load_interaction(user.nickname, interaction_id)
                        if interaction:
                            interactions.append(interaction)
            
            # Sort by timestamp (newest first)
            interactions.sort(key=lambda x: x.timestamp, reverse=True)
            
            return interactions
            
        except Exception as e:
            raise StorageError(f"Failed to load user history: {e}")
    
    def delete_interaction(self, nickname: str, interaction_id: str) -> bool:
        """
        Delete an interaction and all associated files.
        
        Args:
            nickname: User's nickname
            interaction_id: ID of the interaction to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            interaction_dir = self._get_interaction_directory(nickname, interaction_id)
            
            if interaction_dir.exists():
                shutil.rmtree(interaction_dir)
            
            # Remove from user's prompt history
            user = self.load_user_profile(nickname)
            if user:
                user.prompts = [p for p in user.prompts if p.get("id") != interaction_id]
                self.save_user_profile(user)
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete interaction: {e}")
    
    def get_storage_stats(self, nickname: str) -> Dict[str, Any]:
        """
        Get storage statistics for a user.
        
        Args:
            nickname: User's nickname
            
        Returns:
            Dictionary containing storage statistics
        """
        try:
            user_dir = self._get_user_directory(nickname)
            
            if not user_dir.exists():
                return {"total_size": 0, "interaction_count": 0, "file_count": 0}
            
            total_size = 0
            file_count = 0
            interaction_count = 0
            
            for item in user_dir.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir() and item.parent == user_dir:
                    interaction_count += 1
            
            return {
                "total_size": total_size,
                "interaction_count": interaction_count,
                "file_count": file_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {e}")
    
    def _read_file_optimized(self, file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """
        Optimized file reading with caching.
        
        Args:
            file_path: Path to file
            encoding: File encoding
            
        Returns:
            File content or None if failed
        """
        try:
            # Use performance optimizer for file operations
            content = self.performance_optimizer.optimize_file_operations(str(file_path), "read")
            return content
        except Exception as e:
            raise StorageError(f"Failed to read file {file_path}: {e}")
    
    def _write_file_optimized(self, file_path: Path, content: str, encoding: str = 'utf-8'):
        """
        Optimized file writing with batching support.
        
        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding
        """
        def write_operation():
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
            except Exception as e:
                raise StorageError(f"Failed to write file {file_path}: {e}")
        
        # Add to batch operations for better performance
        self.pending_operations.append(write_operation)
        
        # Execute batch if it reaches the limit
        if len(self.pending_operations) >= self.batch_size:
            self._execute_batch_operations()
    
    def _execute_batch_operations(self):
        """Execute all pending file operations in batch."""
        if not self.pending_operations:
            return
        
        operations = self.pending_operations.copy()
        self.pending_operations.clear()
        
        # Use performance optimizer for batch operations
        self.performance_optimizer.batch_file_operations(operations, delay=0.05)
    
    def flush_pending_operations(self):
        """Force execution of all pending operations."""
        self._execute_batch_operations()
    
    def _create_interaction_metadata(self, interaction: Interaction) -> Dict[str, Any]:
        """
        Create metadata dictionary for an interaction.
        
        Args:
            interaction: Interaction object
            
        Returns:
            Dictionary containing interaction metadata
        """
        metadata = {
            "id": interaction.id,
            "timestamp": interaction.timestamp.isoformat(),
            "version": "1.0"
        }
        
        # Input metadata
        if interaction.input_data:
            metadata["input"] = {
                "type": interaction.input_data.input_type.value,
                "content": interaction.input_data.content,
                "metadata": interaction.input_data.metadata
            }
            
            # Add raw file reference if it was saved
            if "raw_input" in interaction.file_paths:
                metadata["input"]["raw_file"] = interaction.file_paths["raw_input"]
        
        # Output metadata
        if interaction.generated_content or interaction.audio_files or interaction.file_paths:
            metadata["output"] = {}
            
            # Text files
            if "support_file" in interaction.file_paths:
                metadata["output"]["support_file"] = interaction.file_paths["support_file"]
            if "poem_file" in interaction.file_paths:
                metadata["output"]["poem_file"] = interaction.file_paths["poem_file"]
            
            # Audio files
            for audio_file in interaction.audio_files:
                if "support" in audio_file.file_path.lower():
                    metadata["output"]["support_audio"] = audio_file.file_path
                elif "poem" in audio_file.file_path.lower():
                    metadata["output"]["poem_audio"] = audio_file.file_path
                elif "remix" in audio_file.file_path.lower():
                    metadata["output"]["remix_audio"] = audio_file.file_path
            
            # Raw input file
            if "raw_input" in interaction.file_paths:
                if interaction.input_data and interaction.input_data.input_type.value == "drawing":
                    metadata["output"]["sketch_file"] = interaction.file_paths["raw_input"]
        
        # Generation metadata
        if interaction.generated_content and interaction.generated_content.generation_metadata:
            metadata["generation_meta"] = interaction.generated_content.generation_metadata
        
        return metadata


class FileManager:
    """
    Utility class for file operations and path management.
    """
    
    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Path to the directory
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Create a safe filename by removing/replacing problematic characters.
        
        Args:
            filename: Original filename
            
        Returns:
            str: Safe filename
        """
        # Remove or replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        safe_name = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Ensure it's not empty and doesn't start with a dot
        if not safe_name or safe_name.startswith("."):
            safe_name = "file_" + safe_name
        
        return safe_name[:255]  # Limit length
    
    @staticmethod
    def get_file_size(path: Path) -> int:
        """
        Get file size in bytes.
        
        Args:
            path: Path to the file
            
        Returns:
            int: File size in bytes, 0 if file doesn't exist
        """
        try:
            return path.stat().st_size if path.exists() else 0
        except OSError:
            return 0
    
    @staticmethod
    def copy_file_safe(src: Path, dest: Path) -> bool:
        """
        Safely copy a file with error handling.
        
        Args:
            src: Source file path
            dest: Destination file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return True
        except (OSError, shutil.Error):
            return False


class HistoryManager:
    """
    Specialized manager for user interaction history operations.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Initialize with a storage manager instance.
        
        Args:
            storage_manager: StorageManager instance
        """
        self.storage = storage_manager
    
    def get_recent_interactions(self, user: User, limit: int = 10) -> List[Interaction]:
        """
        Get the most recent interactions for a user.
        
        Args:
            user: User object
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent Interaction objects
        """
        try:
            all_interactions = self.storage.load_user_history(user)
            return all_interactions[:limit]
        except Exception as e:
            raise StorageError(f"Failed to get recent interactions: {e}")
    
    def search_interactions(self, user: User, query: str) -> List[Interaction]:
        """
        Search interactions by content.
        
        Args:
            user: User object
            query: Search query string
            
        Returns:
            List of matching Interaction objects
        """
        try:
            all_interactions = self.storage.load_user_history(user)
            matching_interactions = []
            
            query_lower = query.lower()
            
            for interaction in all_interactions:
                # Search in input content
                if (interaction.input_data and 
                    query_lower in interaction.input_data.content.lower()):
                    matching_interactions.append(interaction)
                    continue
                
                # Search in generated content
                if interaction.generated_content:
                    if (query_lower in interaction.generated_content.supportive_statement.lower() or
                        query_lower in interaction.generated_content.poem.lower()):
                        matching_interactions.append(interaction)
            
            return matching_interactions
            
        except Exception as e:
            raise StorageError(f"Failed to search interactions: {e}")
    
    def get_interaction_summary(self, user: User) -> Dict[str, Any]:
        """
        Get summary statistics for user's interaction history.
        
        Args:
            user: User object
            
        Returns:
            Dictionary containing summary statistics
        """
        try:
            interactions = self.storage.load_user_history(user)
            
            if not interactions:
                return {
                    "total_interactions": 0,
                    "input_types": {},
                    "date_range": None,
                    "avg_content_length": 0
                }
            
            # Count input types
            input_types = {}
            total_content_length = 0
            
            for interaction in interactions:
                if interaction.input_data:
                    input_type = interaction.input_data.input_type.value
                    input_types[input_type] = input_types.get(input_type, 0) + 1
                    total_content_length += len(interaction.input_data.content)
            
            # Date range
            timestamps = [i.timestamp for i in interactions]
            date_range = {
                "earliest": min(timestamps).isoformat(),
                "latest": max(timestamps).isoformat()
            }
            
            return {
                "total_interactions": len(interactions),
                "input_types": input_types,
                "date_range": date_range,
                "avg_content_length": total_content_length // len(interactions) if interactions else 0
            }
            
        except Exception as e:
            raise StorageError(f"Failed to get interaction summary: {e}")