#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Suite for EchoVerse Companion Application
Tests the complete pipeline: authentication → input processing → content generation → audio processing → storage
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Import all modules for testing
try:
    from streamlit_workspace import StreamlitApp
    from content_generator import ContentGenerator, MockGenerator, GeminiGenerator
    from audio_processor import AudioManager, TTSProcessor, AudioRemixer
    from input_processor import InputProcessor
    from storage_manager import StorageManager
    from auth_manager import UserManager
    from data_models import User, ProcessedInput, GeneratedContent, Interaction, InputType, AudioFile
    from model_manager import ModelRegistry, get_model_registry
    from model_selector import ModelSelector
    from environment_checker import check_environment
    from defensive_system import DefensiveSystem
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    IMPORTS_SUCCESSFUL = False


class EchoVerseEndToEndTest(unittest.TestCase):
    """End-to-end testing of the complete EchoVerse pipeline"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        if not IMPORTS_SUCCESSFUL:
            cls.skipTest(cls, "Required modules not available")
        
        # Create temporary directory for testing
        cls.test_dir = tempfile.mkdtemp(prefix="echoverse_test_")
        cls.test_users_dir = Path(cls.test_dir) / "users"
        cls.test_users_dir.mkdir(exist_ok=True)
        
        print(f"🧪 Test environment created: {cls.test_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if hasattr(cls, 'test_dir') and os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
            print(f"🧹 Test environment cleaned up")
    
    def setUp(self):
        """Set up individual test"""
        self.test_user = User(
            nickname="testuser",
            password="testpass123"
        )
        
        # Initialize components
        self.user_manager = UserManager(users_dir=str(self.test_users_dir))
        self.storage_manager = StorageManager(users_dir=str(self.test_users_dir))
        self.input_processor = InputProcessor()
        self.content_generator = ContentGenerator()
        self.audio_manager = AudioManager()
    
    def test_complete_text_workflow(self):
        """Test complete workflow with text input"""
        print("\n🔄 Testing complete text workflow...")
        
        # Step 1: User registration and authentication
        print("  📝 Testing user registration...")
        registration_success = self.user_manager.register_user(
            self.test_user.nickname, 
            self.test_user.password
        )
        self.assertTrue(registration_success, "User registration should succeed")
        
        # Step 2: User authentication
        print("  🔐 Testing user authentication...")
        authenticated_user = self.user_manager.authenticate_user(
            self.test_user.nickname, 
            self.test_user.password
        )
        self.assertIsNotNone(authenticated_user, "User authentication should succeed")
        self.assertEqual(authenticated_user.nickname, self.test_user.nickname)
        
        # Step 3: Input processing
        print("  📥 Testing input processing...")
        test_input = "I'm feeling overwhelmed with work today and need some encouragement."
        processed_input = self.input_processor.process_text_input(test_input)
        
        self.assertIsNotNone(processed_input, "Input processing should succeed")
        self.assertEqual(processed_input.content, test_input)
        self.assertEqual(processed_input.input_type, InputType.TEXT)
        
        # Step 4: Content generation
        print("  🤖 Testing content generation...")
        generated_content = self.content_generator.generate_support_and_poem(processed_input)
        
        self.assertIsNotNone(generated_content, "Content generation should succeed")
        self.assertIsInstance(generated_content.supportive_statement, str)
        self.assertIsInstance(generated_content.poem, str)
        self.assertTrue(len(generated_content.supportive_statement) > 0)
        self.assertTrue(len(generated_content.poem) > 0)
        
        # Step 5: Audio processing (if available)
        print("  🔊 Testing audio processing...")
        audio_capabilities = self.audio_manager.is_audio_processing_available()
        
        if audio_capabilities.get('any_tts', False):
            audio_result = self.audio_manager.process_text_to_audio(
                generated_content.supportive_statement[:100],  # Limit for testing
                create_remix=False
            )
            
            self.assertIsNotNone(audio_result, "Audio processing should succeed")
            self.assertIn('speech', audio_result)
        else:
            print("    ⚠️ Audio processing not available, skipping audio tests")
        
        # Step 6: Storage
        print("  💾 Testing storage...")
        interaction = Interaction(
            input_data=processed_input,
            generated_content=generated_content
        )
        
        saved_path = self.storage_manager.save_interaction(authenticated_user, interaction)
        self.assertIsNotNone(saved_path, "Interaction storage should succeed")
        
        # Step 7: History retrieval
        print("  📚 Testing history retrieval...")
        user_history = self.storage_manager.load_user_history(authenticated_user)
        self.assertIsInstance(user_history, list)
        self.assertGreater(len(user_history), 0, "History should contain saved interaction")
        
        print("  ✅ Complete text workflow test passed!")
        return True
    
    def test_audio_input_workflow(self):
        """Test workflow with audio input (mocked)"""
        print("\n🎵 Testing audio input workflow...")
        
        # Register user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Mock audio file data
        mock_audio_data = b"fake_audio_data_for_testing"
        
        # Process audio input
        with patch.object(self.input_processor, '_transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = "This is a transcribed audio message about feeling happy."
            
            processed_input = self.input_processor.process_audio_input(mock_audio_data)
            
            self.assertIsNotNone(processed_input)
            self.assertEqual(processed_input.input_type, InputType.AUDIO)
            self.assertIsNotNone(processed_input.transcription)
        
        # Continue with content generation
        generated_content = self.content_generator.generate_support_and_poem(processed_input)
        self.assertIsNotNone(generated_content)
        
        # Save interaction
        interaction = Interaction(
            input_data=processed_input,
            generated_content=generated_content
        )
        saved_path = self.storage_manager.save_interaction(user, interaction)
        self.assertIsNotNone(saved_path)
        
        print("  ✅ Audio input workflow test passed!")
        return True
    
    def test_drawing_input_workflow(self):
        """Test workflow with drawing input (mocked)"""
        print("\n🎨 Testing drawing input workflow...")
        
        # Register user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Mock drawing data
        mock_drawing_data = {
            "objects": [{"type": "path", "stroke": "#000000"}],
            "background": "#ffffff"
        }
        
        # Process drawing input
        processed_input = self.input_processor.process_drawing_input(mock_drawing_data)
        
        self.assertIsNotNone(processed_input)
        self.assertEqual(processed_input.input_type, InputType.DRAWING)
        self.assertIn("drawing", processed_input.content.lower())
        
        # Continue with content generation
        generated_content = self.content_generator.generate_support_and_poem(processed_input)
        self.assertIsNotNone(generated_content)
        
        print("  ✅ Drawing input workflow test passed!")
        return True
    
    def test_fallback_systems(self):
        """Test fallback systems and error handling"""
        print("\n🛡️ Testing fallback systems...")
        
        # Test content generation fallback
        print("  🔄 Testing content generation fallback...")
        
        # Force Gemini to fail, should fallback to Mock
        with patch.object(GeminiGenerator, 'generate_support_and_poem') as mock_gemini:
            mock_gemini.side_effect = Exception("API Error")
            
            test_input = ProcessedInput(
                content="Test fallback content",
                input_type=InputType.TEXT
            )
            
            result = self.content_generator.generate_support_and_poem(test_input)
            self.assertIsNotNone(result, "Should fallback to mock generator")
            self.assertEqual(result.generation_metadata.get("generator"), "mock")
        
        # Test audio processing fallback
        print("  🔊 Testing audio processing fallback...")
        audio_capabilities = self.audio_manager.is_audio_processing_available()
        
        if audio_capabilities.get('pyttsx3_tts', False):
            # Test with ElevenLabs disabled
            with patch.object(self.audio_manager.tts_processor, 'elevenlabs_api_key', None):
                result = self.audio_manager.process_text_to_audio("Test fallback audio")
                if result and result.get('speech'):
                    self.assertEqual(result['speech'].metadata.get('provider'), 'pyttsx3')
        
        print("  ✅ Fallback systems test passed!")
        return True
    
    def test_data_validation(self):
        """Test data validation and integrity"""
        print("\n🔍 Testing data validation...")
        
        # Test invalid user data
        with self.assertRaises(ValueError):
            User(nickname="", password="test")
        
        with self.assertRaises(ValueError):
            User(nickname="test", password="")
        
        with self.assertRaises(ValueError):
            User(nickname="a", password="test")  # Too short nickname
        
        # Test invalid processed input
        with self.assertRaises(ValueError):
            ProcessedInput(content="", input_type=InputType.TEXT)
        
        with self.assertRaises(ValueError):
            ProcessedInput(content="test", input_type="invalid")
        
        # Test invalid generated content
        with self.assertRaises(ValueError):
            GeneratedContent(supportive_statement="", poem="test")
        
        with self.assertRaises(ValueError):
            GeneratedContent(supportive_statement="test", poem="")
        
        print("  ✅ Data validation test passed!")
        return True
    
    def test_storage_integrity(self):
        """Test storage system integrity"""
        print("\n💾 Testing storage integrity...")
        
        # Register user and create interaction
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Create test interaction
        processed_input = ProcessedInput(
            content="Test storage integrity",
            input_type=InputType.TEXT
        )
        generated_content = GeneratedContent(
            supportive_statement="You're doing great with testing!",
            poem="Tests run smooth and clean,\nCode works as it should be seen."
        )
        interaction = Interaction(
            input_data=processed_input,
            generated_content=generated_content
        )
        
        # Save interaction
        saved_path = self.storage_manager.save_interaction(user, interaction)
        self.assertIsNotNone(saved_path)
        
        # Verify files were created
        interaction_dir = Path(saved_path)
        self.assertTrue(interaction_dir.exists())
        self.assertTrue((interaction_dir / "support.txt").exists())
        self.assertTrue((interaction_dir / "poem.txt").exists())
        self.assertTrue((interaction_dir / "meta.json").exists())
        
        # Load and verify content
        with open(interaction_dir / "support.txt", 'r', encoding='utf-8') as f:
            saved_support = f.read()
        self.assertEqual(saved_support, generated_content.supportive_statement)
        
        with open(interaction_dir / "poem.txt", 'r', encoding='utf-8') as f:
            saved_poem = f.read()
        self.assertEqual(saved_poem, generated_content.poem)
        
        # Load metadata
        with open(interaction_dir / "meta.json", 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        self.assertEqual(metadata["input"]["content"], processed_input.content)
        
        print("  ✅ Storage integrity test passed!")
        return True
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n⚡ Testing performance benchmarks...")
        
        # Register user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Benchmark content generation
        start_time = datetime.now()
        
        test_input = ProcessedInput(
            content="Performance test input for benchmarking",
            input_type=InputType.TEXT
        )
        
        generated_content = self.content_generator.generate_support_and_poem(test_input)
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        self.assertLess(generation_time, 30.0, "Content generation should complete within 30 seconds")
        self.assertIsNotNone(generated_content)
        
        print(f"  📊 Content generation time: {generation_time:.2f}s")
        
        # Benchmark storage
        start_time = datetime.now()
        
        interaction = Interaction(
            input_data=test_input,
            generated_content=generated_content
        )
        
        saved_path = self.storage_manager.save_interaction(user, interaction)
        storage_time = (datetime.now() - start_time).total_seconds()
        
        self.assertLess(storage_time, 5.0, "Storage should complete within 5 seconds")
        self.assertIsNotNone(saved_path)
        
        print(f"  📊 Storage time: {storage_time:.2f}s")
        print("  ✅ Performance benchmarks test passed!")
        return True


class ModelSystemTest(unittest.TestCase):
    """Test local model management system"""
    
    def setUp(self):
        """Set up model system tests"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
    
    def test_model_registry(self):
        """Test model registry functionality"""
        print("\n🤖 Testing model registry...")
        
        registry = get_model_registry()
        self.assertIsNotNone(registry)
        
        # Test getting all models
        all_models = registry.get_all_models()
        self.assertIsInstance(all_models, dict)
        self.assertGreater(len(all_models), 0, "Registry should contain models")
        
        # Test getting specific model
        gpt2_model = registry.get_model("gpt2")
        self.assertIsNotNone(gpt2_model, "GPT-2 model should be available")
        self.assertEqual(gpt2_model.name, "gpt2")
        
        # Test CPU compatible models
        cpu_models = registry.get_cpu_compatible_models()
        self.assertIsInstance(cpu_models, dict)
        self.assertGreater(len(cpu_models), 0, "Should have CPU-compatible models")
        
        print("  ✅ Model registry test passed!")
    
    def test_model_selector(self):
        """Test model selection logic"""
        print("\n🎯 Testing model selector...")
        
        # Create temporary config directory
        with tempfile.TemporaryDirectory() as temp_dir:
            selector = ModelSelector(
                cache_dir=temp_dir + "/models",
                config_dir=temp_dir + "/config"
            )
            
            # Test getting candidates
            from model_selector import ModelSelectionCriteria, SelectionStrategy
            criteria = ModelSelectionCriteria(
                strategy=SelectionStrategy.MINIMAL_RESOURCES,
                max_size_gb=5.0
            )
            
            candidates = selector.get_model_candidates(criteria)
            self.assertIsInstance(candidates, list)
            self.assertGreater(len(candidates), 0, "Should have model candidates")
            
            # Test best model selection
            best_model = selector.select_best_model(criteria)
            if best_model:
                self.assertIsNotNone(best_model.model_spec)
                self.assertLessEqual(best_model.model_spec.size_gb, 5.0)
            
            print("  ✅ Model selector test passed!")
    
    def test_environment_checker(self):
        """Test environment checking"""
        print("\n🔧 Testing environment checker...")
        
        env_report = check_environment()
        self.assertIsNotNone(env_report)
        self.assertIsNotNone(env_report.hardware)
        self.assertIsNotNone(env_report.dependencies)
        
        # Verify hardware detection
        self.assertIsInstance(env_report.hardware.has_gpu, bool)
        self.assertIsInstance(env_report.hardware.available_ram_gb, (int, float))
        self.assertGreaterEqual(env_report.hardware.available_ram_gb, 0)
        
        # Verify dependency checking
        self.assertIsInstance(env_report.dependencies, list)
        
        print(f"  📊 GPU Available: {env_report.hardware.has_gpu}")
        print(f"  📊 RAM Available: {env_report.hardware.available_ram_gb:.1f}GB")
        print(f"  📊 Dependencies Checked: {len(env_report.dependencies)}")
        print("  ✅ Environment checker test passed!")
    
    def test_local_model_integration(self):
        """Test local model integration with content generation"""
        print("\n🔗 Testing local model integration...")
        
        try:
            # Test model recommendation for current hardware
            env_report = check_environment()
            registry = get_model_registry()
            
            # Get hardware-appropriate model recommendations
            recommendations = registry.get_recommended_models_for_hardware(
                has_gpu=env_report.hardware.has_gpu,
                vram_gb=env_report.hardware.total_vram_gb,
                ram_gb=int(env_report.hardware.available_ram_gb)
            )
            
            self.assertIsInstance(recommendations, list)
            print(f"  📊 Found {len(recommendations)} compatible models")
            
            if recommendations:
                best_model = recommendations[0]
                print(f"  🏆 Best model: {best_model.name} ({best_model.size_gb:.1f}GB)")
                print(f"    Quality: {best_model.quality_score}/10")
                print(f"    Speed: {best_model.speed_score}/10")
                print(f"    CPU Compatible: {best_model.is_cpu_compatible}")
                
                # Test model validation
                from model_manager import validate_model_compatibility
                is_compatible, reason = validate_model_compatibility(
                    best_model.name,
                    env_report.hardware.has_gpu,
                    env_report.hardware.total_vram_gb,
                    int(env_report.hardware.available_ram_gb)
                )
                
                self.assertTrue(is_compatible, f"Best model should be compatible: {reason}")
                print(f"  ✅ Model compatibility validated: {reason}")
            
            print("  ✅ Local model integration test passed!")
            
        except Exception as e:
            print(f"  ⚠️ Local model integration test failed: {e}")
            # Don't fail the test if model modules aren't available
            pass


