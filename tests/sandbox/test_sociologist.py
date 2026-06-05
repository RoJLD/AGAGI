import pytest
import os
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# We just test that the module imports correctly and has the main function.
# Real tests would require a mocked KuzuDB.

def test_sociologist_imports():
    try:
        import tools.kuzu_sociologist
        assert hasattr(tools.kuzu_sociologist, 'main')
    except ImportError as e:
        pytest.fail(f"Could not import kuzu_sociologist: {e}")
