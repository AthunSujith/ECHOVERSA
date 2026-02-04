"""
Content generation system for EchoVerse companion application.
Provides AI-powered content generation with fallback mechanisms for supportive statements and poems.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

from data_models import ProcessedInput, GeneratedContent
from defensive_system import (
    defensive_wrapper, safe_api_call, get_defensive_logger, 
    get_degradation_manager, get_notification_manager, SeverityLevel
)
from performance_optimizer import (
    get_performance_optimizer, monitor_performance, cache_result,
    LoadingIndicator, ProgressTracker
)

# Try to import local model dependencies with defensive handling
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from model_manager import get_model_registry, get_model_spec
from pathlib import Path

# Initialize defensive systems
logger = get_defensive_logger("content_generator")
degradation_manager = get_degradation_manager()
notification_manager = get_notification_manager()


class ContentGeneratorInterface(ABC):
    """Abstract base class for content generators."""
    
    @abstractmethod
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """
        Generate supportive statement and poem based on input data.
        
        Args:
            input_data: Processed input from user
            
        Returns:
            GeneratedContent with supportive statement and poem
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the generator is available and functional.
        
        Returns:
            bool: True if generator is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_generator_name(self) -> str:
        """
        Get the name/identifier of the generator.
        
        Returns:
            str: Generator name
        """
        pass


class MockGenerator(ContentGeneratorInterface):
    """Mock content generator for fallback and testing purposes."""
    
    def __init__(self):
        """Initialize mock generator."""
        self.name = "mock"
        self._available = True
    
    @defensive_wrapper(fallback_value=None, component_name="mock_generator")
    @monitor_performance("mock_content_generation")
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """
        Generate mock supportive content and poem.
        
        Args:
            input_data: Processed input from user
            
        Returns:
            GeneratedContent with mock supportive statement and poem
        """
        start_time = time.time()
        
        try:
            # Generate contextual supportive statement
            support_templates = [
                "I hear you, and your feelings are completely valid. What you're experiencing matters, and you have the strength to navigate through this.",
                "Thank you for sharing your thoughts with me. You're not alone in feeling this way, and it's okay to take things one step at a time.",
                "Your perspective is valuable and unique. Remember that it's perfectly normal to have complex emotions, and you're doing better than you think.",
                "I appreciate you opening up about this. You have an inner resilience that will help guide you through whatever you're facing.",
                "What you've shared shows real courage and self-awareness. Trust in your ability to find your way forward, even when things feel uncertain."
            ]
            
            poem_templates = [
                "In quiet moments, wisdom grows,\nThrough gentle thoughts, your spirit knows\nThat every step, however small,\nLeads to strength that conquers all.",
                "Like morning light through clouded skies,\nYour inner truth will always rise.\nEach breath you take, each word you say,\nBrings hope and peace to light your way.",
                "In the garden of your mind,\nPlant seeds of love, both strong and kind.\nWith patience, care, and gentle grace,\nYou'll bloom in your own time and space.",
                "Rivers flow through rocky ground,\nYet always make their way around.\nLike water finding its true course,\nYou carry wisdom, strength, and force.",
                "Stars shine brightest in the night,\nYour spirit glows with inner light.\nThrough every season, joy and pain,\nYour heart will learn to love again."
            ]
            
            # Validate input data
            if not input_data or not hasattr(input_data, 'content'):
                logger.logger.warning("Invalid input data provided to mock generator")
                content_hash = 0
            else:
                # Select templates based on input content hash for consistency
                content_hash = hash(input_data.content) % len(support_templates)
            
            supportive_statement = support_templates[content_hash]
            poem = poem_templates[content_hash]
            
            processing_time = time.time() - start_time
            
            metadata = {
                "generator": self.name,
                "processing_time": processing_time,
                "input_type": input_data.input_type.value if input_data and hasattr(input_data, 'input_type') else 'unknown',
                "content_length": len(input_data.content) if input_data and hasattr(input_data, 'content') else 0,
                "template_index": content_hash,
                "fallback_used": False
            }
            
            logger.logger.info(f"Mock generator created content in {processing_time:.2f}s")
            
            return GeneratedContent(
                supportive_statement=supportive_statement,
                poem=poem,
                generation_metadata=metadata
            )
            
        except Exception as e:
            logger.logger.error(f"Mock generator failed unexpectedly: {e}")
            # Emergency fallback
            return GeneratedContent(
                supportive_statement="I'm here to support you through this moment.",
                poem="In every challenge, strength is found,\nYour spirit's light will come around.",
                generation_metadata={
                    "generator": self.name,
                    "processing_time": time.time() - start_time,
                    "error": str(e),
                    "emergency_fallback": True
                }
            )
    
    def is_available(self) -> bool:
        """Mock generator is always available."""
        return self._available
    
    def get_generator_name(self) -> str:
        """Return generator name."""
        return self.name


