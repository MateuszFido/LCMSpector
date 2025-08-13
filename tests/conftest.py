"""
Pytest configuration and shared fixtures for LC-Inspector test suite.

This module provides test configuration and shared fixtures that are available
to all test modules in the LC-Inspector test suite.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the lc-inspector directory to the path for all tests
test_dir = Path(__file__).parent
project_root = test_dir.parent
lc_inspector_dir = project_root / 'lc-inspector'

sys.path.insert(0, str(lc_inspector_dir))
sys.path.insert(0, str(project_root))

# Import shared fixtures from test utilities
from tests.fixtures.test_utilities import (
    stmix_concentration_series,
    aminoacids_polyamines_compounds,
    stmix_filename_parser,
    synthetic_peak_data,
    validation_utilities,
    test_tolerances,
    temp_test_directory
)

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "regression: mark test as a regression test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "stmix: mark test as using STMIX data"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "regression" in str(item.fspath):
            item.add_marker(pytest.mark.regression)
        
        # Add STMIX marker for STMIX-related tests
        if "stmix" in str(item.fspath).lower() or "stmix" in item.name.lower():
            item.add_marker(pytest.mark.stmix)

# Test execution options
def pytest_addoption(parser):
    """Add custom command line options for test execution."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--stmix-only",
        action="store_true", 
        default=False,
        help="run only STMIX validation tests"
    )

def pytest_runtest_setup(item):
    """Setup function called before each test."""
    # Skip slow tests unless --run-slow is given
    if "slow" in item.keywords and not item.config.getoption("--run-slow"):
        pytest.skip("need --run-slow option to run")
    
    # Run only STMIX tests if --stmix-only is given
    if item.config.getoption("--stmix-only") and "stmix" not in item.keywords:
        pytest.skip("running only STMIX tests")

# Shared test fixtures
@pytest.fixture(scope="session", autouse=True)
def test_environment_setup():
    """Set up test environment and verify dependencies."""
    # Verify required directories exist
    required_dirs = [
        project_root / 'lc-inspector',
        project_root / 'tests',
        project_root / 'tests' / 'unit',
        project_root / 'tests' / 'integration',
        project_root / 'tests' / 'regression',
        project_root / 'tests' / 'fixtures'
    ]
    
    for dir_path in required_dirs:
        assert dir_path.exists(), f"Required directory missing: {dir_path}"
    
    # Verify key files exist
    key_files = [
        project_root / 'config.json',
        lc_inspector_dir / 'calculation' / 'calc_conc.py',
        lc_inspector_dir / 'ui' / 'model.py'
    ]
    
    for file_path in key_files:
        if not file_path.exists():
            pytest.skip(f"Required file missing: {file_path}")
    
    print(f"\nTest environment setup complete")
    print(f"Project root: {project_root}")
    print(f"LC-Inspector directory: {lc_inspector_dir}")

@pytest.fixture
def mock_logger():
    """Provide a mock logger for tests that need logging."""
    import logging
    from unittest.mock import Mock
    
    mock_log = Mock(spec=logging.Logger)
    mock_log.info = Mock()
    mock_log.warning = Mock()
    mock_log.error = Mock()
    mock_log.debug = Mock()
    
    return mock_log

@pytest.fixture
def concentration_test_data():
    """Provide standard test data for concentration calculations."""
    return {
        'concentrations': [0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        'slope': 10000.0,
        'intercept': 1000.0,
        'r_squared_threshold': 0.95,
        'tolerance': 0.15
    }

# Error handling fixtures
@pytest.fixture
def capture_warnings():
    """Capture warnings during test execution."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        yield w

# Performance monitoring fixtures
@pytest.fixture
def performance_timer():
    """Monitor test execution time."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.elapsed()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()