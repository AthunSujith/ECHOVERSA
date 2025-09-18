#!/usr/bin/env python3
"""
Cross-platform compatibility testing for EchoVerse companion application.
Tests functionality across different operating systems and environments.
"""

import sys
import os
import platform
import tempfile
import json
import time
from pathlib import Path
import subprocess
import shutil

def test_platform_detection():
    """Test platform detection and system information gathering."""
    print("🖥️ Testing Platform Detection...")
    
    results = []
    
    try:
        # Test platform detection
        system = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()
        processor = platform.processor()
        
        results.append(f"✅ System: {system}")
        results.append(f"✅ Release: {release}")
        results.append(f"✅ Version: {version}")
        results.append(f"✅ Machine: {machine}")
        results.append(f"✅ Processor: {processor}")
        
        # Test Python version compatibility
        python_version = sys.version_info
        if python_version >= (3, 8):
            results.append(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro} (Compatible)")
        else:
            results.append(f"❌ Python version: {python_version.major}.{python_version.minor}.{python_version.micro} (Requires 3.8+)")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Platform detection failed: {e}")
        return False, results

def test_file_system_operations():
    """Test file system operations across platforms."""
    print("📁 Testing File System Operations...")
    
    results = []
    temp_dir = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        results.append(f"✅ Temporary directory created: {temp_dir}")
        
        # Test path handling
        test_path = Path(temp_dir) / "test_subdir" / "test_file.txt"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        results.append("✅ Directory creation with parents works")
        
        # Test file writing with different encodings
        test_content = "Test content with unicode: 测试 🎵 éñ"
        test_path.write_text(test_content, encoding='utf-8')
        results.append("✅ UTF-8 file writing works")
        
        # Test file reading
        read_content = test_path.read_text(encoding='utf-8')
        if read_content == test_content:
            results.append("✅ UTF-8 file reading works")
        else:
            results.append("❌ File content mismatch")
        
        # Test binary file operations
        binary_data = b"Binary test data \x00\x01\x02\x03"
        binary_path = Path(temp_dir) / "binary_test.dat"
        binary_path.write_bytes(binary_data)
        read_binary = binary_path.read_bytes()
        
        if read_binary == binary_data:
            results.append("✅ Binary file operations work")
        else:
            results.append("❌ Binary file operations failed")
        
        # Test file permissions (Unix-like systems)
        if platform.system() != 'Windows':
            try:
                os.chmod(test_path, 0o644)
                results.append("✅ File permissions setting works")
            except Exception as e:
                results.append(f"⚠️ File permissions: {e}")
        else:
            results.append("ℹ️ File permissions test skipped on Windows")
        
        # Test long file paths
        long_path = Path(temp_dir)
        for i in range(10):
            long_path = long_path / f"very_long_directory_name_{i}"
        
        try:
            long_path.mkdir(parents=True, exist_ok=True)
            long_file = long_path / "test_file.txt"
            long_file.write_text("Long path test")
            results.append("✅ Long file paths work")
        except Exception as e:
            results.append(f"⚠️ Long file paths: {e}")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ File system operations failed: {e}")
        return False, results
        
    finally:
        # Cleanup
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
                results.append("✅ Cleanup completed")
            except Exception as e:
                results.append(f"⚠️ Cleanup warning: {e}")