class GeminiGenerator(ContentGeneratorInterface):
    """Google Gemini API content generator."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini generator.
        
        Args:
            api_key: Google Gemini API key (optional, can be set via environment)
        """
        self.name = "gemini"
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._available = False
        
        # Try to initialize Gemini client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client if possible."""
        try:
            import google.generativeai as genai
            
            if not self.api_key:
                logger.logger.warning("Gemini API key not found. Generator will be unavailable.")
                return
            
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel('gemini-pro')
            self._available = True
            logger.logger.info("Gemini generator initialized successfully")
            
        except ImportError:
            logger.logger.warning("Google Generative AI library not installed. Gemini generator unavailable.")
        except Exception as e:
            logger.logger.error(f"Failed to initialize Gemini client: {e}")
    
    @monitor_performance("gemini_content_generation")
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """
        Generate supportive content using Gemini API with defensive error handling.
        
        Args:
            input_data: Processed input from user
            
        Returns:
            GeneratedContent with AI-generated supportive statement and poem
            
        Raises:
            RuntimeError: If generator is not available
        """
        if not self.is_available():
            degradation_manager.register_component_failure(
                component="gemini_api",
                error=Exception("Gemini API not available"),
                fallback_description="Mock generator"
            )
            raise RuntimeError("Gemini generator is not available")
        
        def gemini_api_call():
            # Create prompts for supportive statement and poem
            support_prompt = self._create_support_prompt(input_data)
            poem_prompt = self._create_poem_prompt(input_data)
            
            # Generate supportive statement
            support_response = self._client.generate_content(support_prompt)
            supportive_statement = support_response.text.strip()
            
            # Generate poem
            poem_response = self._client.generate_content(poem_prompt)
            poem = poem_response.text.strip()
            
            return supportive_statement, poem
        
        def fallback_generation():
            logger.logger.warning("Using fallback generation for Gemini API failure")
            # Simple fallback generation
            return (
                "I understand what you're going through, and I want you to know that your feelings are valid and important.",
                "Through every storm and gentle breeze,\nYour heart will find its way to peace.\nWith time and care, you'll clearly see\nThe strength that lives inside of thee."
            )
        
        start_time = time.time()
        
        try:
            result, success = safe_api_call(
                api_name="gemini_api",
                api_function=gemini_api_call,
                fallback_function=fallback_generation,
                max_retries=2,
                timeout=30.0
            )
            
            if result:
                supportive_statement, poem = result
                processing_time = time.time() - start_time
                
                metadata = {
                    "generator": self.name,
                    "processing_time": processing_time,
                    "input_type": input_data.input_type.value if hasattr(input_data, 'input_type') else 'unknown',
                    "content_length": len(input_data.content) if hasattr(input_data, 'content') else 0,
                    "support_length": len(supportive_statement),
                    "poem_length": len(poem),
                    "api_success": success,
                    "fallback_used": not success
                }
                
                if success:
                    logger.logger.info(f"Gemini generator created content in {processing_time:.2f}s")
                else:
                    logger.logger.warning(f"Gemini fallback used, content created in {processing_time:.2f}s")
                    degradation_manager.register_component_degradation(
                        component="gemini_api",
                        reason="API call failed",
                        impact="Using simplified content generation",
                        severity=SeverityLevel.MEDIUM
                    )
                
                return GeneratedContent(
                    supportive_statement=supportive_statement,
                    poem=poem,
                    generation_metadata=metadata
                )
            else:
                raise RuntimeError("Both Gemini API and fallback failed")
                
        except Exception as e:
            logger.logger.error(f"Gemini generation completely failed: {e}")
            degradation_manager.register_component_failure(
                component="gemini_api",
                error=e,
                fallback_description="Mock generator will be used"
            )
            raise RuntimeError(f"Content generation failed: {e}")
    
    def _create_support_prompt(self, input_data: ProcessedInput) -> str:
        """Create prompt for supportive statement generation."""
        base_prompt = """You are a compassionate AI companion. Based on the user's input, provide a warm, supportive, and empathetic response that:
1. Acknowledges their feelings and experiences
2. Offers gentle encouragement and validation
3. Is personal but not overly familiar
4. Is 2-3 sentences long
5. Focuses on emotional support and understanding

User input: {content}

Provide only the supportive response, no additional text or formatting."""
        
        return base_prompt.format(content=input_data.content)
    
    def _create_poem_prompt(self, input_data: ProcessedInput) -> str:
        """Create prompt for poem generation."""
        base_prompt = """Based on the user's input, write a short, uplifting poem that:
1. Reflects themes from their input in a positive light
2. Is 4-8 lines long
3. Has a gentle, hopeful tone
4. Uses simple, accessible language
5. Offers comfort and inspiration

User input: {content}

Provide only the poem, no title or additional text."""
        
        return base_prompt.format(content=input_data.content)
    
    def is_available(self) -> bool:
        """Check if Gemini generator is available."""
        return self._available and self._client is not None
    
    def get_generator_name(self) -> str:
        """Return generator name."""
        return self.name


