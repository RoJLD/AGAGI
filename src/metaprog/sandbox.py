"""
Phase 8: Closed-Loop Metaprogramming - Sandbox Execution.
"""
import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def inject_and_test(code_string: str) -> bool:
    """
    Injects auto-generated code into a sandbox environment and runs a dummy test.
    Commandement 6: Sécurité & Isolation.
    Commandement 7: Validation Rigoureuse.
    """
    sandbox_dir = Path("tests/sandbox")
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = sandbox_dir / "generated_op.py"
    test_file = sandbox_dir / "test_generated_op.py"
    
    # 1. Write the generated code
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(code_string)
            
        # 2. Write a dummy unit test
        test_code = '''import numpy as np
import pytest
from generated_op import new_activation

def test_new_activation():
    x = np.array([-1.0, 0.0, 1.0])
    result = new_activation(x)
    assert result.shape == x.shape
    assert not np.isnan(result).any()
    assert not np.isinf(result).any()
'''
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
            
        # 3. Run pytest in a subprocess with Timeout (Sandbox)
        logger.info(f"Running sandboxed tests on {test_file}")
        # Commandement 6: Timeout strict
        result = subprocess.run(
            ["pytest", str(test_file)],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        
        if result.returncode == 0:
            logger.info("Sandbox test passed.")
            return True
        else:
            logger.error(f"Sandbox test failed:\\n{result.stderr}\\n{result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Sandbox execution timed out!")
        return False
    except Exception as e:
        logger.error(f"Sandbox error: {e}")
        return False
