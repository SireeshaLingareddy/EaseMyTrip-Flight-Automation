#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures for EaseMyTrip Automation
Compatible with PyCharm IDE and VS Code
"""

import os
import sys
import pytest
import json
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import project modules
from src.automation.flight_filter_engine import PureUIFilterEngine
from src.utils.config import TestConfig
from src.utils.logger import TestLogger


@pytest.fixture(scope="session")
def project_root():
    """Provide project root directory path"""
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def logger():
    """Provide configured logger instance for all tests"""
    test_logger = TestLogger()
    logger_instance = test_logger.logger
    logger_instance.info("=" * 80)
    logger_instance.info(" PYTEST SESSION STARTED - EaseMyTrip Automation")
    logger_instance.info("=" * 80)
    return logger_instance


@pytest.fixture(scope="session")
def automation_engine():
    """Provide the automation engine instance for all tests"""
    return PureUIFilterEngine()

@pytest.fixture(scope="session")
def test_data_configs():
    """Load test data configurations from JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'test_data.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        configs = []
        for test_case in data:
            config = TestConfig.from_dict(test_case)
            configs.append(config)
        
        return configs
    
    except Exception as e:
        pytest.fail(f"Failed to load test data from {config_path}: {str(e)}")


@pytest.fixture(scope="function")
def part1_hardcoded_config():
    """Provide hardcoded configuration for Part 1 core automation"""
    return TestConfig(
        test_id="PART1_CORE_PYTEST",
        description="Part 1 core automation: 1 Stop flights Delhi to Bengaluru with ₹4000-₹8000 price range",
        from_city="Ahmedabad",
        to_city="Goa",
        departure_date="2025-09-01",
        stops_filter="Non-stop",
        price_min=2000,
        price_max=8000
    )


@pytest.fixture(scope="function")
def results_directory():
    """Ensure results directory exists and provide path"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


@pytest.fixture(scope="function")
def logs_directory():
    """Ensure logs directory exists and provide path"""
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Ensure results directory exists
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)


def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("\n" + "="*80)
    print(" EaseMyTrip Flight Automation - Pytest Session Started")
    print(" PyCharm & VS Code Compatible")
    print(" Session Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    print("\n" + "="*80)
    print(" EaseMyTrip Flight Automation - Pytest Session Finished")
    print(f" Exit Status: {exitstatus}")
    print(" Session End:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)


def pytest_collection_modifyitems(config, items):
    """Modify test items after collection"""
    # Add markers based on test names
    for item in items:
        if "part1" in item.name.lower():
            item.add_marker(pytest.mark.part1)
        elif "part2" in item.name.lower():
            item.add_marker(pytest.mark.part2)
        
        # Add UI marker for all tests (since they use Playwright)
        item.add_marker(pytest.mark.ui)
        
        # Add slow marker for integration tests
        if "integration" in item.name.lower() or "data_driven" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# PyCharm specific configuration
def configure_pycharm():
    """Additional configuration for PyCharm IDE compatibility"""
    # This function helps PyCharm recognize pytest configuration
    pass


# Custom pytest hooks for better reporting
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Custom test report generation for better logging"""
    outcome = yield
    rep = outcome.get_result()
    
    # Add custom attributes for HTML reporting
    if rep.when == "call":
        if hasattr(item, '_test_config'):
            rep.test_config = item._test_config
        if hasattr(item, '_test_result'):
            rep.test_result = item._test_result