class OpenAIGenerator(ContentGeneratorInterface):
    """OpenAI GPT content generator."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI generator.
        
        Args:
            api_key: OpenAI API key (optional, can be set via environment)
        """
        self.name = "openai-gpt4"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._available = False
        
        # Try to initialize OpenAI client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client if possible."""
        try:
            from openai import OpenAI
            
            if not self.api_key:
                logger.logger.warning("OpenAI API key not found. Generator will be unavailable.")
                return
            
            self._client = OpenAI(api_key=self.api_key)
            self._available = True
            logger.logger.info("OpenAI generator initialized successfully")
            
        except ImportError:
            logger.logger.warning("OpenAI library not installed. Generator unavailable.")
        except Exception as e:
            logger.logger.error(f"Failed to initialize OpenAI client: {e}")
    
    @monitor_performance("openai_content_generation")
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """
        Generate supportive content using OpenAI API.
        """
        if not self.is_available():
            degradation_manager.register_component_failure(
                component="openai_api",
                error=Exception("OpenAI API not available"),
                fallback_description="Mock generator"
            )
            raise RuntimeError("OpenAI generator is not available")
        
        def openai_api_call():
            # Create prompts
            support_system = "You are a compassionate AI companion. Provide a warm, supportive, and empathetic response (2-3 sentences) acknowledging the user's feelings."
            poem_system = "You are an uplifting poet. Write a short, hopeful poem (4-8 lines) based on the user's input. Provide ONLY request in output."
            
            # Generate supportive statement
            support_response = self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": support_system},
                    {"role": "user", "content": input_data.content}
                ],
                temperature=0.7
            )
            supportive_statement = support_response.choices[0].message.content.strip()
            
            # Generate poem
            poem_response = self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": poem_system},
                    {"role": "user", "content": input_data.content}
                ],
                temperature=0.7
            )
            poem = poem_response.choices[0].message.content.strip()
            
            return supportive_statement, poem
        
        def fallback_generation():
            logger.logger.warning("Using fallback generation for OpenAI API failure")
            return (
                "I hear you and I'm here for you. Your feelings are valid.",
                "In shadows deep or light of day,\nHope will always find a way."
            )
        
        start_time = time.time()
        
        try:
            result, success = safe_api_call(
                api_name="openai_api",
                api_function=openai_api_call,
                fallback_function=fallback_generation,
                max_retries=2,
                timeout=30.0
            )
            
            if result:
                supportive_statement, poem = result
                processing_time = time.time() - start_time
                
                metadata = {
                    "generator": self.name,
                    "processing_time": processing_time,
                    "input_type": input_data.input_type.value if hasattr(input_data, 'input_type') else 'unknown',
                    "content_length": len(input_data.content) if hasattr(input_data, 'content') else 0,
                    "api_success": success,
                    "fallback_used": not success
                }
                
                if success:
                    logger.logger.info(f"OpenAI generator created content in {processing_time:.2f}s")
                else:
                    logger.logger.warning("OpenAI fallback used")
                    
                return GeneratedContent(
                    supportive_statement=supportive_statement,
                    poem=poem,
                    generation_metadata=metadata
                )
            else:
                raise RuntimeError("OpenAI generation failed")
                
        except Exception as e:
            logger.logger.error(f"OpenAI generation failed: {e}")
            raise RuntimeError(f"Content generation failed: {e}")

    def is_available(self) -> bool:
        return self._available and self._client is not None
    
    def get_generator_name(self) -> str:
        return self.name


