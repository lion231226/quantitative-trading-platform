#!/usr/bin/env python3
"""
Sentry Configuration Verification Script
验证Sentry配置是否正确并测试连接
"""

import os
import sys
import requests
import time
from datetime import datetime

def check_environment_variables():
    """检查必需的环境变量是否已设置"""
    print("🔍 检查Sentry环境变量...")

    required_vars = [
        'SENTRY_DSN',
        'SENTRY_ENVIRONMENT',
        'SENTRY_TRACES_SAMPLE_RATE'
    ]

    frontend_vars = [
        'NEXT_PUBLIC_SENTRY_DSN',
        'NEXT_PUBLIC_SENTRY_ENVIRONMENT',
        'NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE'
    ]

    missing_vars = []

    # 检查后端变量
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"后端: {var}")
        else:
            print(f"✅ {var}: {'*' * 10}...{value[-10:]}")

    # 检查前端变量（在.env文件中）
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()

        for var in frontend_vars:
            if f"{var}=" in env_content:
                print(f"✅ {var}: 已在.env文件中配置")
            else:
                missing_vars.append(f"前端: {var}")

    if missing_vars:
        print(f"❌ 缺失的环境变量: {', '.join(missing_vars)}")
        return False

    print("✅ 所有必需的环境变量已配置")
    return True

def validate_dsn_format(dsn):
    """验证DSN格式是否正确"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(dsn)

        # 检查必需的组件
        if not all([parsed.scheme, parsed.netloc, parsed.path]):
            return False

        # 检查域名是否包含sentry
        if 'sentry.io' not in parsed.netloc and 'ingest.sentry.io' not in parsed.netloc:
            return False

        return True
    except:
        return False

def test_sentry_connection():
    """测试Sentry连接"""
    print("\n🌐 测试Sentry连接...")

    dsn = os.getenv('SENTRY_DSN')
    if not dsn:
        print("❌ 未找到SENTRY_DSN环境变量")
        return False

    if not validate_dsn_format(dsn):
        print("❌ DSN格式无效")
        return False

    try:
        # 发送测试请求到Sentry
        parsed_dsn = dsn.split('@')
        if len(parsed_dsn) < 2:
            print("❌ DSN格式错误")
            return False

        project_id = parsed_dsn[1].split('/')[-1]
        ingest_url = f"https://{parsed_dsn[1].split('/')[-2]}/api/{project_id}/store/"

        # 创建测试事件
        test_event = {
            "message": "Sentry配置验证测试",
            "level": "info",
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "python",
            "environment": os.getenv('SENTRY_ENVIRONMENT', 'development'),
            "release": "verification-test",
            "tags": {
                "test": True,
                "verification": True
            }
        }

        # 发送测试事件
        response = requests.post(
            ingest_url,
            json=test_event,
            headers={
                'Content-Type': 'application/json',
                'X-Sentry-Auth': f'Sentry sentry_key={dsn.split("@")[0].split("://")[1]}'
            },
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Sentry连接测试成功")
            print(f"📊 事件ID: {response.headers.get('X-Sentry-Event-Id', 'N/A')}")
            return True
        else:
            print(f"❌ Sentry连接失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def check_sentry_dependencies():
    """检查Sentry依赖是否已安装"""
    print("\n📦 检查Sentry依赖...")

    try:
        import sentry_sdk
        print("✅ sentry-sdk 已安装")
        print(f"   版本: {sentry_sdk.__version__}")
    except ImportError:
        print("❌ sentry-sdk 未安装")
        return False

    try:
        from fastapi import FastAPI
        print("✅ FastAPI 已安装")
    except ImportError:
        print("❌ FastAPI 未安装")
        return False

    return True

def generate_test_error():
    """生成测试错误以验证Sentry捕获"""
    print("\n🧪 生成测试错误...")

    try:
        import sentry_sdk

        # 初始化Sentry
        sentry_sdk.init(
            dsn=os.getenv('SENTRY_DSN'),
            environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            debug=os.getenv('SENTRY_DEBUG', 'false').lower() == 'true'
        )

        # 捕获测试异常
        try:
            # 故意引发一个异常
            raise ValueError("这是一个Sentry配置验证测试异常")
        except Exception as e:
            # 捕获并发送到Sentry
            sentry_sdk.capture_exception(e)
            print("✅ 测试异常已发送到Sentry")

        # 发送测试消息
        sentry_sdk.capture_message("Sentry配置验证完成", level="info")
        print("✅ 测试消息已发送到Sentry")

        # 等待一下让事件发送
        time.sleep(2)

        return True

    except Exception as e:
        print(f"❌ 生成测试错误失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Sentry配置验证开始...\n")

    # 检查环境变量
    env_ok = check_environment_variables()

    # 检查依赖
    deps_ok = check_sentry_dependencies()

    # 测试连接
    connection_ok = test_sentry_connection()

    # 生成测试错误
    if env_ok and deps_ok and connection_ok:
        test_ok = generate_test_error()
    else:
        test_ok = False

    # 输出结果
    print(f"\n{'='*50}")
    print("📊 验证结果总结:")
    print(f"环境变量配置: {'✅ 通过' if env_ok else '❌ 失败'}")
    print(f"依赖安装检查: {'✅ 通过' if deps_ok else '❌ 失败'}")
    print(f"Sentry连接测试: {'✅ 通过' if connection_ok else '❌ 失败'}")
    print(f"测试错误生成: {'✅ 通过' if test_ok else '❌ 失败'}")

    if all([env_ok, deps_ok, connection_ok, test_ok]):
        print("\n🎉 Sentry配置验证完成！系统监控已就绪。")
        print("\n📱 请在Sentry控制台中查看测试事件:")
        print("   - 前端项目: https://sentry.io/organizations/your-org/issues/?project=4510465805975632")
        print("   - 后端项目: https://sentry.io/organizations/your-org/issues/?project=4510465825177680")
        return 0
    else:
        print("\n❌ Sentry配置验证失败，请检查上述错误。")
        return 1

if __name__ == "__main__":
    sys.exit(main())