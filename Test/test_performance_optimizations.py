#!/usr/bin/env python3
"""
Test script for performance optimizations in EchoVerse companion application.
Tests loading indicators, progress tracking, caching, and file I/O optimizations.
"""

import sys
import time
import logging
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from performance_optimizer import (
        get_performance_optimizer, LoadingIndicator, ProgressTracker,
        SmartCache, MemoryOptimizer, monitor_performance, cache_result
    )
    from storage_manager import StorageManager
    from data_models import User, Interaction, ProcessedInput, GeneratedContent, InputType
    from datetime import datetime
    import uuid
    
    print("✅ All performance optimization modules imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_loading_indicators():
    """Test loading indicators functionality."""
    print("\n🔄 Testing Loading Indicators...")
    
    # Test basic loading indicator
    with LoadingIndicator("Testing basic loading...", show_spinner=False):
        time.sleep(1)
    
    # Test loading indicator with message update
    indicator = LoadingIndicator("Initial message...", show_spinner=False)
    with indicator:
        time.sleep(0.5)
        indicator.update_message("Updated message...")
        time.sleep(0.5)
    
    print("✅ Loading indicators test completed")


def test_progress_tracking():
    """Test progress tracking functionality."""
    print("\n📊 Testing Progress Tracking...")
    
    # Test basic progress tracking
    progress = ProgressTracker(5, "Testing progress")
    
    for i in range(1, 6):
        progress.update(i, f"Step {i} of 5")
        time.sleep(0.2)
    
    progress.complete("Progress test completed")
    
    print("✅ Progress tracking test completed")


def test_smart_cache():
    """Test smart cache functionality."""
    print("\n🧠 Testing Smart Cache...")
    
    cache = SmartCache(max_size=5, ttl_seconds=2)
    
    # Test cache set and get
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.get("key1") == "value1", "Cache get failed"
    assert cache.get("key2") == "value2", "Cache get failed"
    assert cache.get("nonexistent") is None, "Cache should return None for missing keys"
    
    # Test cache stats
    stats = cache.get_stats()
    assert stats["size"] == 3, f"Expected cache size 3, got {stats['size']}"
    assert stats["hit_count"] > 0, "Cache should have hits"
    
    # Test TTL expiration
    time.sleep(2.5)
    assert cache.get("key1") is None, "Cache should expire after TTL"
    
    # Test cache eviction (LRU)
    for i in range(10):
        cache.set(f"key_{i}", f"value_{i}")
    
    stats = cache.get_stats()
    assert stats["size"] <= 5, f"Cache size should not exceed max_size, got {stats['size']}"
    
    print("✅ Smart cache test completed")


def test_memory_optimizer():
    """Test memory optimizer functionality."""
    print("\n🧹 Testing Memory Optimizer...")
    
    optimizer = MemoryOptimizer()
    
    # Test memory usage reporting
    memory_info = optimizer.get_memory_usage()
    assert isinstance(memory_info, dict), "Memory info should be a dictionary"
    
    # Test memory optimization
    result = optimizer.optimize_memory(force_gc=True)
    assert isinstance(result, dict), "Optimization result should be a dictionary"
    assert "memory_before" in result, "Result should contain memory_before"
    assert "memory_after" in result, "Result should contain memory_after"
    
    print("✅ Memory optimizer test completed")


@monitor_performance("test_performance_monitoring")
def test_performance_monitoring():
    """Test performance monitoring decorator."""
    print("\n⏱️ Testing Performance Monitoring...")
    
    # This function is decorated with @monitor_performance
    time.sleep(0.1)  # Simulate some work
    
    return "test_result"


@cache_result("test_cache_{args}", ttl=60)
def test_cached_function(value):
    """Test function result caching."""
    print(f"Computing result for {value}")
    time.sleep(0.1)  # Simulate expensive computation
    return f"result_{value}"


def test_result_caching():
    """Test function result caching."""
    print("\n💾 Testing Result Caching...")
    
    # First call should compute the result
    start_time = time.time()
    result1 = test_cached_function("test")
    first_duration = time.time() - start_time
    
    # Second call should use cached result
    start_time = time.time()
    result2 = test_cached_function("test")
    second_duration = time.time() - start_time
    
    assert result1 == result2, "Cached result should match original"
    assert second_duration < first_duration, "Cached call should be faster"
    
    print("✅ Result caching test completed")


def test_storage_optimizations():
    """Test storage manager optimizations."""
    print("\n💾 Testing Storage Optimizations...")
    
    try:
        # Create test storage manager with absolute path
        import tempfile
        temp_dir = tempfile.mkdtemp()
        storage = StorageManager(temp_dir)
        
        # Create test user
        user = User(
            nickname="test_user_perf",
            password="test_password",
            created=datetime.now(),
            preferences={},
            prompts=[]
        )
        
        # Test optimized user profile operations
        storage.create_user_directory(user)
        storage.save_user_profile(user)
        
        loaded_user = storage.load_user_profile(user.nickname)
        assert loaded_user is not None, "User should be loaded successfully"
        assert loaded_user.nickname == user.nickname, "Loaded user should match original"
        
        # Test optimized interaction operations
        processed_input = ProcessedInput(
            content="Test input for performance",
            input_type=InputType.TEXT,
            metadata={"test": True}
        )
        
        generated_content = GeneratedContent(
            supportive_statement="Test supportive statement",
            poem="Test poem content",
            generation_metadata={"generator": "test"}
        )
        
        interaction = Interaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            input_data=processed_input,
            generated_content=generated_content,
            audio_files=[],
            file_paths={}
        )
        
        # Test batch file operations
        interaction_id = storage.save_interaction(user, interaction)
        assert interaction_id is not None, "Interaction should be saved successfully"
        
        # Ensure all file operations are completed
        storage.flush_pending_operations()
        time.sleep(0.1)  # Give time for batch operations to complete
        
        # Test cached loading
        loaded_interaction = storage.load_interaction(user.nickname, interaction_id)
        assert loaded_interaction is not None, "Interaction should be loaded successfully"
        assert loaded_interaction.id == interaction_id, "Loaded interaction should match original"
        
        # Clean up test files
        import shutil
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
        
        print("✅ Storage optimizations test completed")
        
    except Exception as e:
        print(f"❌ Storage optimization test failed: {e}")
        raise