class LocalModelGenerator(ContentGeneratorInterface):
    """Local model generator using GGUF models with llama.cpp."""
    
    def __init__(self, model_name: str = "tinyllama-1.1b-chat-gguf-q4"):
        """
        Initialize local model generator.
        
        Args:
            model_name: Name of the model to use
        """
        self.name = f"LocalModel-{model_name}"
        self.model_name = model_name
        self.model = None
        self._available = False
        
        if not LLAMA_CPP_AVAILABLE:
            logger.logger.warning("llama-cpp-python not available for local models")
            return
        
        try:
            self._load_model()
        except Exception as e:
            logger.logger.error(f"Failed to initialize local model {model_name}: {e}")
    
    def _load_model(self):
        """Load the local model."""
        # Get model specification
        model_spec = get_model_spec(self.model_name)
        if not model_spec:
            raise ValueError(f"Model {self.model_name} not found in registry")
        
        # Find model file
        model_path = self._find_model_file()
        if not model_path:
            raise FileNotFoundError(f"Model file not found for {self.model_name}")
        
        logger.logger.info(f"Loading local model from {model_path}")
        
        # Initialize llama.cpp model
        self.model = Llama(
            model_path=str(model_path),
            n_ctx=2048,  # Context window
            n_threads=4,  # CPU threads
            verbose=False
        )
        
        self._available = True
        logger.logger.info(f"Successfully loaded local model: {self.model_name}")
    
    def _find_model_file(self) -> Optional[Path]:
        """Find the model file in the download directory."""
        base_path = Path("download/models") / self.model_name
        
        if not base_path.exists():
            return None
        
        # Look for .gguf files
        gguf_files = list(base_path.glob("*.gguf"))
        if gguf_files:
            return gguf_files[0]
        
        return None
    
    @monitor_performance("local_model_content_generation")
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """Generate supportive content using local model."""
        if not self.is_available():
            raise RuntimeError("Local model generator is not available")
        
        start_time = time.time()
        
        try:
            # Generate supportive statement
            support_prompt = self._create_support_prompt(input_data)
            supportive_statement = self._generate_text(support_prompt)
            
            # Generate poem
            poem_prompt = self._create_poem_prompt(input_data)
            poem = self._generate_text(poem_prompt)
            
            processing_time = time.time() - start_time
            
            # Create metadata
            metadata = {
                "generator": self.name,
                "model_name": self.model_name,
                "processing_time": processing_time,
                "input_type": input_data.input_type.value,
                "content_length": len(input_data.content),
                "support_length": len(supportive_statement),
                "poem_length": len(poem)
            }
            
            logger.logger.info(f"Local model generated content in {processing_time:.2f}s")
            
            return GeneratedContent(
                supportive_statement=supportive_statement,
                poem=poem,
                generation_metadata=metadata
            )
            
        except Exception as e:
            logger.logger.error(f"Local model generation failed: {e}")
            raise RuntimeError(f"Content generation failed: {e}")
    
    def _generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        """Generate text using the local model."""
        try:
            # Generate response
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                stop=["User:", "Human:", "\n\n"],
                echo=False
            )
            
            # Extract generated text
            generated_text = response['choices'][0]['text'].strip()
            
            # Clean up the response
            generated_text = self._clean_response(generated_text)
            
            return generated_text
            
        except Exception as e:
            logger.logger.error(f"Text generation failed: {e}")
            return "I'm here to support you through this moment."
    
    def _clean_response(self, text: str) -> str:
        """Clean up generated response."""
        # Remove common artifacts
        text = text.strip()
        
        # Remove any remaining prompt artifacts
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('User:', 'Human:', 'Assistant:', 'AI:', 'Friend:', 'Topic:', 'Poem:')):
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines) if len(cleaned_lines) > 1 else ' '.join(cleaned_lines)
        
        # Ensure reasonable length for supportive statements
        if len(result) > 200:
            sentences = result.split('.')
            result = '. '.join(sentences[:2])
            if not result.endswith('.'):
                result += '.'
        
        return result if result else "I'm here to support you."
    
    def _create_support_prompt(self, input_data: ProcessedInput) -> str:
        """Create prompt for supportive statement generation."""
        prompt = f"""You are a caring friend offering support. Respond with 1-2 sentences that are warm and encouraging.

User: {input_data.content}

Friend: I hear you, and"""
        
        return prompt
    
    def _create_poem_prompt(self, input_data: ProcessedInput) -> str:
        """Create prompt for poem generation."""
        prompt = f"""Write a short, hopeful poem (4 lines) about overcoming challenges.

Topic: {input_data.content}

Poem:
When storms"""
        
        return prompt
    
    def is_available(self) -> bool:
        """Check if local model generator is available."""
        return self._available and self.model is not None
    
    def get_generator_name(self) -> str:
        """Return generator name."""
        return self.name


