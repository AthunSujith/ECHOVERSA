"""
Core data models for EchoVerse companion application.
Defines data classes and validation functions for user data, input processing,
content generation, and interaction management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import uuid
import re


class InputType(Enum):
    """Enumeration of supported input types."""
    TEXT = "text"
    AUDIO = "audio"
    DRAWING = "drawing"


@dataclass
class User:
    """User profile data model."""
    nickname: str
    password: str  # Note: In production, this should be hashed
    created: datetime = field(default_factory=datetime.now)
    preferences: Dict[str, Any] = field(default_factory=dict)
    prompts: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate user data after initialization."""
        if not self.nickname or not isinstance(self.nickname, str):
            raise ValueError("Nickname must be a non-empty string")
        if not self.password or not isinstance(self.password, str):
            raise ValueError("Password must be a non-empty string")
        if len(self.nickname) < 2:
            raise ValueError("Nickname must be at least 2 characters long")
        if len(self.password) < 4:
            raise ValueError("Password must be at least 4 characters long")


@dataclass
class ProcessedInput:
    """Processed input data from various input sources."""
    content: str
    input_type: InputType
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Optional[bytes] = None
    transcription: Optional[str] = None  # For audio inputs with Whisper transcription
    
    def __post_init__(self):
        """Validate processed input data."""
        if not self.content or not isinstance(self.content, str):
            raise ValueError("Content must be a non-empty string")
        if not isinstance(self.input_type, InputType):
            raise ValueError("Input type must be a valid InputType enum")
        if self.transcription is not None and not isinstance(self.transcription, str):
            raise ValueError("Transcription must be a string if provided")


@dataclass
class GeneratedContent:
    """AI-generated content including supportive statements and poems."""
    supportive_statement: str
    poem: str
    generation_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate generated content."""
        if not self.supportive_statement or not isinstance(self.supportive_statement, str):
            raise ValueError("Supportive statement must be a non-empty string")
        if not self.poem or not isinstance(self.poem, str):
            raise ValueError("Poem must be a non-empty string")


@dataclass
class AudioFile:
    """Audio file data model."""
    file_path: str
    duration: Optional[float] = None
    format: str = "wav"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate audio file data."""
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("File path must be a non-empty string")


@dataclass
class Interaction:
    """Complete interaction data including input, generated content, and outputs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    input_data: Optional[ProcessedInput] = None
    generated_content: Optional[GeneratedContent] = None
    audio_files: List[AudioFile] = field(default_factory=list)
    file_paths: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate interaction data."""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("ID must be a non-empty string")


# Validation Functions

def validate_nickname(nickname: str) -> bool:
    """
    Validate user nickname format and constraints.
    
    Args:
        nickname: The nickname to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(nickname, str):
        return False
    if len(nickname) < 2 or len(nickname) > 50:
        return False
    # Allow alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', nickname):
        return False
    return True


def validate_password(password: str) -> bool:
    """
    Validate password strength and format.
    
    Args:
        password: The password to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(password, str):
        return False
    if len(password) < 4:  # Minimum length for basic security
        return False
    if len(password) > 128:  # Maximum reasonable length
        return False
    return True


def validate_input_content(content: str, input_type: InputType) -> bool:
    """
    Validate input content based on type.
    
    Args:
        content: The content to validate
        input_type: The type of input
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(content, str) or not content.strip():
        return False
    
    if input_type == InputType.TEXT:
        # Text input should be reasonable length
        return len(content) <= 10000
    elif input_type == InputType.AUDIO:
        # Audio content is typically a description or transcription
        return len(content) <= 50000
    elif input_type == InputType.DRAWING:
        # Drawing content is typically a description
        return len(content) <= 5000
    
    return False


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path format and safety.
    
    Args:
        file_path: The file path to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return False
    
    # Basic path traversal protection
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    # Should be a relative path within the project
    return True


def create_interaction_metadata(input_data: ProcessedInput, 
                              generated_content: GeneratedContent,
                              processing_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create metadata dictionary for an interaction.
    
    Args:
        input_data: The processed input data
        generated_content: The generated content
        processing_info: Additional processing information
        
    Returns:
        Dict containing interaction metadata
    """
    return {
        "input_type": input_data.input_type.value,
        "content_length": len(input_data.content),
        "support_length": len(generated_content.supportive_statement),
        "poem_length": len(generated_content.poem),
        "processing_time": processing_info.get("processing_time", 0),
        "model_used": processing_info.get("model_used", "unknown"),
        "tts_engine": processing_info.get("tts_engine", "unknown"),
        "created_at": datetime.now().isoformat()
    }


# Data integrity validation functions

def validate_user_data_integrity(user: User) -> List[str]:
    """
    Comprehensive validation of user data integrity.
    
    Args:
        user: User object to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    try:
        if not validate_nickname(user.nickname):
            errors.append("Invalid nickname format")
        if not validate_password(user.password):
            errors.append("Invalid password format")
        if not isinstance(user.created, datetime):
            errors.append("Invalid creation timestamp")
        if not isinstance(user.preferences, dict):
            errors.append("Preferences must be a dictionary")
        if not isinstance(user.prompts, list):
            errors.append("Prompts must be a list")
    except Exception as e:
        errors.append(f"User validation error: {str(e)}")
    
    return errors


def validate_interaction_data_integrity(interaction: Interaction) -> List[str]:
    """
    Comprehensive validation of interaction data integrity.
    
    Args:
        interaction: Interaction object to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    try:
        if not interaction.id or not isinstance(interaction.id, str):
            errors.append("Invalid interaction ID")
        if not isinstance(interaction.timestamp, datetime):
            errors.append("Invalid timestamp")
        if interaction.input_data and not isinstance(interaction.input_data, ProcessedInput):
            errors.append("Invalid input data type")
        if interaction.generated_content and not isinstance(interaction.generated_content, GeneratedContent):
            errors.append("Invalid generated content type")
        if not isinstance(interaction.audio_files, list):
            errors.append("Audio files must be a list")
        if not isinstance(interaction.file_paths, dict):
            errors.append("File paths must be a dictionary")
            
        # Validate audio files
        for audio_file in interaction.audio_files:
            if not isinstance(audio_file, AudioFile):
                errors.append("Invalid audio file type in list")
                break
                
    except Exception as e:
        errors.append(f"Interaction validation error: {str(e)}")
    
    return errors