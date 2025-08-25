# EaseMyTrip Flight Automation

A comprehensive automated testing framework for EaseMyTrip flight booking platform using Playwright and Python. This project implements intelligent flight filtering, real-time airport code extraction, and automated validation with professional Excel reporting.

##  Features

- **Intelligent City Selection**: Character-by-character typing with autocomplete handling and score-based matching
- **Real Airport Code Extraction**: Dynamic extraction from website selections using regex patterns
- **Multi-Strategy Optimization**: Optimized UI interaction strategies for maximum reliability
- **Enhanced Delhi Handling**: Special variations and improved error handling for Delhi city selection
- **Professional Reporting**: Comprehensive Excel reports with flight details and automation results
- **Dual Testing Modes**: Core automation tests and data-driven test scenarios
- **Comprehensive Logging**: Detailed logs for debugging and test monitoring

## 📁 Project Structure

```
EaseMyTrip_Flight_Automation/
├── README.md                           # Project documentation
├── conftest.py                         # Pytest configuration and fixtures
├── pytest.ini                         # Pytest settings
├── run_tests.py                        # Main test execution script
├── config/
│   ├── requirements.txt                # Python dependencies
│   └── test_data.json                  # Test case data for data-driven tests
├── src/
│   ├── __init__.py
│   ├── automation/
│   │   ├── __init__.py
│   │   └── flight_filter_engine.py     # Core automation engine (optimized)
│   └── utils/
│       ├── __init__.py
│       ├── config.py                   # Configuration management
│       └── logger.py                   # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── test_framework.py               # Base test framework
│   ├── test_part1_core_automation.py   # Core automation tests
│   ├── test_part2_data_driven.py       # Data-driven tests
├── results/
│   ├── part1/                          # Part 1 test results
│   │   ├── *.xlsx                      # Excel reports
│   │   └── *.html                      # HTML test reports
│   └── part2/                          # Part 2 test results
│       ├── *.xlsx                      # Excel reports  
│       └── *.html                      # HTML test reports
└── logs/                               # Test execution logs
    └── *.log                           # Detailed test logs
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Internet connection for package installation and browser download

### Installation Steps

1. **Clone or Download the Project**
   ```bash
   git clone <repository-url>
   cd EaseMyTrip_Flight_Automation
   ```

2. **Create Virtual Environment** (Recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   venv\Scripts\activate     # On Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r config/requirements.txt
   ```

4. **Install Playwright Browsers**
   ```bash
   playwright install chromium
   ```

## 🧪 Test Execution

### Part 1: Core Automation Tests

Tests the fundamental automation capabilities with hardcoded test data:

```bash
# Run Part 1 tests
python run_part1.py

# Alternative direct execution
pytest tests/test_part1_core_automation.py -v --html=results/part1/report.html
```

**Part 1 Test Case:**
- Provided the hard coded values

### Part 2: Data-Driven Tests

Executes multiple test scenarios from `config/test_data.json`:

```bash
# Run Part 2 tests
python run_part2.py

# Alternative direct execution  
pytest tests/test_part2_data_driven.py -v --html=results/part2/report.html
```

### Run All Tests

Execute both test suites:

```bash
python run_tests.py
```

## 📊 Sample Input Data

### Test Data Format (`config/test_data.json`)

```json
[
    {
        "test_id": "TC001",
        "description": "Find 1-stop flights from Delhi to Mumbai with realistic pricing",
        "from_city": "Delhi",
        "to_city": "Mumbai", 
        "departure_date": "2025-09-01",
        "stops_filter": "1 Stop",
        "price_min": 6000,
        "price_max": 7000
    },
    {
        "test_id": "TC002", 
        "description": "Find non-stop flights from Bengaluru to Mumbai",
        "from_city": "Bengaluru",
        "to_city": "Mumbai",
        "departure_date": "2025-09-02",
        "stops_filter": "Non-stop",
        "price_min": 3000,
        "price_max": 4500
    },
    {
        "test_id": "TC003",
        "description": "Find 2+ stop flights from Hyderabad to Delhi", 
        "from_city": "Hyderabad",
        "to_city": "Delhi",
        "departure_date": "2025-09-03",
        "stops_filter": "2+ Stop",
        "price_min": 5000,
        "price_max": 7000
    }
]
```

### Filter Options

- **Stops**: "Non-stop", "1 Stop", "2+ Stop"
- **Price Range**: Minimum and maximum price in INR
- **Date Format**: YYYY-MM-DD

## 📈 Output Files

### Excel Reports
- **Part 1**: `results/part1/Part1_Core_Automation_Pytest_Results_YYYYMMDD_HHMMSS.xlsx`
- **Part 2**: `results/part2/Part2_Data_Driven_Pytest_Test_Results_YYYYMMDD_HHMMSS.xlsx`

### HTML Reports  
- **Part 1**: `results/part1/Part1_Pytest_Report_YYYYMMDD_HHMMSS.html`
- **Part 2**: `results/part2/Part2_Pytest_Report_YYYYMMDD_HHMMSS.html`

### Logs
- Detailed execution logs in `logs/` directory
- Dual output: console and file logging
- Enhanced debugging information

---


