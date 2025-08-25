#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures for EaseMyTrip Automation
"""

import sys
import pytest
import gc
import psutil
import os
import json
import time
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
def logger():
    """Provide configured logger instance for all tests"""
    test_logger = TestLogger()
    logger_instance = test_logger.logger
    logger_instance.info("=" * 80)
    logger_instance.info(" PYTEST SESSION STARTED - EaseMyTrip Automation")
    logger_instance.info("=" * 80)
    return logger_instance


@pytest.fixture(scope="function") 
def automation_engine():
    """Provide fresh automation engine instance for each test"""
    engine = PureUIFilterEngine()
    yield engine
    
    # Aggressive cleanup after each test
    try:
        # Force garbage collection
        gc.collect()
        
        # Kill any remaining chromium processes
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower():
                    proc.terminate()
        except:
            pass
        
        # Additional cleanup pause
        time.sleep(1)
        
    except Exception as cleanup_error:
        print(f"Cleanup warning: {cleanup_error}")
        pass

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
        departure_date="2025-12-01",
        stops_filter="1 Stop",
        price_min=6000,
        price_max=20000
    )


@pytest.fixture(scope="function")
def results_directory():
    """Ensure results directory exists and provide path"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Ensure results directory exists
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
