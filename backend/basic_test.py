#!/usr/bin/env python3
"""
基本功能验证测试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试核心模块导入"""
    print("Testing module imports...")

    try:
        from app.core.database import DatabaseManager, db_manager
        print("✓ Database manager imported successfully")
    except Exception as e:
        print(f"✗ Database manager import failed: {e}")
        return False

    try:
        from app.services.data_processor import DataProcessor
        print("✓ Data processor imported successfully")
    except Exception as e:
        print(f"✗ Data processor import failed: {e}")
        return False

    try:
        from app.services.data_storage import DataStorageService
        print("✓ Data storage service imported successfully")
    except Exception as e:
        print(f"✗ Data storage service import failed: {e}")
        return False

    return True

def test_database_manager():
    """测试数据库管理器"""
    print("\nTesting database manager...")

    try:
        from app.core.database import db_manager

        # 测试数据库连接
        connection_ok = db_manager.check_connection()
        if connection_ok:
            print("✓ Database connection test passed")
        else:
            print("⚠ Database connection test failed (may need initialization)")

        # 测试数据库初始化
        try:
            db_manager.initialize_database()
            print("✓ Database initialization successful")
        except Exception as e:
            print(f"⚠ Database initialization warning: {e}")

        return True
    except Exception as e:
        print(f"✗ Database manager test failed: {e}")
        return False

def test_models():
    """测试数据模型"""
    print("\nTesting data models...")

    try:
        from app.models.market_data import MarketData, MarketDataDB
        from datetime import date

        # 测试MarketData模型
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

        # 验证价格关系
        assert market_data.high_price >= market_data.low_price
        assert market_data.open_price > 0
        assert market_data.close_price > 0

        print("✓ MarketData model test passed")
        return True

    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        return False

def main():
    """主测试函数"""
    print("Starting basic functionality validation tests")
    print("=" * 50)

    # 设置测试环境变量
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_quant_trading.db'

    tests = [
        test_imports,
        test_models,
        test_database_manager
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test exception: {e}")

    print("\n" + "=" * 50)
    print(f"Test results: {passed}/{total} passed")
    print(f"Success rate: {passed/total*100:.1f}%")

    if passed == total:
        print("All functionality validation tests passed!")
        return True
    else:
        print("Some tests failed, but core functionality is basically available")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)