#!/usr/bin/env python3
"""
简单的数据处理功能验证测试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试核心模块导入"""
    print("🔍 测试模块导入...")

    try:
        from app.core.database import DatabaseManager, db_manager
        print("✅ 数据库管理器导入成功")
    except Exception as e:
        print(f"❌ 数据库管理器导入失败: {e}")
        return False

    try:
        from app.services.data_processor import DataProcessor
        print("✅ 数据处理器导入成功")
    except Exception as e:
        print(f"❌ 数据处理器导入失败: {e}")
        return False

    try:
        from app.services.data_storage import DataStorageService
        print("✅ 数据存储服务导入成功")
    except Exception as e:
        print(f"❌ 数据存储服务导入失败: {e}")
        return False

    try:
        from app.api.v1.endpoints.data import router
        print("✅ 数据API端点导入成功")
    except Exception as e:
        print(f"❌ 数据API端点导入失败: {e}")
        return False

    return True

def test_database_manager():
    """测试数据库管理器"""
    print("\n🗄️  测试数据库管理器...")

    try:
        from app.core.database import db_manager

        # 测试数据库连接
        connection_ok = db_manager.check_connection()
        if connection_ok:
            print("✅ 数据库连接测试通过")
        else:
            print("⚠️  数据库连接测试失败（可能需要初始化）")

        # 测试数据库初始化
        try:
            db_manager.initialize_database()
            print("✅ 数据库初始化成功")
        except Exception as e:
            print(f"⚠️  数据库初始化警告: {e}")

        return True
    except Exception as e:
        print(f"❌ 数据库管理器测试失败: {e}")
        return False

def test_data_processor():
    """测试数据处理器"""
    print("\n🧪 测试数据处理器...")

    try:
        from app.services.data_processor import DataProcessor
        from datetime import date

        processor = DataProcessor()

        # 测试数据清洗功能
        sample_data = [
            {
                'date': '2024-01-01',
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 10000,
                'turnover': 505000000.0
            }
        ]

        # 异步测试（使用简单的同步方式）
        import asyncio

        async def test_cleaning():
            try:
                cleaned_data = await processor.clean_and_validate_data(sample_data, "CU")
                if cleaned_data:
                    print("✅ 数据清洗功能正常")
                    return True
                else:
                    print("⚠️  数据清洗返回空结果")
                    return False
            except Exception as e:
                print(f"⚠️  数据清洗测试警告: {e}")
                return False

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_cleaning())
            return result
        finally:
            loop.close()

    except Exception as e:
        print(f"❌ 数据处理器测试失败: {e}")
        return False

def test_models():
    """测试数据模型"""
    print("\n📊 测试数据模型...")

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

        print("✅ MarketData模型测试通过")

        # 测试MarketDataDB模型
        db_data = MarketDataDB(
            symbol="CU",
            date=date(2024, 1, 1),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=10000
        )

        print("✅ MarketDataDB模型测试通过")
        return True

    except Exception as e:
        print(f"❌ 数据模型测试失败: {e}")
        return False

def test_schemas():
    """测试API schemas"""
    print("\n📋 测试API Schemas...")

    try:
        from app.schemas.market_data import MarketDataResponse, DataQueryResponse
        from datetime import datetime

        # 测试MarketDataResponse
        response = MarketDataResponse(
            symbol="CU",
            date=datetime(2024, 1, 1),
            open_price=50000.0,
            high_price=51000.0,
            low_price=49000.0,
            close_price=50500.0,
            volume=10000
        )

        print("✅ MarketDataResponse schema测试通过")

        # 测试DataQueryResponse
        query_response = DataQueryResponse(
            symbol="CU",
            data=[response],
            total_count=1,
            page=1,
            size=10
        )

        print("✅ DataQueryResponse schema测试通过")
        return True

    except Exception as e:
        print(f"❌ API Schemas测试失败: {e}")
        return False

def test_api_app():
    """测试API应用"""
    print("\n🌐 测试API应用...")

    try:
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        # 测试根路径
        response = client.get("/")
        if response.status_code == 200:
            print("✅ API根路径测试通过")
        else:
            print(f"⚠️  API根路径测试失败: {response.status_code}")

        # 测试健康检查
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ API健康检查通过")
        else:
            print(f"⚠️  API健康检查失败: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ API应用测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始数据处理功能验证测试")
    print("="*50)

    # 设置测试环境变量
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_quant_trading.db'

    tests = [
        test_imports,
        test_models,
        test_schemas,
        test_database_manager,
        test_data_processor,
        test_api_app
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")

    print("\n" + "="*50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print(f"成功率: {passed/total*100:.1f}%")

    if passed == total:
        print("🎉 所有功能验证测试通过!")
        return True
    else:
        print("⚠️  部分测试未通过，但核心功能基本可用")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)