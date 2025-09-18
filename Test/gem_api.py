#!/usr/bin/env python3
"""
Gemini API Validation and Testing Utility for EchoVerse
Tests Google Gemini API connectivity, functionality, and integration
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Try to import required modules
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ google.generativeai not available")

try:
    from content_generator import GeminiGenerator, ContentGenerator
    from data_models import ProcessedInput, InputType
    ECHOVERSE_MODULES_AVAILABLE = True
except ImportError as e:
    ECHOVERSE_MODULES_AVAILABLE = False
    print(f"⚠️ EchoVerse modules not available: {e}")


class GeminiAPIValidator:
    """Comprehensive Gemini API validation and testing"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the validator with API key"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        self.test_results = []
        
        if not self.api_key:
            print("❌ No Gemini API key found. Set GEMINI_API_KEY environment variable.")
            return
        
        if not GENAI_AVAILABLE:
            print("❌ google.generativeai library not available")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            print("✅ Gemini API configured successfully")
        except Exception as e:
            print(f"❌ Failed to configure Gemini API: {e}")
    
    def is_available(self) -> bool:
        """Check if Gemini API is available and configured"""
        return self.model is not None and GENAI_AVAILABLE
    
    def test_basic_connectivity(self) -> Dict[str, Any]:
        """Test basic API connectivity"""
        print("\n🔌 Testing basic Gemini API connectivity...")
        
        if not self.is_available():
            result = {
                "test": "basic_connectivity",
                "success": False,
                "error": "API not available or configured",
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(result)
            return result
        
        try:
            start_time = time.time()
            response = self.model.generate_content("Hello, this is a test message.")
            end_time = time.time()
            
            if response and response.text:
                result = {
                    "test": "basic_connectivity",
                    "success": True,
                    "response_time": end_time - start_time,
                    "response_length": len(response.text),
                    "response_preview": response.text[:100] + "..." if len(response.text) > 100 else response.text,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"✅ Basic connectivity test passed ({result['response_time']:.2f}s)")
            else:
                result = {
                    "test": "basic_connectivity",
                    "success": False,
                    "error": "Empty or invalid response",
                    "timestamp": datetime.now().isoformat()
                }
                print("❌ Basic connectivity test failed - empty response")
            
        except Exception as e:
            result = {
                "test": "basic_connectivity",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ Basic connectivity test failed: {e}")
        
        self.test_results.append(result)
        return result
    
    def test_supportive_content_generation(self) -> Dict[str, Any]:
        """Test supportive content generation"""
        print("\n💝 Testing supportive content generation...")
        
        if not self.is_available():
            result = {
                "test": "supportive_content",
                "success": False,
                "error": "API not available",
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(result)
            return result
        
        test_prompts = [
            "I'm feeling overwhelmed with work and stressed about deadlines.",
            "I had a difficult day and feel like giving up on my goals.",
            "I'm struggling with self-doubt and imposter syndrome.",
            "I feel lonely and disconnected from others lately."
        ]
        
        results = []
        
        for i, user_input in enumerate(test_prompts, 1):
            print(f"  📝 Testing prompt {i}/{len(test_prompts)}...")
            
            try:
                prompt = f"""
                You are a compassionate AI companion. A user has shared: "{user_input}"
                
                Please provide a warm, supportive, and encouraging response that:
                - Acknowledges their feelings with empathy
                - Offers gentle encouragement and hope
                - Provides practical perspective or gentle guidance
                - Is personal and heartfelt, not generic
                - Is 2-3 sentences long
                
                Response:
                """
                
                start_time = time.time()
                response = self.model.generate_content(prompt)
                end_time = time.time()
                
                if response and response.text:
                    support_text = response.text.strip()
                    
                    # Validate response quality
                    quality_score = self._evaluate_supportive_response(user_input, support_text)
                    
                    test_result = {
                        "prompt_index": i,
                        "user_input": user_input,
                        "response": support_text,
                        "response_time": end_time - start_time,
                        "quality_score": quality_score,
                        "success": True
                    }
                    
                    print(f"    ✅ Generated supportive response (quality: {quality_score}/10)")
                    
                else:
                    test_result = {
                        "prompt_index": i,
                        "user_input": user_input,
                        "success": False,
                        "error": "Empty response"
                    }
                    print(f"    ❌ Failed to generate response")
                
                results.append(test_result)
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                test_result = {
                    "prompt_index": i,
                    "user_input": user_input,
                    "success": False,
                    "error": str(e)
                }
                results.append(test_result)
                print(f"    ❌ Error: {e}")
        
        # Calculate overall results
        successful_tests = [r for r in results if r.get("success", False)]
        avg_quality = sum(r.get("quality_score", 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        
        overall_result = {
            "test": "supportive_content",
            "success": len(successful_tests) > 0,
            "total_prompts": len(test_prompts),
            "successful_prompts": len(successful_tests),
            "success_rate": len(successful_tests) / len(test_prompts),
            "average_quality_score": avg_quality,
            "average_response_time": avg_response_time,
            "individual_results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Supportive content test: {len(successful_tests)}/{len(test_prompts)} successful")
        print(f"📊 Average quality score: {avg_quality:.1f}/10")
        
        self.test_results.append(overall_result)
        return overall_result
    
    def test_poem_generation(self) -> Dict[str, Any]:
        """Test poem generation"""
        print("\n🎭 Testing poem generation...")
        
        if not self.is_available():
            result = {
                "test": "poem_generation",
                "success": False,
                "error": "API not available",
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(result)
            return result
        
        test_themes = [
            "hope and resilience",
            "finding strength in difficult times",
            "self-compassion and acceptance",
            "new beginnings and growth"
        ]
        
        results = []
        
        for i, theme in enumerate(test_themes, 1):
            print(f"  🎨 Testing poem theme {i}/{len(test_themes)}: {theme}...")
            
            try:
                prompt = f"""
                Write a short, uplifting poem about {theme}. The poem should:
                - Be 4-8 lines long
                - Have a gentle, encouraging tone
                - Use accessible, heartfelt language
                - Offer comfort and inspiration
                - Have a natural rhythm (doesn't need to rhyme perfectly)
                
                Poem:
                """
                
                start_time = time.time()
                response = self.model.generate_content(prompt)
                end_time = time.time()
                
                if response and response.text:
                    poem_text = response.text.strip()
                    
                    # Validate poem structure
                    lines = [line.strip() for line in poem_text.split('\n') if line.strip()]
                    quality_score = self._evaluate_poem_response(theme, poem_text, lines)
                    
                    test_result = {
                        "theme_index": i,
                        "theme": theme,
                        "poem": poem_text,
                        "line_count": len(lines),
                        "response_time": end_time - start_time,
                        "quality_score": quality_score,
                        "success": True
                    }
                    
                    print(f"    ✅ Generated poem ({len(lines)} lines, quality: {quality_score}/10)")
                    
                else:
                    test_result = {
                        "theme_index": i,
                        "theme": theme,
                        "success": False,
                        "error": "Empty response"
                    }
                    print(f"    ❌ Failed to generate poem")
                
                results.append(test_result)
                time.sleep(0.5)
                
            except Exception as e:
                test_result = {
                    "theme_index": i,
                    "theme": theme,
                    "success": False,
                    "error": str(e)
                }
                results.append(test_result)
                print(f"    ❌ Error: {e}")
        
        # Calculate overall results
        successful_tests = [r for r in results if r.get("success", False)]
        avg_quality = sum(r.get("quality_score", 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        
        overall_result = {
            "test": "poem_generation",
            "success": len(successful_tests) > 0,
            "total_themes": len(test_themes),
            "successful_themes": len(successful_tests),
            "success_rate": len(successful_tests) / len(test_themes),
            "average_quality_score": avg_quality,
            "average_response_time": avg_response_time,
            "individual_results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Poem generation test: {len(successful_tests)}/{len(test_themes)} successful")
        print(f"📊 Average quality score: {avg_quality:.1f}/10")
        
        self.test_results.append(overall_result)
        return overall_result
    
    def test_echoverse_integration(self) -> Dict[str, Any]:
        """Test integration with EchoVerse content generator"""
        print("\n🔗 Testing EchoVerse integration...")
        
        if not ECHOVERSE_MODULES_AVAILABLE:
            result = {
                "test": "echoverse_integration",
                "success": False,
                "error": "EchoVerse modules not available",
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(result)
            return result
        
        try:
            # Test GeminiGenerator directly
            gemini_generator = GeminiGenerator()
            
            if not gemini_generator.is_available():
                result = {
                    "test": "echoverse_integration",
                    "success": False,
                    "error": "GeminiGenerator not available",
                    "timestamp": datetime.now().isoformat()
                }
                self.test_results.append(result)
                return result
            
            # Test with ProcessedInput
            test_input = ProcessedInput(
                content="I'm feeling anxious about an upcoming presentation at work.",
                input_type=InputType.TEXT,
                metadata={"test": True}
            )
            
            start_time = time.time()
            generated_content = gemini_generator.generate_support_and_poem(test_input)
            end_time = time.time()
            
            if generated_content:
                result = {
                    "test": "echoverse_integration",
                    "success": True,
                    "response_time": end_time - start_time,
                    "supportive_statement_length": len(generated_content.supportive_statement),
                    "poem_length": len(generated_content.poem),
                    "generator_metadata": generated_content.generation_metadata,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"✅ EchoVerse integration test passed ({result['response_time']:.2f}s)")
                
                # Test ContentGenerator fallback system
                content_generator = ContentGenerator()
                fallback_test_input = ProcessedInput(
                    content="Testing fallback system integration",
                    input_type=InputType.TEXT
                )
                
                fallback_content = content_generator.generate_support_and_poem(fallback_test_input)
                if fallback_content:
                    result["fallback_test"] = {
                        "success": True,
                        "generator_used": fallback_content.generation_metadata.get("generator", "unknown")
                    }
                    print("✅ Fallback system integration working")
                else:
                    result["fallback_test"] = {"success": False}
                    print("⚠️ Fallback system integration failed")
                
            else:
                result = {
                    "test": "echoverse_integration",
                    "success": False,
                    "error": "No content generated",
                    "timestamp": datetime.now().isoformat()
                }
                print("❌ EchoVerse integration test failed - no content generated")
            
        except Exception as e:
            result = {
                "test": "echoverse_integration",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ EchoVerse integration test failed: {e}")
        
        self.test_results.append(result)
        return result
    
    def test_rate_limiting_and_error_handling(self) -> Dict[str, Any]:
        """Test rate limiting and error handling"""
        print("\n⚡ Testing rate limiting and error handling...")
        
        if not self.is_available():
            result = {
                "test": "rate_limiting",
                "success": False,
                "error": "API not available",
                "timestamp": datetime.now().isoformat()
            }
            self.test_results.append(result)
            return result
        
        # Test rapid requests
        rapid_requests = []
        for i in range(5):
            try:
                start_time = time.time()
                response = self.model.generate_content(f"Quick test message {i+1}")
                end_time = time.time()
                
                rapid_requests.append({
                    "request_number": i + 1,
                    "success": bool(response and response.text),
                    "response_time": end_time - start_time
                })
                
            except Exception as e:
                rapid_requests.append({
                    "request_number": i + 1,
                    "success": False,
                    "error": str(e)
                })
        
        successful_rapid = [r for r in rapid_requests if r.get("success", False)]
        
        # Test invalid input handling
        invalid_inputs = [
            "",  # Empty string
            "x" * 10000,  # Very long string
            None,  # None value (will be converted to string)
        ]
        
        invalid_input_results = []
        for i, invalid_input in enumerate(invalid_inputs):
            try:
                response = self.model.generate_content(str(invalid_input) if invalid_input is not None else "")
                invalid_input_results.append({
                    "input_type": f"invalid_{i}",
                    "handled_gracefully": True,
                    "got_response": bool(response and response.text)
                })
            except Exception as e:
                invalid_input_results.append({
                    "input_type": f"invalid_{i}",
                    "handled_gracefully": False,
                    "error": str(e)
                })
        
        result = {
            "test": "rate_limiting",
            "success": True,
            "rapid_requests": {
                "total": len(rapid_requests),
                "successful": len(successful_rapid),
                "success_rate": len(successful_rapid) / len(rapid_requests)
            },
            "invalid_input_handling": invalid_input_results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Rapid requests: {len(successful_rapid)}/{len(rapid_requests)} successful")
        print(f"📊 Invalid input handling: {len(invalid_input_results)} tests completed")
        
        self.test_results.append(result)
        return result
    
    def _evaluate_supportive_response(self, user_input: str, response: str) -> int:
        """Evaluate quality of supportive response (1-10 scale)"""
        score = 5  # Base score
        
        # Check length (should be substantial but not too long)
        if 50 <= len(response) <= 500:
            score += 1
        
        # Check for empathetic language
        empathy_words = ["understand", "feel", "know", "hear", "see", "acknowledge", "recognize"]
        if any(word in response.lower() for word in empathy_words):
            score += 1
        
        # Check for encouraging language
        encouraging_words = ["can", "will", "able", "strength", "capable", "possible", "hope", "believe"]
        if any(word in response.lower() for word in encouraging_words):
            score += 1
        
        # Check that it's not generic
        if "you" in response.lower() and len(response.split()) > 10:
            score += 1
        
        # Penalize if too short or too generic
        if len(response) < 30:
            score -= 2
        
        return max(1, min(10, score))
    
    def _evaluate_poem_response(self, theme: str, poem: str, lines: List[str]) -> int:
        """Evaluate quality of poem response (1-10 scale)"""
        score = 5  # Base score
        
        # Check line count (4-8 is ideal)
        if 4 <= len(lines) <= 8:
            score += 2
        elif len(lines) < 4:
            score -= 1
        elif len(lines) > 12:
            score -= 1
        
        # Check for poetic language
        poetic_indicators = ["like", "as", "through", "beyond", "within", "beneath", "above"]
        if any(word in poem.lower() for word in poetic_indicators):
            score += 1
        
        # Check for theme relevance
        theme_words = theme.lower().split()
        if any(word in poem.lower() for word in theme_words):
            score += 1
        
        # Check for emotional/uplifting content
        uplifting_words = ["light", "bright", "hope", "joy", "peace", "love", "strength", "grow", "rise"]
        if any(word in poem.lower() for word in uplifting_words):
            score += 1
        
        return max(1, min(10, score))
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("🚀 Starting Gemini API Comprehensive Validation")
        print("=" * 60)
        
        if not self.is_available():
            print("❌ Gemini API not available - cannot run tests")
            return {
                "overall_success": False,
                "error": "API not available",
                "timestamp": datetime.now().isoformat()
            }
        
        # Run all tests
        tests = [
            self.test_basic_connectivity,
            self.test_supportive_content_generation,
            self.test_poem_generation,
            self.test_echoverse_integration,
            self.test_rate_limiting_and_error_handling
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ Test {test_func.__name__} failed with exception: {e}")
        
        # Calculate overall results
        successful_tests = [r for r in self.test_results if r.get("success", False)]
        
        overall_result = {
            "overall_success": len(successful_tests) == len(self.test_results),
            "total_tests": len(self.test_results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(self.test_results) if self.test_results else 0,
            "individual_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 GEMINI API VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(self.test_results) - len(successful_tests)}")
        print(f"Success Rate: {overall_result['success_rate']:.1%}")
        
        if overall_result["overall_success"]:
            print("\n🎉 All Gemini API tests passed!")
        else:
            print("\n⚠️ Some Gemini API tests failed")
            failed_tests = [r for r in self.test_results if not r.get("success", False)]
            for failed_test in failed_tests:
                print(f"  ❌ {failed_test.get('test', 'unknown')}: {failed_test.get('error', 'unknown error')}")
        
        return overall_result
    
    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_api_test_results_{timestamp}.json"
        
        results_data = {
            "test_session": {
                "timestamp": datetime.now().isoformat(),
                "api_key_configured": bool(self.api_key),
                "genai_available": GENAI_AVAILABLE,
                "echoverse_modules_available": ECHOVERSE_MODULES_AVAILABLE
            },
            "results": self.test_results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            print(f"📄 Test results saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return ""


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini API Validation for EchoVerse")
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--save-results", action="store_true", help="Save results to JSON file")
    parser.add_argument("--quick", action="store_true", help="Run quick connectivity test only")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = GeminiAPIValidator(api_key=args.api_key)
    
    if args.quick:
        # Quick test
        result = validator.test_basic_connectivity()
        success = result.get("success", False)
    else:
        # Full test suite
        result = validator.run_all_tests()
        success = result.get("overall_success", False)
    
    # Save results if requested
    if args.save_results:
        validator.save_results()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()