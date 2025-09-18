"""
System-wide validation tests for EchoVerse Companion Application.
Tests complete system integration, performance, and reliability.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import json
import time
import threading
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Import all system components
try:
    from streamlit_workspace import StreamlitApp
    from content_generator import ContentGenerator
    from audio_processor import AudioManager
    from input_processor import InputProcessor
    from storage_manager import StorageManager
    from auth_manager import UserManager
    from data_models import User, ProcessedInput, GeneratedContent, Interaction, InputType
    from model_manager import get_model_registry
    from model_selector import ModelSelector
    from environment_checker import check_environment
    from defensive_system import DefensiveSystem
    SYSTEM_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"System modules not available: {e}")
    SYSTEM_MODULES_AVAILABLE = False


@unittest.skipUnless(SYSTEM_MODULES_AVAILABLE, "System modules not available")
class SystemValidationTest(unittest.TestCase):
    """Comprehensive system validation tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up system-wide test environment"""
        cls.test_dir = tempfile.mkdtemp(prefix="echoverse_system_test_")
        cls.users_dir = Path(cls.test_dir) / "users"
        cls.models_dir = Path(cls.test_dir) / "models"
        cls.config_dir = Path(cls.test_dir) / "config"
        
        # Create directories
        cls.users_dir.mkdir(exist_ok=True)
        cls.models_dir.mkdir(exist_ok=True)
        cls.config_dir.mkdir(exist_ok=True)
        
        print(f"System test environment: {cls.test_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up system test environment"""
        if hasattr(cls, 'test_dir') and os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
    
    def setUp(self):
        """Set up individual test"""
        # Initialize all system components
        self.user_manager = UserManager(users_dir=str(self.users_dir))
        self.storage_manager = StorageManager(users_dir=str(self.users_dir))
        self.input_processor = InputProcessor()
        self.content_generator = ContentGenerator()
        self.audio_manager = AudioManager()
        self.model_selector = ModelSelector(
            cache_dir=str(self.models_dir),
            config_dir=str(self.config_dir)
        )
        self.defensive_system = DefensiveSystem()
        
        # Create test user
        self.test_user = User(
            nickname="systemtest",
            password="testpass123"
        )
    
    def test_system_initialization(self):
        """Test that all system components initialize correctly"""
        print("\n🔧 Testing system initialization...")
        
        # Test component initialization
        components = {
            "UserManager": self.user_manager,
            "StorageManager": self.storage_manager,
            "InputProcessor": self.input_processor,
            "ContentGenerator": self.content_generator,
            "AudioManager": self.audio_manager,
            "ModelSelector": self.model_selector,
            "DefensiveSystem": self.defensive_system
        }
        
        for name, component in components.items():
            self.assertIsNotNone(component, f"{name} should initialize")
            print(f"  ✅ {name} initialized")
        
        # Test system health
        health = self.defensive_system.get_system_health()
        self.assertIsInstance(health, dict)
        self.assertIn("overall_status", health)
        print(f"  📊 System health: {health['overall_status']}")
        
        print("  ✅ System initialization test passed!")
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from registration to content generation"""
        print("\n👤 Testing complete user workflow...")
        
        # Step 1: User registration
        registration_success = self.user_manager.register_user(
            self.test_user.nickname, 
            self.test_user.password
        )
        self.assertTrue(registration_success, "User registration should succeed")
        print("  ✅ User registration successful")
        
        # Step 2: User authentication
        authenticated_user = self.user_manager.authenticate_user(
            self.test_user.nickname, 
            self.test_user.password
        )
        self.assertIsNotNone(authenticated_user, "User authentication should succeed")
        print("  ✅ User authentication successful")
        
        # Step 3: Multiple input processing and content generation
        test_inputs = [
            ("I'm feeling anxious about my presentation tomorrow.", InputType.TEXT),
            ("I had a wonderful day at the park with my family.", InputType.TEXT),
            ("I'm struggling with motivation to exercise regularly.", InputType.TEXT)
        ]
        
        interactions = []
        
        for i, (input_text, input_type) in enumerate(test_inputs, 1):
            print(f"  📝 Processing input {i}/{len(test_inputs)}...")
            
            # Process input
            processed_input = self.input_processor.process_text_input(input_text)
            self.assertIsNotNone(processed_input)
            self.assertEqual(processed_input.input_type, input_type)
            
            # Generate content
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            self.assertIsNotNone(generated_content)
            self.assertTrue(len(generated_content.supportive_statement) > 0)
            self.assertTrue(len(generated_content.poem) > 0)
            
            # Create interaction
            interaction = Interaction(
                input_data=processed_input,
                generated_content=generated_content
            )
            
            # Save interaction
            saved_path = self.storage_manager.save_interaction(authenticated_user, interaction)
            self.assertIsNotNone(saved_path)
            
            interactions.append(interaction)
            print(f"    ✅ Input {i} processed and saved")
        
        # Step 4: History retrieval and validation
        print("  📚 Testing history retrieval...")
        user_history = self.storage_manager.load_user_history(authenticated_user)
        self.assertIsInstance(user_history, list)
        self.assertGreaterEqual(len(user_history), len(test_inputs))
        print(f"    ✅ Retrieved {len(user_history)} interactions from history")
        
        print("  ✅ Complete user workflow test passed!")
        return interactions
    
    def test_concurrent_user_operations(self):
        """Test system behavior under concurrent user operations"""
        print("\n⚡ Testing concurrent user operations...")
        
        def create_user_and_interact(user_id):
            """Create a user and perform interactions"""
            try:
                # Create unique user
                user = User(
                    nickname=f"concurrent_user_{user_id}",
                    password=f"pass_{user_id}"
                )
                
                # Register user
                registration_success = self.user_manager.register_user(
                    user.nickname, user.password
                )
                if not registration_success:
                    return {"success": False, "error": "Registration failed"}
                
                # Authenticate user
                authenticated_user = self.user_manager.authenticate_user(
                    user.nickname, user.password
                )
                if not authenticated_user:
                    return {"success": False, "error": "Authentication failed"}
                
                # Perform interactions
                interactions_count = 0
                for i in range(3):  # 3 interactions per user
                    input_text = f"Concurrent test input {i} from user {user_id}"
                    
                    # Process input
                    processed_input = self.input_processor.process_text_input(input_text)
                    if not processed_input:
                        continue
                    
                    # Generate content
                    generated_content = self.content_generator.generate_support_and_poem(processed_input)
                    if not generated_content:
                        continue
                    
                    # Save interaction
                    interaction = Interaction(
                        input_data=processed_input,
                        generated_content=generated_content
                    )
                    
                    saved_path = self.storage_manager.save_interaction(authenticated_user, interaction)
                    if saved_path:
                        interactions_count += 1
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "interactions_count": interactions_count
                }
                
            except Exception as e:
                return {"success": False, "error": str(e), "user_id": user_id}
        
        # Run concurrent operations
        num_concurrent_users = 5
        results = []
        
        with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = [
                executor.submit(create_user_and_interact, i) 
                for i in range(num_concurrent_users)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Validate results
        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        
        print(f"  📊 Successful concurrent operations: {len(successful_results)}/{num_concurrent_users}")
        print(f"  📊 Failed concurrent operations: {len(failed_results)}")
        
        if failed_results:
            for failed in failed_results:
                print(f"    ❌ User {failed.get('user_id', 'unknown')}: {failed.get('error', 'unknown error')}")
        
        # At least 80% should succeed
        success_rate = len(successful_results) / num_concurrent_users
        self.assertGreaterEqual(success_rate, 0.8, "At least 80% of concurrent operations should succeed")
        
        print("  ✅ Concurrent operations test passed!")
        return results
    
    def test_system_performance_benchmarks(self):
        """Test system performance benchmarks"""
        print("\n⚡ Testing system performance benchmarks...")
        
        # Register test user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Performance test scenarios
        test_scenarios = [
            {
                "name": "Short text input",
                "input": "I'm happy today!",
                "expected_max_time": 30.0
            },
            {
                "name": "Medium text input",
                "input": "I've been feeling overwhelmed with work lately. There's so much to do and not enough time. I'm worried about meeting all my deadlines and maintaining quality in my work.",
                "expected_max_time": 35.0
            },
            {
                "name": "Long text input",
                "input": "Today has been a particularly challenging day for me. I woke up feeling anxious about the presentation I have to give at work tomorrow. It's been weeks since I started preparing for it, but I still don't feel ready. The topic is complex, and I'm worried that I won't be able to explain it clearly to my colleagues. On top of that, I've been dealing with some personal issues at home that have been weighing on my mind. My relationship with my partner has been strained lately, and we've been having more arguments than usual. I feel like I'm constantly walking on eggshells, trying not to say the wrong thing. All of this stress is starting to affect my sleep, and I find myself lying awake at night, my mind racing with worries and what-if scenarios.",
                "expected_max_time": 45.0
            }
        ]
        
        performance_results = []
        
        for scenario in test_scenarios:
            print(f"  🏃 Testing: {scenario['name']}...")
            
            start_time = time.time()
            
            # Process input
            processed_input = self.input_processor.process_text_input(scenario["input"])
            input_processing_time = time.time() - start_time
            
            # Generate content
            content_start_time = time.time()
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            content_generation_time = time.time() - content_start_time
            
            # Save interaction
            storage_start_time = time.time()
            interaction = Interaction(
                input_data=processed_input,
                generated_content=generated_content
            )
            saved_path = self.storage_manager.save_interaction(user, interaction)
            storage_time = time.time() - storage_start_time
            
            total_time = time.time() - start_time
            
            result = {
                "scenario": scenario["name"],
                "input_length": len(scenario["input"]),
                "input_processing_time": input_processing_time,
                "content_generation_time": content_generation_time,
                "storage_time": storage_time,
                "total_time": total_time,
                "expected_max_time": scenario["expected_max_time"],
                "within_expected": total_time <= scenario["expected_max_time"]
            }
            
            performance_results.append(result)
            
            print(f"    ⏱️ Total time: {total_time:.2f}s (expected: <{scenario['expected_max_time']}s)")
            print(f"    📊 Content generation: {content_generation_time:.2f}s")
            print(f"    📊 Storage: {storage_time:.2f}s")
            
            if result["within_expected"]:
                print(f"    ✅ Performance within expected range")
            else:
                print(f"    ⚠️ Performance slower than expected")
        
        # Calculate overall performance metrics
        avg_total_time = sum(r["total_time"] for r in performance_results) / len(performance_results)
        avg_content_time = sum(r["content_generation_time"] for r in performance_results) / len(performance_results)
        within_expected_count = sum(1 for r in performance_results if r["within_expected"])
        
        print(f"\n  📊 Performance Summary:")
        print(f"    Average total time: {avg_total_time:.2f}s")
        print(f"    Average content generation time: {avg_content_time:.2f}s")
        print(f"    Scenarios within expected time: {within_expected_count}/{len(performance_results)}")
        
        # At least 2/3 scenarios should meet performance expectations
        performance_success_rate = within_expected_count / len(performance_results)
        self.assertGreaterEqual(performance_success_rate, 0.67, 
                               "At least 67% of performance scenarios should meet expectations")
        
        print("  ✅ Performance benchmarks test passed!")
        return performance_results
    
    def test_error_resilience(self):
        """Test system resilience to various error conditions"""
        print("\n🛡️ Testing system error resilience...")
        
        # Register test user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        error_scenarios = [
            {
                "name": "Empty input handling",
                "test_func": lambda: self.input_processor.process_text_input(""),
                "should_handle_gracefully": True
            },
            {
                "name": "Very long input handling",
                "test_func": lambda: self.input_processor.process_text_input("x" * 50000),
                "should_handle_gracefully": True
            },
            {
                "name": "Special characters input",
                "test_func": lambda: self.input_processor.process_text_input("🎉💖🌟 Special chars! @#$%^&*()"),
                "should_handle_gracefully": True
            },
            {
                "name": "Content generation with None input",
                "test_func": lambda: self.content_generator.generate_support_and_poem(None),
                "should_handle_gracefully": True
            }
        ]
        
        resilience_results = []
        
        for scenario in error_scenarios:
            print(f"  🧪 Testing: {scenario['name']}...")
            
            try:
                result = scenario["test_func"]()
                
                if scenario["should_handle_gracefully"]:
                    # Should either return a valid result or None, but not crash
                    test_result = {
                        "scenario": scenario["name"],
                        "handled_gracefully": True,
                        "result_type": type(result).__name__,
                        "error": None
                    }
                    print(f"    ✅ Handled gracefully (returned {type(result).__name__})")
                else:
                    test_result = {
                        "scenario": scenario["name"],
                        "handled_gracefully": False,
                        "result_type": type(result).__name__,
                        "error": "Should have raised exception but didn't"
                    }
                    print(f"    ⚠️ Should have raised exception but returned {type(result).__name__}")
                
            except Exception as e:
                if scenario["should_handle_gracefully"]:
                    test_result = {
                        "scenario": scenario["name"],
                        "handled_gracefully": False,
                        "result_type": None,
                        "error": str(e)
                    }
                    print(f"    ❌ Failed to handle gracefully: {e}")
                else:
                    test_result = {
                        "scenario": scenario["name"],
                        "handled_gracefully": True,
                        "result_type": None,
                        "error": str(e)
                    }
                    print(f"    ✅ Correctly raised exception: {type(e).__name__}")
            
            resilience_results.append(test_result)
        
        # Calculate resilience metrics
        gracefully_handled = sum(1 for r in resilience_results if r["handled_gracefully"])
        resilience_rate = gracefully_handled / len(resilience_results)
        
        print(f"\n  📊 Error Resilience Summary:")
        print(f"    Scenarios handled gracefully: {gracefully_handled}/{len(resilience_results)}")
        print(f"    Resilience rate: {resilience_rate:.1%}")
        
        # At least 80% should be handled gracefully
        self.assertGreaterEqual(resilience_rate, 0.8, 
                               "At least 80% of error scenarios should be handled gracefully")
        
        print("  ✅ Error resilience test passed!")
        return resilience_results
    
    def test_data_integrity_validation(self):
        """Test data integrity across the entire system"""
        print("\n🔍 Testing data integrity validation...")
        
        # Register test user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Create test interactions with various data types
        test_cases = [
            {
                "input": "Simple test input",
                "metadata": {"test_case": "simple"}
            },
            {
                "input": "Input with unicode: 你好世界 🌍",
                "metadata": {"test_case": "unicode", "language": "mixed"}
            },
            {
                "input": "Input with\nnewlines\nand\ttabs",
                "metadata": {"test_case": "formatting", "has_newlines": True}
            }
        ]
        
        integrity_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"  📝 Testing data integrity case {i}/{len(test_cases)}...")
            
            # Process and save interaction
            processed_input = self.input_processor.process_text_input(test_case["input"])
            processed_input.metadata.update(test_case["metadata"])
            
            generated_content = self.content_generator.generate_support_and_poem(processed_input)
            
            interaction = Interaction(
                input_data=processed_input,
                generated_content=generated_content
            )
            
            saved_path = self.storage_manager.save_interaction(user, interaction)
            
            # Verify data integrity by loading and comparing
            user_history = self.storage_manager.load_user_history(user)
            
            # Find the saved interaction
            saved_interaction = None
            for hist_interaction in user_history:
                if hist_interaction.input_data.content == test_case["input"]:
                    saved_interaction = hist_interaction
                    break
            
            self.assertIsNotNone(saved_interaction, f"Interaction {i} should be found in history")
            
            # Verify data integrity
            integrity_check = {
                "test_case": i,
                "input_content_match": saved_interaction.input_data.content == test_case["input"],
                "metadata_preserved": all(
                    saved_interaction.input_data.metadata.get(k) == v 
                    for k, v in test_case["metadata"].items()
                ),
                "generated_content_present": (
                    len(saved_interaction.generated_content.supportive_statement) > 0 and
                    len(saved_interaction.generated_content.poem) > 0
                ),
                "file_structure_valid": os.path.exists(saved_path)
            }
            
            # Check file contents
            if os.path.exists(saved_path):
                support_file = os.path.join(saved_path, "support.txt")
                poem_file = os.path.join(saved_path, "poem.txt")
                meta_file = os.path.join(saved_path, "meta.json")
                
                integrity_check["files_exist"] = (
                    os.path.exists(support_file) and
                    os.path.exists(poem_file) and
                    os.path.exists(meta_file)
                )
                
                if integrity_check["files_exist"]:
                    # Verify file contents match
                    with open(support_file, 'r', encoding='utf-8') as f:
                        saved_support = f.read()
                    
                    with open(poem_file, 'r', encoding='utf-8') as f:
                        saved_poem = f.read()
                    
                    integrity_check["file_content_match"] = (
                        saved_support == saved_interaction.generated_content.supportive_statement and
                        saved_poem == saved_interaction.generated_content.poem
                    )
                    
                    # Verify metadata JSON
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        saved_meta = json.load(f)
                    
                    integrity_check["metadata_json_valid"] = (
                        saved_meta["input"]["content"] == test_case["input"]
                    )
            
            integrity_results.append(integrity_check)
            
            # Print results for this test case
            all_checks_passed = all(integrity_check.values())
            if all_checks_passed:
                print(f"    ✅ Data integrity verified for case {i}")
            else:
                print(f"    ❌ Data integrity issues found for case {i}")
                for check, result in integrity_check.items():
                    if not result:
                        print(f"      - {check}: FAILED")
        
        # Calculate overall integrity metrics
        total_checks = len(integrity_results)
        passed_checks = sum(1 for result in integrity_results if all(result.values()))
        integrity_rate = passed_checks / total_checks
        
        print(f"\n  📊 Data Integrity Summary:")
        print(f"    Test cases with full integrity: {passed_checks}/{total_checks}")
        print(f"    Integrity rate: {integrity_rate:.1%}")
        
        # All data integrity checks should pass
        self.assertEqual(integrity_rate, 1.0, "All data integrity checks should pass")
        
        print("  ✅ Data integrity validation test passed!")
        return integrity_results
    
    def test_system_resource_usage(self):
        """Test system resource usage and memory management"""
        print("\n💾 Testing system resource usage...")
        
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"  📊 Initial memory usage: {initial_memory:.1f} MB")
        
        # Register test user
        self.user_manager.register_user(self.test_user.nickname, self.test_user.password)
        user = self.user_manager.authenticate_user(self.test_user.nickname, self.test_user.password)
        
        # Perform multiple operations to test memory usage
        memory_measurements = [initial_memory]
        
        for i in range(10):  # 10 iterations
            # Create and process multiple inputs
            for j in range(5):  # 5 inputs per iteration
                input_text = f"Memory test iteration {i}, input {j}. " * 10  # Longer text
                
                processed_input = self.input_processor.process_text_input(input_text)
                generated_content = self.content_generator.generate_support_and_poem(processed_input)
                
                interaction = Interaction(
                    input_data=processed_input,
                    generated_content=generated_content
                )
                
                self.storage_manager.save_interaction(user, interaction)
            
            # Measure memory after each iteration
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(current_memory)
            
            # Force garbage collection
            gc.collect()
        
        final_memory = memory_measurements[-1]
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_measurements)
        
        print(f"  📊 Final memory usage: {final_memory:.1f} MB")
        print(f"  📊 Memory increase: {memory_increase:.1f} MB")
        print(f"  📊 Peak memory usage: {max_memory:.1f} MB")
        
        # Memory increase should be reasonable (less than 100MB for this test)
        self.assertLess(memory_increase, 100, "Memory increase should be less than 100MB")
        
        # Check for memory leaks (memory should not continuously increase)
        recent_measurements = memory_measurements[-3:]  # Last 3 measurements
        memory_trend = recent_measurements[-1] - recent_measurements[0]
        
        print(f"  📊 Recent memory trend: {memory_trend:.1f} MB")
        
        # Recent trend should be minimal (less than 20MB)
        self.assertLess(abs(memory_trend), 20, "Recent memory trend should be minimal")
        
        print("  ✅ Resource usage test passed!")
        
        return {
            "initial_memory": initial_memory,
            "final_memory": final_memory,
            "memory_increase": memory_increase,
            "max_memory": max_memory,
            "memory_measurements": memory_measurements
        }


def run_system_validation():
    """Run complete system validation suite"""
    print("🚀 Starting EchoVerse System Validation Suite")
    print("=" * 80)
    
    if not SYSTEM_MODULES_AVAILABLE:
        print("❌ Cannot run system validation - required modules not available")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(SystemValidationTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Print comprehensive summary
    print("\n" + "=" * 80)
    print("📊 SYSTEM VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 SYSTEM VALIDATION PASSED")
        print("✅ All system components are working correctly")
        print("✅ Performance benchmarks met")
        print("✅ Error resilience verified")
        print("✅ Data integrity maintained")
        print("✅ Resource usage within acceptable limits")
    else:
        print("\n❌ SYSTEM VALIDATION FAILED")
        
        if result.failures:
            print("\n❌ FAILURES:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\n❌ ERRORS:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EchoVerse System Validation")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    
    args = parser.parse_args()
    
    if args.quick:
        # Run a subset of tests for quick validation
        suite = unittest.TestSuite()
        suite.addTest(SystemValidationTest('test_system_initialization'))
        suite.addTest(SystemValidationTest('test_complete_user_workflow'))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        success = len(result.failures) == 0 and len(result.errors) == 0
    else:
        success = run_system_validation()
    
    sys.exit(0 if success else 1)