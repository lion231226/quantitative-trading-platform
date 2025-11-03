#!/usr/bin/env python3
"""
Simple validation test without Unicode
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test core module imports"""
    print("Testing module imports...")

    try:
        from app.core.database import DatabaseManager, db_manager
        print("OK: Database manager imported successfully")
    except Exception as e:
        print(f"FAIL: Database manager import failed: {e}")
        return False

    try:
        from app.services.data_processor import DataProcessor
        print("OK: Data processor imported successfully")
    except Exception as e:
        print(f"FAIL: Data processor import failed: {e}")
        return False

    try:
        from app.services.data_storage import DataStorageService
        print("OK: Data storage service imported successfully")
    except Exception as e:
        print(f"FAIL: Data storage service import failed: {e}")
        return False

    return True

def test_models():
    """Test data models"""
    print("\nTesting data models...")

    try:
        from app.models.market_data import MarketData, MarketDataDB
        from datetime import date

        # Test MarketData model
        market_data = MarketData(
            symbol="CU",
            date=date(2024, 1, 1),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=10000,
            turnover=505000000.0
        )

        # Validate price relationships
        assert market_data.high_price >= market_data.low_price
        assert market_data.open_price > 0
        assert market_data.close_price > 0

        print("OK: MarketData model test passed")
        return True

    except Exception as e:
        print(f"FAIL: Data model test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting basic functionality validation")
    print("=" * 50)

    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_quant_trading.db'

    tests = [
        test_imports,
        test_models
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: Test exception: {e}")

    print("\n" + "=" * 50)
    print(f"Test results: {passed}/{total} passed")
    print(f"Success rate: {passed/total*100:.1f}%")

    if passed == total:
        print("All validation tests passed!")
        return True
    else:
        print("Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)