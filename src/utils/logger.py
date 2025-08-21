#!/usr/bin/env python3
"""
Logging utilities for EaseMyTrip automation
"""
import logging
import os
from datetime import datetime
from typing import Optional


class TestLogger:
    """Enhanced logging for test execution"""
    
    def __init__(self, log_file: Optional[str] = None, logs_dir: str = "logs"):
        """
        Initialize logger with optional custom log file
        Args:
            log_file: Custom log file name (optional)
            logs_dir: Directory for log files
        """
        self.logs_dir = logs_dir
        
        # Ensure logs directory exists
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Set log file name
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"easymytrip_test_{timestamp}.log"
        
        self.log_file = os.path.join(logs_dir, log_file)
        
        # Set up logger
        self.logger = logging.getLogger("EaseMyTripAutomation")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        """Get the configured logger instance"""
        return self.logger
