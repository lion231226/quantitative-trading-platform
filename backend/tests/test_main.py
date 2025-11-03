import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestMainAPI:
    """主API端点测试"""

    def test_root_endpoint(self):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert "docs" in data

        assert data["status"] == "healthy"
        assert "量化交易单均线策略分析平台 API" in data["message"]

    def test_health_check_endpoint(self):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "api_version" in data

    def test_api_docs_endpoint(self):
        """测试API文档端点"""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_api_openapi_endpoint(self):
        """测试OpenAPI规范端点"""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_invalid_endpoint(self):
        """测试无效端点"""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

class TestAPIResponseFormat:
    """API响应格式测试"""

    def test_error_response_format(self):
        """测试错误响应格式"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

        data = response.json()
        # 注意：这里可能需要根据实际的错误处理调整
        assert "detail" in data or "error" in data

    def test_success_response_format(self):
        """测试成功响应格式"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert all(isinstance(value, str) for value in data.values())

class TestCORS:
    """CORS配置测试"""

    def test_cors_headers(self):
        """测试CORS头"""
        response = client.options("/")
        assert response.status_code == 200

        # 检查CORS相关的头
        headers = response.headers
        assert "access-control-allow-origin" in headers or "Access-Control-Allow-Origin" in headers

class TestPerformance:
    """性能测试"""

    def test_response_time(self):
        """测试响应时间"""
        import time

        start_time = time.time()
        response = client.get("/")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # 响应时间应少于1秒

    def test_concurrent_requests(self):
        """测试并发请求"""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/")
            results.append(response.status_code)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert all(status == 200 for status in results)
        assert len(results) == 10