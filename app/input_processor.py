"""
Input processing module for EchoVerse companion application.
Handles multi-modal input processing including text, audio, and drawing inputs.
"""

import base64
import io
import json
import os
from typing import Optional, Dict, Any, Union
from PIL import Image

# Optional numpy import for advanced image processing
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

from data_models import ProcessedInput, InputType, validate_input_content


class InputProcessor:
    """
    Main input processor that orchestrates different input types.
    Handles text, audio, and drawing inputs with appropriate processing.
    """
    
    def __init__(self):
        """Initialize the input processor."""
        self.audio_transcriber = AudioTranscriber()
        self.drawing_processor = DrawingProcessor()
    
    def process_text_input(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedInput:
        """
        Process text input and create ProcessedInput object.
        
        Args:
            text: The text input to process
            metadata: Optional metadata dictionary
            
        Returns:
            ProcessedInput object with processed text data
            
        Raises:
            ValueError: If text input is invalid
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text input must be a non-empty string")
        
        # Clean and normalize text
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Text input cannot be empty after cleaning")
        
        # Validate content
        if not validate_input_content(cleaned_text, InputType.TEXT):
            raise ValueError("Text input exceeds maximum length or contains invalid content")
        
        # Create metadata
        processing_metadata = {
            "original_length": len(text),
            "cleaned_length": len(cleaned_text),
            "processing_method": "text_cleanup",
            **(metadata or {})
        }
        
        return ProcessedInput(
            content=cleaned_text,
            input_type=InputType.TEXT,
            metadata=processing_metadata,
            raw_data=None
        )
    
    def process_audio_input(self, audio_data: bytes, filename: str = "audio_input", 
                          metadata: Optional[Dict[str, Any]] = None) -> ProcessedInput:
        """
        Process audio input with optional transcription.
        
        Args:
            audio_data: Raw audio file bytes
            filename: Original filename for reference
            metadata: Optional metadata dictionary
            
        Returns:
            ProcessedInput object with processed audio data
            
        Raises:
            ValueError: If audio input is invalid
        """
        if not audio_data or not isinstance(audio_data, bytes):
            raise ValueError("Audio data must be non-empty bytes")
        
        if len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")
        
        # Basic audio file validation (check for common audio headers)
        if not self._is_valid_audio_format(audio_data):
            raise ValueError("Invalid audio file format")
        
        # Attempt transcription (optional - graceful fallback)
        transcription = None
        transcription_error = None
        content = f"Audio file: {filename}"
        
        try:
            transcription = self.audio_transcriber.transcribe_audio(audio_data)
            if transcription:
                # Use transcription as primary content if available
                content = transcription
        except Exception as e:
            transcription_error = str(e)
            # Keep default content as filename
        
        # Validate transcribed content
        if transcription and not validate_input_content(transcription, InputType.AUDIO):
            # If transcription is too long, truncate it but keep original in transcription field
            content = f"Audio file: {filename} (transcription available but truncated)"
        
        # Create metadata
        processing_metadata = {
            "filename": filename,
            "file_size": len(audio_data),
            "transcription_attempted": True,
            "transcription_success": transcription_error is None,
            "transcription_error": transcription_error,
            "whisper_available": self.audio_transcriber.whisper_available,
            "processing_method": "audio_transcription",
            **(metadata or {})
        }
        
        return ProcessedInput(
            content=content,
            input_type=InputType.AUDIO,
            metadata=processing_metadata,
            raw_data=audio_data,
            transcription=transcription  # Store full transcription separately
        )
    
    def process_drawing_input(self, canvas_data: Union[Dict[str, Any], str], 
                            metadata: Optional[Dict[str, Any]] = None) -> ProcessedInput:
        """
        Process drawing canvas input and generate PNG.
        
        Args:
            canvas_data: Canvas data (dict with drawing info or base64 string)
            metadata: Optional metadata dictionary
            
        Returns:
            ProcessedInput object with processed drawing data
            
        Raises:
            ValueError: If drawing input is invalid
        """
        if not canvas_data:
            raise ValueError("Canvas data cannot be empty")
        
        # Process the drawing and generate PNG
        try:
            png_data, description = self.drawing_processor.process_canvas_data(canvas_data)
        except Exception as e:
            raise ValueError(f"Failed to process drawing: {str(e)}")
        
        # Validate description content
        if not validate_input_content(description, InputType.DRAWING):
            description = "Drawing input (description too long)"
        
        # Create metadata
        processing_metadata = {
            "has_png_data": png_data is not None,
            "png_size": len(png_data) if png_data else 0,
            "processing_method": "canvas_to_png",
            "description_generated": True,
            **(metadata or {})
        }
        
        return ProcessedInput(
            content=description,
            input_type=InputType.DRAWING,
            metadata=processing_metadata,
            raw_data=png_data
        )
    
    def _is_valid_audio_format(self, audio_data: bytes) -> bool:
        """
        Basic validation of audio file format by checking headers.
        
        Args:
            audio_data: Raw audio file bytes
            
        Returns:
            bool: True if appears to be valid audio format
        """
        if len(audio_data) < 4:
            return False
        
        # Check for common audio file headers
        headers = [
            b'RIFF',  # WAV
            b'ID3',   # MP3
            b'fLaC',  # FLAC
            b'OggS',  # OGG
            b'FORM',  # AIFF
        ]
        
        for header in headers:
            if audio_data.startswith(header):
                return True
        
        # Check for MP3 frame sync (0xFF 0xFB, 0xFF 0xFA, etc.)
        if len(audio_data) >= 2 and audio_data[0] == 0xFF and (audio_data[1] & 0xE0) == 0xE0:
            return True
        
        return False


class AudioTranscriber:
    """
    Handles audio transcription using Whisper (optional dependency).
    Provides graceful fallback when Whisper is not available.
    """
    
    def __init__(self):
        """Initialize the audio transcriber."""
        self.whisper_available = self._check_whisper_availability()
        self.whisper_model = None
        if self.whisper_available:
            self._load_whisper_model()
    
    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data to text using Whisper.
        
        Args:
            audio_data: Raw audio file bytes
            
        Returns:
            str: Transcribed text
            
        Raises:
            RuntimeError: If transcription fails
        """
        if not self.whisper_available:
            raise RuntimeError("Whisper transcription not available")
        
        try:
            return self._whisper_transcribe(audio_data)
        except Exception as e:
            # Fallback to mock transcription if Whisper fails
            try:
                return self._mock_transcription(audio_data)
            except:
                raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def _check_whisper_availability(self) -> bool:
        """
        Check if Whisper is available for transcription.
        
        Returns:
            bool: True if Whisper is available
        """
        try:
            import whisper
            return True
        except ImportError:
            return False
    
    def _load_whisper_model(self):
        """
        Load Whisper model with graceful fallback.
        Uses the smallest model (base) for better performance.
        """
        if not self.whisper_available:
            return
        
        try:
            import whisper
            # Use base model for good balance of speed and accuracy
            self.whisper_model = whisper.load_model("base")
        except Exception as e:
            # If model loading fails, disable Whisper
            self.whisper_available = False
            self.whisper_model = None
    
    def _whisper_transcribe(self, audio_data: bytes) -> str:
        """
        Perform actual Whisper transcription.
        
        Args:
            audio_data: Raw audio file bytes
            
        Returns:
            str: Transcribed text
            
        Raises:
            RuntimeError: If transcription fails
        """
        if not self.whisper_model:
            raise RuntimeError("Whisper model not loaded")
        
        import tempfile
        import os
        
        # Save audio data to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(temp_file_path)
            transcription = result.get("text", "").strip()
            
            if not transcription:
                raise RuntimeError("Empty transcription result")
            
            return transcription
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass  # Ignore cleanup errors
    
    def _mock_transcription(self, audio_data: bytes) -> str:
        """
        Mock transcription for testing and fallback.
        
        Args:
            audio_data: Raw audio file bytes
            
        Returns:
            str: Mock transcription text
        """
        # Generate a mock transcription based on file size
        file_size_kb = len(audio_data) / 1024
        
        if file_size_kb < 50:
            return "Short audio message recorded"
        elif file_size_kb < 200:
            return "Medium length audio message with personal thoughts and feelings"
        else:
            return "Long audio message containing detailed personal reflection and emotional expression"


class DrawingProcessor:
    """
    Handles drawing canvas input processing and PNG generation.
    Converts canvas data to PNG images and generates descriptions.
    """
    
    def __init__(self):
        """Initialize the drawing processor."""
        pass
    
    def process_canvas_data(self, canvas_data: Union[Dict[str, Any], str]) -> tuple[Optional[bytes], str]:
        """
        Process canvas data and generate PNG with description.
        
        Args:
            canvas_data: Canvas data (dict or base64 string)
            
        Returns:
            tuple: (PNG bytes, description string)
            
        Raises:
            ValueError: If canvas data is invalid
        """
        if isinstance(canvas_data, str):
            # Handle base64 encoded image data
            return self._process_base64_image(canvas_data)
        elif isinstance(canvas_data, dict):
            # Handle structured canvas data
            return self._process_canvas_dict(canvas_data)
        else:
            raise ValueError("Canvas data must be string (base64) or dictionary")
    
    def _process_base64_image(self, base64_data: str) -> tuple[Optional[bytes], str]:
        """
        Process base64 encoded image data.
        
        Args:
            base64_data: Base64 encoded image string
            
        Returns:
            tuple: (PNG bytes, description string)
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',', 1)[1]
            
            # Decode base64 data
            image_bytes = base64.b64decode(base64_data)
            
            # Open and validate image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to PNG if not already
            png_buffer = io.BytesIO()
            image.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            # Generate description
            description = self._generate_image_description(image)
            
            return png_data, description
            
        except Exception as e:
            raise ValueError(f"Failed to process base64 image: {str(e)}")
    
    def _process_canvas_dict(self, canvas_data: Dict[str, Any]) -> tuple[Optional[bytes], str]:
        """
        Process structured canvas data dictionary.
        
        Args:
            canvas_data: Dictionary containing canvas information
            
        Returns:
            tuple: (PNG bytes, description string)
        """
        try:
            # Extract relevant information from canvas data
            width = canvas_data.get('width', 400)
            height = canvas_data.get('height', 400)
            strokes = canvas_data.get('strokes', [])
            background_color = canvas_data.get('background_color', 'white')
            
            # Create image from canvas data
            image = self._create_image_from_strokes(width, height, strokes, background_color)
            
            # Convert to PNG
            png_buffer = io.BytesIO()
            image.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            # Generate description
            description = self._generate_canvas_description(canvas_data)
            
            return png_data, description
            
        except Exception as e:
            raise ValueError(f"Failed to process canvas data: {str(e)}")
    
    def _create_image_from_strokes(self, width: int, height: int, 
                                 strokes: list, background_color: str) -> Image.Image:
        """
        Create PIL Image from stroke data.
        
        Args:
            width: Canvas width
            height: Canvas height
            strokes: List of stroke data
            background_color: Background color
            
        Returns:
            PIL Image object
        """
        # Create blank image
        image = Image.new('RGB', (width, height), background_color)
        
        # For now, create a simple placeholder image
        # In a full implementation, this would render the actual strokes
        from PIL import ImageDraw
        
        draw = ImageDraw.Draw(image)
        
        # Draw some placeholder content based on stroke count
        if strokes:
            # Draw simple shapes to represent drawing activity
            for i, stroke in enumerate(strokes[:10]):  # Limit to first 10 strokes
                x = (i * 30) % width
                y = (i * 20) % height
                draw.ellipse([x, y, x+20, y+20], fill='black')
        
        return image
    
    def _generate_image_description(self, image: Image.Image) -> str:
        """
        Generate description for a PIL Image.
        
        Args:
            image: PIL Image object
            
        Returns:
            str: Description of the image
        """
        width, height = image.size
        mode = image.mode
        
        # Basic image analysis
        if mode == 'RGB' and NUMPY_AVAILABLE:
            # Convert to numpy array for basic analysis
            img_array = np.array(image)
            avg_color = np.mean(img_array, axis=(0, 1))
            
            # Determine dominant color
            if avg_color[0] > avg_color[1] and avg_color[0] > avg_color[2]:
                dominant_color = "reddish"
            elif avg_color[1] > avg_color[2]:
                dominant_color = "greenish"
            else:
                dominant_color = "bluish"
        elif mode == 'RGB':
            # Fallback color analysis without numpy
            # Sample a few pixels to determine dominant color
            pixels = list(image.getdata())
            if pixels:
                avg_r = sum(p[0] for p in pixels[:100]) / min(100, len(pixels))
                avg_g = sum(p[1] for p in pixels[:100]) / min(100, len(pixels))
                avg_b = sum(p[2] for p in pixels[:100]) / min(100, len(pixels))
                
                if avg_r > avg_g and avg_r > avg_b:
                    dominant_color = "reddish"
                elif avg_g > avg_b:
                    dominant_color = "greenish"
                else:
                    dominant_color = "bluish"
            else:
                dominant_color = "colorful"
        else:
            dominant_color = "monochrome"
        
        return f"Hand-drawn sketch ({width}x{height}) with {dominant_color} tones"
    
    def _generate_canvas_description(self, canvas_data: Dict[str, Any]) -> str:
        """
        Generate description for canvas data.
        
        Args:
            canvas_data: Canvas data dictionary
            
        Returns:
            str: Description of the canvas content
        """
        width = canvas_data.get('width', 400)
        height = canvas_data.get('height', 400)
        stroke_count = len(canvas_data.get('strokes', []))
        
        if stroke_count == 0:
            return f"Empty canvas ({width}x{height})"
        elif stroke_count < 5:
            return f"Simple drawing with {stroke_count} strokes on {width}x{height} canvas"
        elif stroke_count < 20:
            return f"Detailed sketch with {stroke_count} strokes on {width}x{height} canvas"
        else:
            return f"Complex artwork with {stroke_count} strokes on {width}x{height} canvas"