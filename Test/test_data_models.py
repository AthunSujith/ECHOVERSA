"""
Test script for data models validation.
This script tests the core data models and validation functions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from data_models import (
    User, ProcessedInput, GeneratedContent, AudioFile, Interaction,
    InputType, validate_nickname, validate_password, validate_input_content,
    validate_user_data_integrity, validate_interaction_data_integrity
)
from datetime import datetime


def test_user_creation():
    """Test User data class creation and validation."""
    print("Testing User creation...")
    
    # Valid user
    try:
        user = User(nickname="testuser", password="testpass123")
        print("✓ Valid user created successfully")
    except Exception as e:
        print(f"✗ Failed to create valid user: {e}")
        return False
    
    # Invalid nickname
    try:
        user = User(nickname="", password="testpass123")
        print("✗ Should have failed with empty nickname")
        return False
    except ValueError:
        print("✓ Correctly rejected empty nickname")
    
    # Invalid password
    try:
        user = User(nickname="testuser", password="123")
        print("✗ Should have failed with short password")
        return False
    except ValueError:
        print("✓ Correctly rejected short password")
    
    return True


def test_processed_input():
    """Test ProcessedInput data class."""
    print("\nTesting ProcessedInput...")
    
    try:
        processed_input = ProcessedInput(
            content="Hello world",
            input_type=InputType.TEXT,
            metadata={"source": "user_input"}
        )
        print("✓ ProcessedInput created successfully")
    except Exception as e:
        print(f"✗ Failed to create ProcessedInput: {e}")
        return False
    
    # Test validation
    try:
        ProcessedInput(content="", input_type=InputType.TEXT)
        print("✗ Should have failed with empty content")
        return False
    except ValueError:
        print("✓ Correctly rejected empty content")
    
    return True


def test_generated_content():
    """Test GeneratedContent data class."""
    print("\nTesting GeneratedContent...")
    
    try:
        content = GeneratedContent(
            supportive_statement="You are doing great!",
            poem="Roses are red, violets are blue"
        )
        print("✓ GeneratedContent created successfully")
    except Exception as e:
        print(f"✗ Failed to create GeneratedContent: {e}")
        return False
    
    return True


def test_interaction():
    """Test Interaction data class."""
    print("\nTesting Interaction...")
    
    try:
        interaction = Interaction()
        print(f"✓ Interaction created with ID: {interaction.id}")
        print(f"✓ Timestamp: {interaction.timestamp}")
    except Exception as e:
        print(f"✗ Failed to create Interaction: {e}")
        return False
    
    return True


def test_validation_functions():
    """Test validation functions."""
    print("\nTesting validation functions...")
    
    # Test nickname validation
    assert validate_nickname("validuser") == True
    assert validate_nickname("user123") == True
    assert validate_nickname("a") == False
    assert validate_nickname("") == False
    print("✓ Nickname validation working")
    
    # Test password validation
    assert validate_password("validpass") == True
    assert validate_password("123") == False
    assert validate_password("") == False
    print("✓ Password validation working")
    
    # Test input content validation
    assert validate_input_content("Hello world", InputType.TEXT) == True
    assert validate_input_content("", InputType.TEXT) == False
    print("✓ Input content validation working")
    
    return True


def test_data_integrity():
    """Test data integrity validation functions."""
    print("\nTesting data integrity validation...")
    
    # Test valid user
    user = User(nickname="testuser", password="testpass123")
    errors = validate_user_data_integrity(user)
    if not errors:
        print("✓ Valid user passed integrity check")
    else:
        print(f"✗ Valid user failed integrity check: {errors}")
        return False
    
    # Test valid interaction
    interaction = Interaction()
    errors = validate_interaction_data_integrity(interaction)
    if not errors:
        print("✓ Valid interaction passed integrity check")
    else:
        print(f"✗ Valid interaction failed integrity check: {errors}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("Running data models tests...\n")
    
    tests = [
        test_user_creation,
        test_processed_input,
        test_generated_content,
        test_interaction,
        test_validation_functions,
        test_data_integrity
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"Test {test.__name__} failed!")
    
    print(f"\n{passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✓ All data model tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)