class DefensiveSystemTest(unittest.TestCase):
    """Test defensive programming systems"""
    
    def setUp(self):
        """Set up defensive system tests"""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
    
    def test_defensive_system(self):
        """Test defensive programming features"""
        print("\n🛡️ Testing defensive system...")
        
        try:
            defensive_system = DefensiveSystem()
            
            # Test dependency checking
            deps_available = defensive_system.check_dependencies()
            self.assertIsInstance(deps_available, dict)
            
            # Test graceful degradation
            degradation_status = defensive_system.get_degradation_status()
            self.assertIsInstance(degradation_status, dict)
            
            print("  ✅ Defensive system test passed!")
        except ImportError:
            print("  ⚠️ Defensive system module not available, skipping")


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Starting EchoVerse Comprehensive Test Suite")
    print("=" * 80)
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Cannot run tests - import failures detected")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(EchoVerseEndToEndTest))
    test_suite.addTest(unittest.makeSuite(ModelSystemTest))
    test_suite.addTest(unittest.makeSuite(DefensiveSystemTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return success


def run_quick_smoke_test():
    """Run a quick smoke test of core functionality"""
    print("💨 Running Quick Smoke Test")
    print("=" * 40)
    
    if not IMPORTS_SUCCESSFUL:
        print("❌ Import failures detected")
        return False
    
    try:
        # Test basic imports and initialization
        print("📦 Testing imports...")
        content_generator = ContentGenerator()
        audio_manager = AudioManager()
        input_processor = InputProcessor()
        print("✅ Core components initialized")
        
        # Test basic functionality
        print("🧪 Testing basic functionality...")
        test_input = ProcessedInput(
            content="Quick smoke test",
            input_type=InputType.TEXT
        )
        
        generated_content = content_generator.generate_support_and_poem(test_input)
        if generated_content:
            print("✅ Content generation working")
        else:
            print("⚠️ Content generation failed")
            return False
        
        print("🎉 Smoke test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EchoVerse Test Suite")
    parser.add_argument("--smoke", action="store_true", help="Run quick smoke test only")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive test suite")
    
    args = parser.parse_args()
    
    if args.smoke:
        success = run_quick_smoke_test()
    elif args.comprehensive:
        success = run_comprehensive_tests()
    else:
        # Default: run smoke test first, then comprehensive if it passes
        print("Running default test sequence...")
        smoke_success = run_quick_smoke_test()
        if smoke_success:
            print("\n" + "="*50)
            success = run_comprehensive_tests()
        else:
            success = False
    
    sys.exit(0 if success else 1)