#!/usr/bin/env python3
"""
Master Run Script for EaseMyTrip Automation Tests
Provides options to run Part 1, Part 2, or both with organized output
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

def create_results_structure():
    """Create organized results directory structure"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create main results directory
    results_dir = os.path.join(project_root, "results")
    part1_dir = os.path.join(results_dir, "part1")
    part2_dir = os.path.join(results_dir, "part2")
    
    os.makedirs(part1_dir, exist_ok=True)
    os.makedirs(part2_dir, exist_ok=True)
    
    return project_root, part1_dir, part2_dir

def run_part1():
    """Run Part 1 Core Automation Tests"""
    project_root, part1_dir, _ = create_results_structure()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = os.path.join(part1_dir, f"Part1_Pytest_Report_{timestamp}.html")
    
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_part1_core_automation.py",
        "--verbose",
        "--tb=short",
        "--disable-warnings",
        f"--html={html_report}",
        "--self-contained-html"
    ]
    
    print(" Running Part 1 Core Automation Tests...")
    print(f" HTML Report: {html_report}")
    
    result = subprocess.run(pytest_cmd, cwd=project_root)
    return result.returncode, html_report

def run_part2():
    """Run Part 2 Data-Driven Tests"""
    project_root, _, part2_dir = create_results_structure()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = os.path.join(part2_dir, f"Part2_Pytest_Report_{timestamp}.html")
    
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_part2_data_driven.py",
        "--verbose",
        "--tb=short",
        "--disable-warnings",
        f"--html={html_report}",
        "--self-contained-html"
    ]
    
    print(" Running Part 2 Data-Driven Tests...")
    print(f" HTML Report: {html_report}")
    
    result = subprocess.run(pytest_cmd, cwd=project_root)
    return result.returncode, html_report

def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description="EaseMyTrip Automation Test Runner")
    parser.add_argument("--part", choices=["1", "2", "both"], default="both",
                       help="Which part to run (default: both)")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" EaseMyTrip Flight Automation - Pytest Test Runner")
    print(" Framework: Pytest + Playwright + PyCharm Compatible")
    print("=" * 80)
    
    results = []
    
    if args.part in ["1", "both"]:
        print("\n" + "=" * 50)
        print(" PART 1: Core Automation Testing")
        print("=" * 50)
        exit_code, report_path = run_part1()
        results.append(("Part 1", exit_code, report_path))
    
    if args.part in ["2", "both"]:
        print("\n" + "=" * 50)
        print(" PART 2: Data-Driven Testing")
        print("=" * 50)
        exit_code, report_path = run_part2()
        results.append(("Part 2", exit_code, report_path))
    
    # Summary
    print("\n" + "=" * 80)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    for part_name, exit_code, report_path in results:
        status = " PASSED" if exit_code == 0 else f" FAILED (exit code: {exit_code})"
        print(f"{part_name}: {status}")
        print(f"    Report: {report_path}")
    
    overall_success = all(exit_code == 0 for _, exit_code, _ in results)
    
    if overall_success:
        print("\n All tests completed successfully!")
        return 0
    else:
        print("\n Some tests had issues. Check individual reports for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