def test_performance_optimizer_integration():
    """Test performance optimizer integration."""
    print("\n🚀 Testing Performance Optimizer Integration...")
    
    optimizer = get_performance_optimizer()
    
    # Test performance monitoring
    result = test_performance_monitoring()
    assert result == "test_result", "Performance monitoring should not affect function result"
    
    # Test cache functionality
    cache_stats = optimizer.cache.get_stats()
    assert isinstance(cache_stats, dict), "Cache stats should be a dictionary"
    
    # Test memory optimization
    memory_result = optimizer.memory_optimizer.optimize_memory()
    assert isinstance(memory_result, dict), "Memory optimization should return results"
    
    # Test performance report
    report = optimizer.get_performance_report()
    assert isinstance(report, dict), "Performance report should be a dictionary"
    assert "operations" in report, "Report should contain operations data"
    assert "cache" in report, "Report should contain cache data"
    assert "memory" in report, "Report should contain memory data"
    
    print("✅ Performance optimizer integration test completed")


def main():
    """Run all performance optimization tests."""
    print("🧪 Starting Performance Optimization Tests...")
    print("=" * 50)
    
    try:
        # Run all tests
        test_loading_indicators()
        test_progress_tracking()
        test_smart_cache()
        test_memory_optimizer()
        test_result_caching()
        test_storage_optimizations()
        test_performance_optimizer_integration()
        
        print("\n" + "=" * 50)
        print("🎉 All performance optimization tests passed!")
        
        # Display final performance report
        optimizer = get_performance_optimizer()
        report = optimizer.get_performance_report()
        
        print("\n📊 Final Performance Report:")
        print(f"Total Operations: {report['operations']['total_operations']}")
        print(f"Average Duration: {report['operations']['avg_duration']:.3f}s")
        print(f"Success Rate: {report['operations']['success_rate']:.1%}")
        print(f"Cache Hit Rate: {report['cache']['main_cache']['hit_rate']:.1%}")
        
        # Cleanup
        optimizer.cleanup_resources()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()