def test_json_serialization():
    """Test JSON serialization with various data types."""
    print("📄 Testing JSON Serialization...")
    
    results = []
    
    try:
        # Test various data types
        test_data = {
            "string": "test string",
            "unicode": "测试 🎵 éñ",
            "integer": 42,
            "float": 3.14159,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, "four", 5.0],
            "nested": {
                "inner": "value",
                "number": 123
            },
            "special_chars": "Line 1\nLine 2\tTabbed\r\nWindows line ending"
        }
        
        # Test JSON serialization
        json_str = json.dumps(test_data, ensure_ascii=False, indent=2)
        results.append("✅ JSON serialization works")
        
        # Test JSON deserialization
        parsed_data = json.loads(json_str)
        
        if parsed_data == test_data:
            results.append("✅ JSON deserialization works")
        else:
            results.append("❌ JSON round-trip failed")
        
        # Test with file I/O
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        try:
            json.dump(test_data, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()
            
            with open(temp_file.name, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            if file_data == test_data:
                results.append("✅ JSON file I/O works")
            else:
                results.append("❌ JSON file I/O failed")
                
        finally:
            os.unlink(temp_file.name)
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ JSON serialization failed: {e}")
        return False, results

def test_environment_variables():
    """Test environment variable handling."""
    print("🌍 Testing Environment Variables...")
    
    results = []
    
    try:
        # Test reading common environment variables
        common_vars = ['PATH', 'HOME', 'USER', 'USERNAME', 'USERPROFILE', 'TEMP', 'TMP']
        found_vars = []
        
        for var in common_vars:
            value = os.environ.get(var)
            if value:
                found_vars.append(var)
        
        results.append(f"✅ Found environment variables: {', '.join(found_vars)}")
        
        # Test setting and getting custom environment variable
        test_var = "ECHOVERSE_TEST_VAR"
        test_value = "test_value_123"
        
        os.environ[test_var] = test_value
        retrieved_value = os.environ.get(test_var)
        
        if retrieved_value == test_value:
            results.append("✅ Environment variable setting/getting works")
        else:
            results.append("❌ Environment variable operations failed")
        
        # Cleanup
        del os.environ[test_var]
        
        # Test path separator
        path_sep = os.pathsep
        results.append(f"✅ Path separator: '{path_sep}'")
        
        # Test directory separator
        dir_sep = os.sep
        results.append(f"✅ Directory separator: '{dir_sep}'")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Environment variable testing failed: {e}")
        return False, results

def test_subprocess_operations():
    """Test subprocess operations for cross-platform compatibility."""
    print("⚙️ Testing Subprocess Operations...")
    
    results = []
    
    try:
        # Test basic command execution
        if platform.system() == 'Windows':
            # Windows commands
            test_commands = [
                ['echo', 'Hello World'],
                ['dir', '/b'],  # List directory contents
                ['python', '--version']
            ]
        else:
            # Unix-like commands
            test_commands = [
                ['echo', 'Hello World'],
                ['ls', '-la'],  # List directory contents
                ['python3', '--version']
            ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    check=False
                )
                
                if result.returncode == 0:
                    results.append(f"✅ Command '{' '.join(cmd)}' executed successfully")
                else:
                    results.append(f"⚠️ Command '{' '.join(cmd)}' returned code {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                results.append(f"⚠️ Command '{' '.join(cmd)}' timed out")
            except FileNotFoundError:
                results.append(f"⚠️ Command '{' '.join(cmd)}' not found")
            except Exception as e:
                results.append(f"❌ Command '{' '.join(cmd)}' failed: {e}")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Subprocess testing failed: {e}")
        return False, results

def test_unicode_handling():
    """Test Unicode and internationalization support."""
    print("🌐 Testing Unicode Handling...")
    
    results = []
    
    try:
        # Test various Unicode strings
        unicode_tests = [
            ("English", "Hello World"),
            ("Chinese", "你好世界"),
            ("Japanese", "こんにちは世界"),
            ("Arabic", "مرحبا بالعالم"),
            ("Russian", "Привет мир"),
            ("Emoji", "Hello 🌍 World 🎵 Test 💖"),
            ("Mixed", "Hello 世界 🌍 مرحبا"),
            ("Special", "Line\nBreak\tTab\r\nReturn"),
        ]
        
        for name, text in unicode_tests:
            try:
                # Test string operations
                encoded = text.encode('utf-8')
                decoded = encoded.decode('utf-8')
                
                if decoded == text:
                    results.append(f"✅ {name} Unicode handling works")
                else:
                    results.append(f"❌ {name} Unicode handling failed")
                    
            except Exception as e:
                results.append(f"❌ {name} Unicode test failed: {e}")
        
        # Test file I/O with Unicode
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        try:
            unicode_content = "Unicode test: 你好 🌍 مرحبا Привет"
            temp_file.write(unicode_content)
            temp_file.close()
            
            with open(temp_file.name, 'r', encoding='utf-8') as f:
                read_content = f.read()
            
            if read_content == unicode_content:
                results.append("✅ Unicode file I/O works")
            else:
                results.append("❌ Unicode file I/O failed")
                
        finally:
            os.unlink(temp_file.name)
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Unicode testing failed: {e}")
        return False, results

def test_datetime_handling():
    """Test datetime and timezone handling."""
    print("🕒 Testing DateTime Handling...")
    
    results = []
    
    try:
        from datetime import datetime, timezone, timedelta
        
        # Test current datetime
        now = datetime.now()
        results.append(f"✅ Current datetime: {now}")
        
        # Test UTC datetime
        utc_now = datetime.now(timezone.utc)
        results.append(f"✅ UTC datetime: {utc_now}")
        
        # Test ISO format
        iso_string = now.isoformat()
        parsed_datetime = datetime.fromisoformat(iso_string)
        
        if abs((parsed_datetime - now).total_seconds()) < 1:
            results.append("✅ ISO datetime format works")
        else:
            results.append("❌ ISO datetime format failed")
        
        # Test timezone operations
        try:
            local_tz = datetime.now().astimezone().tzinfo
            results.append(f"✅ Local timezone: {local_tz}")
        except Exception as e:
            results.append(f"⚠️ Timezone detection: {e}")
        
        # Test datetime arithmetic
        future = now + timedelta(days=1, hours=2, minutes=30)
        diff = future - now
        
        if abs(diff.total_seconds() - (24*3600 + 2*3600 + 30*60)) < 1:
            results.append("✅ DateTime arithmetic works")
        else:
            results.append("❌ DateTime arithmetic failed")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ DateTime testing failed: {e}")
        return False, results

def test_memory_and_performance():
    """Test memory usage and basic performance characteristics."""
    print("🚀 Testing Memory and Performance...")
    
    results = []
    
    try:
        import gc
        
        # Test garbage collection
        collected = gc.collect()
        results.append(f"✅ Garbage collection: {collected} objects collected")
        
        # Test memory allocation
        test_data = []
        start_time = time.time()
        
        for i in range(10000):
            test_data.append(f"Test string {i}")
        
        allocation_time = time.time() - start_time
        results.append(f"✅ Memory allocation: {allocation_time:.3f}s for 10k strings")
        
        # Test memory cleanup
        del test_data
        collected_after = gc.collect()
        results.append(f"✅ Memory cleanup: {collected_after} objects collected")
        
        # Test basic performance
        start_time = time.time()
        
        # CPU-bound task
        total = sum(i * i for i in range(10000))
        
        cpu_time = time.time() - start_time
        results.append(f"✅ CPU performance: {cpu_time:.3f}s for computation")
        
        # Test I/O performance
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            start_time = time.time()
            
            for i in range(1000):
                temp_file.write(f"Line {i}\n".encode())
            
            temp_file.close()
            io_time = time.time() - start_time
            results.append(f"✅ I/O performance: {io_time:.3f}s for 1k writes")
            
        finally:
            os.unlink(temp_file.name)
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Memory/Performance testing failed: {e}")
        return False, results

def run_all_compatibility_tests():
    """Run all cross-platform compatibility tests."""
    print("🧪 Starting Cross-Platform Compatibility Testing...")
    print("=" * 70)
    
    test_functions = [
        test_platform_detection,
        test_file_system_operations,
        test_json_serialization,
        test_environment_variables,
        test_subprocess_operations,
        test_unicode_handling,
        test_datetime_handling,
        test_memory_and_performance
    ]
    
    all_results = []
    passed_tests = 0
    total_tests = len(test_functions)
    
    for test_func in test_functions:
        try:
            success, results = test_func()
            all_results.extend(results)
            
            if success:
                passed_tests += 1
                print(f"✅ {test_func.__name__} PASSED")
            else:
                print(f"❌ {test_func.__name__} FAILED")
            
            # Print individual results
            for result in results:
                print(f"  {result}")
            
            print()
            
        except Exception as e:
            print(f"❌ {test_func.__name__} CRASHED: {e}")
            all_results.append(f"❌ {test_func.__name__} crashed: {e}")
            print()
    
    # Generate summary report
    print("=" * 70)
    print("📊 CROSS-PLATFORM COMPATIBILITY REPORT")
    print("=" * 70)
    
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Architecture: {platform.machine()}")
    print()
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    print()
    
    # Count individual results
    success_count = len([r for r in all_results if r.startswith("✅")])
    warning_count = len([r for r in all_results if r.startswith("⚠️")])
    info_count = len([r for r in all_results if r.startswith("ℹ️")])
    failure_count = len([r for r in all_results if r.startswith("❌")])
    
    print(f"Individual Checks:")
    print(f"  ✅ Passed: {success_count}")
    print(f"  ⚠️ Warnings: {warning_count}")
    print(f"  ℹ️ Info: {info_count}")
    print(f"  ❌ Failed: {failure_count}")
    print()
    
    if failure_count == 0:
        print("🎉 All compatibility tests passed! The application should work well on this platform.")
    elif failure_count < 5:
        print("⚠️ Minor compatibility issues detected. The application should still work with some limitations.")
    else:
        print("❌ Significant compatibility issues detected. The application may not work properly on this platform.")
    
    # Save detailed report
    report_data = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version
        },
        "summary": {
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "success_rate": passed_tests/total_tests*100,
            "success_count": success_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "failure_count": failure_count
        },
        "results": all_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    report_file = Path("compatibility_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Detailed report saved to: {report_file}")

def main():
    """Main function to run compatibility tests."""
    run_all_compatibility_tests()

if __name__ == "__main__":
    main()