#!/usr/bin/env python3
"""
End-to-end integration testing for EchoVerse companion application.
Tests complete user workflows, fallback scenarios, and cross-platform compatibility.
"""

import sys
import time
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import uuid
import json

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

try:
    # Import all major components
    from auth_manager import UserManager, AuthenticationError
    from data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType, AudioFile
    from storage_manager import StorageManager, HistoryManager
    from session_manager import SessionManager
    from input_processor import InputProcessor
    from content_generator import ContentGenerator, MockGenerator, GeminiGenerator
    from audio_processor import AudioManager, TTSProcessor, AudioRemixer
    from performance_optimizer import get_performance_optimizer
    from defensive_system import initialize_defensive_systems
    from logging_config import setup_application_logging
    
    print("✅ All core modules imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class EndToEndTestSuite:
    """Comprehensive end-to-end test suite for EchoVerse application."""
    
    def __init__(self):
        """Initialize the test suite with temporary directories and components."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = []
        
        # Initialize logging and defensive systems
        self.logger = setup_application_logging()
        initialize_defensive_systems()
        
        # Initialize core components
        self.user_manager = UserManager()
        self.storage_manager = StorageManager(self.temp_dir)
        self.history_manager = HistoryManager(self.storage_manager)
        self.session_manager = SessionManager(self.storage_manager, self.temp_dir)
        self.input_processor = InputProcessor()
        self.content_generator = ContentGenerator()
        self.audio_manager = AudioManager()
        self.performance_optimizer = get_performance_optimizer()
        
        print(f"🧪 Test environment initialized in: {self.temp_dir}")
    
    def log_test_result(self, test_name: str, success: bool, message: str = "", duration: float = 0):
        """Log test result for final reporting."""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({duration:.3f}s): {message}")
    
    def test_complete_user_registration_workflow(self):
        """Test complete user registration and authentication workflow."""
        test_name = "Complete User Registration Workflow"
        start_time = time.time()
        
        try:
            # Test user registration
            test_nickname = f"test_user_{int(time.time())}"
            test_password = "secure_password_123"
            
            success, message = self.user_manager.register_user(test_nickname, test_password)
            assert success, f"User registration failed: {message}"
            
            # Test user login
            session_token, login_message = self.user_manager.login_user(test_nickname, test_password)
            assert session_token is not None, f"User login failed: {login_message}"
            
            # Test user profile loading
            current_user = self.user_manager.get_current_user(session_token)
            assert current_user is not None, "Failed to get current user"
            assert current_user.nickname == test_nickname, "User nickname mismatch"
            
            # Test session management
            self.session_manager.start_session(current_user, session_token)
            
            # Test user logout
            logout_success = self.user_manager.logout_user(session_token)
            assert logout_success, "User logout failed"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "All authentication steps completed successfully", duration)
            return current_user, session_token
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_complete_text_interaction_workflow(self, user: User):
        """Test complete text input to output workflow."""
        test_name = "Complete Text Interaction Workflow"
        start_time = time.time()
        
        try:
            # Step 1: Process text input
            test_text = "I'm feeling overwhelmed with work and need some encouragement."
            processed_input = self.input_processor.process_text_input(test_text, {})
            
            assert processed_input is not None, "Text input processing failed"
            assert processed_input.content == test_text, "Processed content mismatch"
            assert processed_input.input_type == InputType.TEXT, "Input type mismatch"
            
            # Step 2: Generate supportive content
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            
            assert generated_content is not None, "Content generation failed"
            assert len(generated_content.supportive_statement) > 0, "Empty supportive statement"
            assert len(generated_content.poem) > 0, "Empty poem"
            
            # Step 3: Generate audio (if available)
            audio_files = []
            audio_capabilities = self.audio_manager.is_audio_processing_available()
            
            if audio_capabilities.get('any_tts', False):
                # Generate support audio
                support_audio_result = self.audio_manager.process_text_to_audio(
                    generated_content.supportive_statement,
                    create_remix=False
                )
                
                if support_audio_result.get('speech'):
                    audio_files.append(support_audio_result['speech'])
                
                # Generate poem audio
                poem_audio_result = self.audio_manager.process_text_to_audio(
                    generated_content.poem,
                    create_remix=False
                )
                
                if poem_audio_result.get('speech'):
                    audio_files.append(poem_audio_result['speech'])
            
            # Step 4: Create and save interaction
            interaction = Interaction(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                input_data=processed_input,
                generated_content=generated_content,
                audio_files=audio_files,
                file_paths={}
            )
            
            interaction_id = self.storage_manager.save_interaction(user, interaction)
            assert interaction_id is not None, "Interaction save failed"
            
            # Ensure all file operations are completed
            self.storage_manager.flush_pending_operations()
            time.sleep(0.1)  # Give time for batch operations to complete
            
            # Step 5: Load and verify saved interaction
            loaded_interaction = self.storage_manager.load_interaction(user.nickname, interaction_id)
            assert loaded_interaction is not None, "Interaction load failed"
            assert loaded_interaction.input_data.content == test_text, "Loaded content mismatch"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, f"Complete workflow with {len(audio_files)} audio files", duration)
            return interaction
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_audio_input_workflow(self, user: User):
        """Test audio input processing workflow."""
        test_name = "Audio Input Workflow"
        start_time = time.time()
        
        try:
            # Create mock audio data
            mock_audio_data = b"mock_audio_data_for_testing"
            metadata = {"filename": "test_audio.wav", "duration": 5.0}
            
            # Process audio input
            processed_input = self.input_processor.process_audio_input(
                mock_audio_data, "test_audio.wav", metadata
            )
            
            assert processed_input is not None, "Audio input processing failed"
            assert processed_input.input_type == InputType.AUDIO, "Input type should be AUDIO"
            assert processed_input.raw_data == mock_audio_data, "Raw audio data mismatch"
            
            # Generate content from audio input
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            assert generated_content is not None, "Content generation from audio failed"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "Audio input processed successfully", duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_drawing_input_workflow(self, user: User):
        """Test drawing input processing workflow."""
        test_name = "Drawing Input Workflow"
        start_time = time.time()
        
        try:
            # Create mock drawing data
            mock_drawing_data = {
                "objects": [{"type": "path", "path": "M10,10 L50,50"}],
                "background": "#ffffff"
            }
            
            # Process drawing input
            processed_input = self.input_processor.process_drawing_input(mock_drawing_data, {})
            
            assert processed_input is not None, "Drawing input processing failed"
            assert processed_input.input_type == InputType.DRAWING, "Input type should be DRAWING"
            
            # Generate content from drawing input
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            assert generated_content is not None, "Content generation from drawing failed"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "Drawing input processed successfully", duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_fallback_scenarios(self):
        """Test all fallback scenarios and error conditions."""
        test_name = "Fallback Scenarios"
        start_time = time.time()
        
        try:
            fallback_tests = []
            
            # Test content generation fallback
            try:
                # Force use of mock generator
                mock_generator = MockGenerator()
                test_input = ProcessedInput(
                    content="Test fallback content",
                    input_type=InputType.TEXT,
                    metadata={}
                )
                
                result = mock_generator.generate_support_and_poem(test_input)
                assert result is not None, "Mock generator fallback failed"
                fallback_tests.append("✅ Content generation fallback")
                
            except Exception as e:
                fallback_tests.append(f"❌ Content generation fallback: {e}")
            
            # Test audio processing fallback
            try:
                tts_processor = TTSProcessor()  # No API key - should use fallback
                audio_capabilities = self.audio_manager.is_audio_processing_available()
                
                if not audio_capabilities.get('any_tts', False):
                    fallback_tests.append("✅ Audio processing graceful degradation")
                else:
                    fallback_tests.append("ℹ️ Audio processing available - no fallback needed")
                    
            except Exception as e:
                fallback_tests.append(f"❌ Audio processing fallback: {e}")
            
            # Test storage error handling
            try:
                # Try to create storage in invalid location
                invalid_storage = StorageManager("/invalid/path/that/does/not/exist")
                fallback_tests.append("❌ Storage should have failed with invalid path")
                
            except Exception:
                fallback_tests.append("✅ Storage error handling works correctly")
            
            # Test authentication error handling
            try:
                # Try to login with invalid credentials
                session_token, message = self.user_manager.login_user("nonexistent_user", "wrong_password")
                assert session_token is None, "Login should fail with invalid credentials"
                fallback_tests.append("✅ Authentication error handling")
                
            except Exception as e:
                fallback_tests.append(f"❌ Authentication error handling: {e}")
            
            duration = time.time() - start_time
            success_count = len([t for t in fallback_tests if t.startswith("✅")])
            total_count = len(fallback_tests)
            
            message = f"{success_count}/{total_count} fallback scenarios passed"
            self.log_test_result(test_name, success_count == total_count, message, duration)
            
            for test in fallback_tests:
                print(f"  {test}")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_performance_and_caching(self, user: User):
        """Test performance optimizations and caching functionality."""
        test_name = "Performance and Caching"
        start_time = time.time()
        
        try:
            # Test cache functionality
            cache = self.performance_optimizer.cache
            
            # Test cache set/get
            cache.set("test_key", "test_value")
            cached_value = cache.get("test_key")
            assert cached_value == "test_value", "Cache set/get failed"
            
            # Test cache stats
            stats = cache.get_stats()
            assert stats["hit_count"] > 0, "Cache should have hits"
            
            # Test memory optimization
            memory_result = self.performance_optimizer.memory_optimizer.optimize_memory()
            assert isinstance(memory_result, dict), "Memory optimization should return results"
            
            # Test performance monitoring
            perf_report = self.performance_optimizer.get_performance_report()
            assert "operations" in perf_report, "Performance report should contain operations"
            assert "cache" in perf_report, "Performance report should contain cache data"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "All performance features working", duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_session_persistence(self, user: User):
        """Test session management and persistence."""
        test_name = "Session Persistence"
        start_time = time.time()
        
        try:
            # Start a session
            session_token = str(uuid.uuid4())
            self.session_manager.start_session(user, session_token)
            
            # Create test interaction
            test_interaction = Interaction(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                input_data=ProcessedInput(
                    content="Test session persistence",
                    input_type=InputType.TEXT,
                    metadata={}
                ),
                generated_content=GeneratedContent(
                    supportive_statement="Test support",
                    poem="Test poem",
                    generation_metadata={}
                ),
                audio_files=[],
                file_paths={}
            )
            
            # Save interaction to session
            session_saved = self.session_manager.save_interaction_to_session(test_interaction)
            assert session_saved, "Session save should succeed"
            
            # Test session data persistence
            session_data = self.session_manager.get_session_data()
            assert session_data is not None, "Session data should be available"
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, "Session persistence working correctly", duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_cross_platform_compatibility(self):
        """Test cross-platform compatibility features."""
        test_name = "Cross-Platform Compatibility"
        start_time = time.time()
        
        try:
            import platform
            import os
            
            compatibility_tests = []
            
            # Test platform detection
            current_platform = platform.system()
            compatibility_tests.append(f"✅ Platform detected: {current_platform}")
            
            # Test path handling
            test_path = Path(self.temp_dir) / "test_file.txt"
            test_path.write_text("test content")
            assert test_path.exists(), "Path handling should work cross-platform"
            compatibility_tests.append("✅ Path handling works correctly")
            
            # Test file operations
            with open(test_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "test content", "File I/O should work cross-platform"
            compatibility_tests.append("✅ File I/O operations work correctly")
            
            # Test directory operations
            test_dir = Path(self.temp_dir) / "test_subdir"
            test_dir.mkdir(exist_ok=True)
            assert test_dir.exists(), "Directory creation should work cross-platform"
            compatibility_tests.append("✅ Directory operations work correctly")
            
            # Test JSON serialization
            test_data = {"test": "data", "unicode": "测试", "number": 123}
            json_str = json.dumps(test_data, ensure_ascii=False)
            parsed_data = json.loads(json_str)
            assert parsed_data == test_data, "JSON handling should work cross-platform"
            compatibility_tests.append("✅ JSON serialization works correctly")
            
            duration = time.time() - start_time
            success_count = len([t for t in compatibility_tests if t.startswith("✅")])
            total_count = len(compatibility_tests)
            
            message = f"{success_count}/{total_count} compatibility tests passed"
            self.log_test_result(test_name, success_count == total_count, message, duration)
            
            for test in compatibility_tests:
                print(f"  {test}")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def test_error_recovery_and_resilience(self):
        """Test error recovery and system resilience."""
        test_name = "Error Recovery and Resilience"
        start_time = time.time()
        
        try:
            resilience_tests = []
            
            # Test invalid input handling
            try:
                result = self.input_processor.process_text_input("", {})
                if result is None or len(result.content) == 0:
                    resilience_tests.append("✅ Empty input handled gracefully")
                else:
                    resilience_tests.append("❌ Empty input should be handled")
            except Exception:
                resilience_tests.append("✅ Empty input throws appropriate exception")
            
            # Test invalid file operations
            try:
                invalid_path = Path("/invalid/nonexistent/path/file.txt")
                content = self.storage_manager._read_file_optimized(invalid_path)
                resilience_tests.append("❌ Invalid file read should fail")
            except Exception:
                resilience_tests.append("✅ Invalid file operations handled correctly")
            
            # Test memory pressure handling
            try:
                # Force memory optimization
                result = self.performance_optimizer.memory_optimizer.optimize_memory(force_gc=True)
                resilience_tests.append("✅ Memory pressure handling works")
            except Exception as e:
                resilience_tests.append(f"❌ Memory handling failed: {e}")
            
            # Test concurrent access
            try:
                import threading
                
                def concurrent_cache_access():
                    for i in range(10):
                        self.performance_optimizer.cache.set(f"concurrent_{i}", f"value_{i}")
                        self.performance_optimizer.cache.get(f"concurrent_{i}")
                
                threads = [threading.Thread(target=concurrent_cache_access) for _ in range(3)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                
                resilience_tests.append("✅ Concurrent access handled correctly")
                
            except Exception as e:
                resilience_tests.append(f"❌ Concurrent access failed: {e}")
            
            duration = time.time() - start_time
            success_count = len([t for t in resilience_tests if t.startswith("✅")])
            total_count = len(resilience_tests)
            
            message = f"{success_count}/{total_count} resilience tests passed"
            self.log_test_result(test_name, success_count == total_count, message, duration)
            
            for test in resilience_tests:
                print(f"  {test}")
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, str(e), duration)
            raise
    
    def run_all_tests(self):
        """Run the complete end-to-end test suite."""
        print("🚀 Starting End-to-End Integration Testing...")
        print("=" * 60)
        
        total_start_time = time.time()
        
        try:
            # Test 1: Complete user registration workflow
            user, session_token = self.test_complete_user_registration_workflow()
            
            # Test 2: Complete text interaction workflow
            interaction = self.test_complete_text_interaction_workflow(user)
            
            # Test 3: Audio input workflow
            self.test_audio_input_workflow(user)
            
            # Test 4: Drawing input workflow
            self.test_drawing_input_workflow(user)
            
            # Test 5: Fallback scenarios
            self.test_fallback_scenarios()
            
            # Test 6: Performance and caching
            self.test_performance_and_caching(user)
            
            # Test 7: Session persistence
            self.test_session_persistence(user)
            
            # Test 8: Cross-platform compatibility
            self.test_cross_platform_compatibility()
            
            # Test 9: Error recovery and resilience
            self.test_error_recovery_and_resilience()
            
        except Exception as e:
            print(f"\n❌ Critical test failure: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            total_duration = time.time() - total_start_time
            self.generate_test_report(total_duration)
            self.cleanup()
    
    def generate_test_report(self, total_duration: float):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 END-TO-END TEST REPORT")
        print("=" * 60)
        
        passed_tests = [r for r in self.test_results if r["success"]]
        failed_tests = [r for r in self.test_results if not r["success"]]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)} ✅")
        print(f"Failed: {len(failed_tests)} ❌")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        print(f"Total Duration: {total_duration:.3f}s")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['message']}")
        
        print("\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"  - {test['test_name']} ({test['duration']:.3f}s)")
        
        # Save detailed report to file
        report_file = Path(self.temp_dir) / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": len(self.test_results),
                    "passed": len(passed_tests),
                    "failed": len(failed_tests),
                    "success_rate": len(passed_tests)/len(self.test_results)*100,
                    "total_duration": total_duration
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Overall result
        if len(failed_tests) == 0:
            print("\n🎉 ALL TESTS PASSED! The application is ready for production.")
        else:
            print(f"\n⚠️ {len(failed_tests)} tests failed. Please review and fix issues before deployment.")
    
    def cleanup(self):
        """Clean up test environment."""
        try:
            if Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
            print(f"\n🧹 Test environment cleaned up: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


def main():
    """Run the end-to-end test suite."""
    test_suite = EndToEndTestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()