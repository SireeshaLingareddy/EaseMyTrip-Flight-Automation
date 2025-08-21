#!/usr/bin/env python3
"""
Configuration classes and data structures for EaseMyTrip automation
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TestConfig:
    """Configuration for each test case"""
    test_id: str
    departure_city: str = ""
    arrival_city: str = ""
    departure_date: str = ""  # YYYY-MM-DD format from JSON
    stops_filter: str = ""    # "1 Stop", "Non-stop", "2+ Stop"
    airline_filter: str = ""  # Airline name for filtering (optional)
    
    # Additional fields for Part 2 compatibility
    description: str = ""
    from_city: str = ""       # Legacy field mapping
    to_city: str = ""         # Legacy field mapping  
    price_min: int = 0
    price_max: int = 0
    
    # def __post_init__(self):
    #     """Handle field mapping for compatibility"""
    #     # Map legacy fields to new fields
    #     if self.from_city and not self.departure_city:
    #         self.departure_city = self.from_city
    #     if self.to_city and not self.arrival_city:
    #         self.arrival_city = self.to_city
    #     # Map new fields to legacy fields for backward compatibility
    #     if self.departure_city and not self.from_city:
    #         self.from_city = self.departure_city
    #     if self.arrival_city and not self.to_city:
    #         self.to_city = self.arrival_city

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestConfig':
        """Create TestConfig from dictionary"""
        return cls(
            test_id=data.get('test_id', ''),
            departure_city=data.get('departure_city', data.get('from_city', '')),
            arrival_city=data.get('arrival_city', data.get('to_city', '')),
            departure_date=data.get('departure_date', ''),
            stops_filter=data.get('stops_filter', ''),
            airline_filter=data.get('airline_filter', ''),
            description=data.get('description', ''),
            from_city=data.get('from_city', ''),
            to_city=data.get('to_city', ''),
            price_min=data.get('price_min', 0),
            price_max=data.get('price_max', 0)
        )


@dataclass
class AppConfig:
    """Application-wide configuration"""
    # Browser settings
    browser_headless: bool = False
    browser_timeout: int = 30000
    page_load_timeout: int = 60000
    
    # Test settings
    wait_between_actions: float = 1.0
    max_retries: int = 3
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "easymytrip_automation.log"
    
    # Output settings
    results_dir: str = "results"
    
    @classmethod
    def get_default(cls) -> 'AppConfig':
        """Get default application configuration"""
        return cls()