class ContentGenerator:
    """
    Main content generator that orchestrates different generation backends with fallback logic.
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize content generator with fallback chain.
        
        Args:
            gemini_api_key: Optional Gemini API key
        """
        self.generators = []
        self.current_generator = None
        
        # Initialize generators in priority order
        self._initialize_generators(gemini_api_key)
    
    def _initialize_generators(self, gemini_api_key: Optional[str]):
        """Initialize generators."""
        
        # 1. Try OpenAI (Top Priority if available)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                openai_gen = OpenAIGenerator(openai_key)
                if openai_gen.is_available():
                    self.generators.append(openai_gen)
                    logger.logger.info("OpenAI generator added to chain")
            except Exception as e:
                logger.logger.warning(f"Failed to initialize OpenAI: {e}")

        # 2. Try Gemini (Second Priority)
        # Try Gemini first if key available (Preferred for Cloud/Vercel)
        if gemini_api_key or os.getenv("GEMINI_API_KEY"):
            try:
                gemini_gen = GeminiGenerator(gemini_api_key)
                if gemini_gen.is_available():
                    self.generators.append(gemini_gen)
                    logger.logger.info("Gemini generator added to chain")
            except Exception as e:
                logger.logger.warning(f"Failed to initialize Gemini: {e}")
                
        logger.logger.info("Initializing Local Models as backup")
        
        # Try to initialize local model generator
        try:
            # Try TinyLlama first (most lightweight)
            local_gen = LocalModelGenerator("tinyllama-1.1b-chat-gguf-q4")
            if local_gen.is_available():
                self.generators.append(local_gen)
                logger.logger.info("TinyLlama local generator added to chain")
            else:
                # Try Phi-2 as backup
                local_gen = LocalModelGenerator("phi-2-gguf-q4")
                if local_gen.is_available():
                    self.generators.append(local_gen)
                    logger.logger.info("Phi-2 local generator added to chain")
        except Exception as e:
            logger.logger.warning(f"Failed to initialize local model generator: {e}")
        
        # Always add mock generator as fallback
        mock_gen = MockGenerator()
        self.generators.append(mock_gen)
        logger.logger.info("Mock generator added as fallback")
        
        # Set current generator to first available
        if self.generators:
            self.current_generator = self.generators[0]
            logger.logger.info(f"Using {self.current_generator.get_generator_name()} as primary generator")
    
    @monitor_performance("content_generation_with_fallback")
    def generate_support_and_poem(self, input_data: ProcessedInput) -> GeneratedContent:
        """
        Generate supportive content with automatic fallback.
        
        Args:
            input_data: Processed input from user
            
        Returns:
            GeneratedContent with supportive statement and poem
            
        Raises:
            RuntimeError: If all generators fail
        """
        last_error = None
        
        # Create progress tracker for generation attempts
        progress = ProgressTracker(len(self.generators), "Generating supportive content")
        
        try:
            for i, generator in enumerate(self.generators):
                progress.update(i + 1, f"Trying {generator.get_generator_name()}")
                
                try:
                    if generator.is_available():
                        logger.logger.info(f"Attempting generation with {generator.get_generator_name()}")
                        result = generator.generate_support_and_poem(input_data)
                        self.current_generator = generator
                        progress.complete(f"Generated with {generator.get_generator_name()}")
                        return result
                    else:
                        logger.logger.warning(f"{generator.get_generator_name()} is not available")
                except Exception as e:
                    logger.logger.error(f"{generator.get_generator_name()} failed: {e}")
                    last_error = e
                    continue
            
            # If we get here, all generators failed
            progress.complete("All generators failed")
            raise RuntimeError(f"All content generators failed. Last error: {last_error}")
            
        except Exception as e:
            progress.complete(f"Error: {str(e)}")
            raise
    
    def is_gemini_available(self) -> bool:
        """
        Check if Gemini generator is available.
        
        Returns:
            bool: True if Gemini is available, False otherwise
        """
        for generator in self.generators:
            if isinstance(generator, GeminiGenerator):
                return generator.is_available()
        return False
    
    def get_current_generator_name(self) -> str:
        """
        Get the name of the currently active generator.
        
        Returns:
            str: Current generator name
        """
        if self.current_generator:
            return self.current_generator.get_generator_name()
        return "none"
    
    def get_available_generators(self) -> list[str]:
        """
        Get list of available generator names.
        
        Returns:
            List of available generator names
        """
        return [gen.get_generator_name() for gen in self.generators if gen.is_available()]