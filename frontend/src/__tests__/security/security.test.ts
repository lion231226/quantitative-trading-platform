/**
 * 安全功能测试套件
 *
 * 测试覆盖:
 * 1. 输入验证和清理
 * 2. XSS防护
 * 3. CSRF保护
 * 4. 加密功能
 * 5. 安全头配置
 */

import { describe, it, expect, beforeEach } from '@jest/globals';
import {
  sanitizeInput,
  escapeHtml,
  escapeSql,
  validateInput,
  apiSchemas,
  securityFilter,
  InputValidator,
  Encryption
} from '../../utils/security/inputValidation';

describe('输入验证和安全清理', () => {
  describe('sanitizeInput', () => {
    it('应该移除危险字符', () => {
      const input = '<script>alert("xss")</script>';
      const result = sanitizeInput(input);
      expect(result).toBe('scriptalert("xss")/script');
    });

    it('应该移除JavaScript事件处理器', () => {
      const input = '<img onclick="alert(1)" src="test.jpg">';
      const result = sanitizeInput(input);
      expect(result).not.toContain('onclick');
    });

    it('应该移除JavaScript协议', () => {
      const input = 'javascript:alert("xss")';
      const result = sanitizeInput(input);
      expect(result).toBe('alert("xss")');
    });

    it('应该截断过长的输入', () => {
      const input = 'a'.repeat(1001);
      const result = sanitizeInput(input);
      expect(result.length).toBe(1000);
    });

    it('应该处理非字符串输入', () => {
      expect(sanitizeInput(null)).toBe('');
      expect(sanitizeInput(undefined)).toBe('');
      expect(sanitizeInput(123)).toBe('');
    });
  });

  describe('escapeHtml', () => {
    it('应该转义HTML特殊字符', () => {
      const input = '<script>alert("xss")</script>';
      const result = escapeHtml(input);
      expect(result).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
    });

    it('应该转义单引号和双引号', () => {
      const input = '"test" and \'test\'';
      const result = escapeHtml(input);
      expect(result).toBe('&quot;test&quot; and &#039;test&#039;');
    });
  });

  describe('escapeSql', () => {
    it('应该转义SQL特殊字符', () => {
      const input = "'; DROP TABLE users; --";
      const result = escapeSql(input);
      expect(result).toBe(''' DROP TABLE users ');
    });

    it('应该移除SQL注释', () => {
      const input = 'SELECT * FROM users /* comment */';
      const result = escapeSql(input);
      expect(result).toBe('SELECT * FROM users ');
    });
  });

  describe('validateInput with Zod schemas', () => {
    it('应该验证邮箱格式', async () => {
      const validator = validateInput(apiSchemas.register.shape.email);

      const validResult = await validator('test@example.com');
      expect(validResult.success).toBe(true);

      const invalidResult = await validator('invalid-email');
      expect(invalidResult.success).toBe(false);
      expect(invalidResult.errors).toContain('邮箱格式不正确');
    });

    it('应该验证用户名格式', async () => {
      const validator = validateInput(apiSchemas.register.shape.username);

      const validResult = await validator('valid_user123');
      expect(validResult.success).toBe(true);

      const invalidResult = await validator('invalid user!');
      expect(invalidResult.success).toBe(false);
    });

    it('应该验证密码强度', async () => {
      const validator = validateInput(apiSchemas.register.shape.password);

      const validResult = await validator('StrongPass123');
      expect(validResult.success).toBe(true);

      const weakResult = await validator('weak');
      expect(weakResult.success).toBe(false);
      expect(weakResult.errors).toContain('密码必须包含大小写字母和数字');
    });

    it('应该验证分页参数', async () => {
      const validator = validateInput(apiSchemas.paginatedQuery);

      const validResult = await validator({ page: 1, limit: 10 });
      expect(validResult.success).toBe(true);

      const invalidResult = await validator({ page: -1, limit: 0 });
      expect(invalidResult.success).toBe(false);
    });
  });

  describe('securityFilter', () => {
    it('应该过滤XSS攻击', () => {
      const input = '<script>alert("xss")</script>';
      const result = securityFilter.xss(input);
      expect(result).not.toContain('<script>');
      expect(result).not.toContain('</script>');
    });

    it('应该过滤SQL注入', () => {
      const input = "'; DROP TABLE users; --";
      const result = securityFilter.sql(input);
      expect(result).not.toContain("'");
      expect(result).not.toContain('--');
    });

    it('应该移除脚本标签', () => {
      const input = '<script>alert("test")</script><p>content</p>';
      const result = securityFilter.scripts(input);
      expect(result).not.toContain('<script>');
      expect(result).toContain('<p>content</p>');
    });

    it('应该移除样式标签', () => {
      const input = '<style>body { color: red; }</style><p>content</p>';
      const result = securityFilter.styles(input);
      expect(result).not.toContain('<style>');
      expect(result).toContain('<p>content</p>');
    });

    it('应该移除所有HTML标签', () => {
      const input = '<div><p>Hello <strong>World</strong></p></div>';
      const result = securityFilter.stripHtml(input);
      expect(result).toBe('Hello World');
    });
  });

  describe('InputValidator class', () => {
    let validator: InputValidator;

    beforeEach(() => {
      validator = new InputValidator();
    });

    it('应该验证字符串', () => {
      const result = validator.string('test', { minLength: 3, maxLength: 10 });
      expect(result).toBe('test');
      expect(validator.hasErrors()).toBe(false);

      const shortResult = validator.string('ab', { minLength: 3 });
      expect(shortResult).toBeNull();
      expect(validator.hasErrors()).toBe(true);
    });

    it('应该验证数字', () => {
      const result = validator.number('123', { min: 100, max: 200 });
      expect(result).toBe(123);
      expect(validator.hasErrors()).toBe(false);

      const outOfRangeResult = validator.number('300', { max: 200 });
      expect(outOfRangeResult).toBeNull();
      expect(validator.hasErrors()).toBe(true);
    });

    it('应该验证邮箱', () => {
      const result = validator.email('test@example.com');
      expect(result).toBe('test@example.com');
      expect(validator.hasErrors()).toBe(false);

      const invalidResult = validator.email('invalid-email');
      expect(invalidResult).toBeNull();
      expect(validator.hasErrors()).toBe(true);
    });

    it('应该验证URL', () => {
      const result = validator.url('https://example.com');
      expect(result).toBe('https://example.com');
      expect(validator.hasErrors()).toBe(false);

      const invalidResult = validator.url('not-a-url');
      expect(invalidResult).toBeNull();
      expect(validator.hasErrors()).toBe(true);
    });
  });
});

describe('加密功能测试', () => {
  describe('Encryption', () => {
    it('应该生成唯一密钥', () => {
      const key1 = Encryption.generateKey();
      const key2 = Encryption.generateKey();
      expect(key1).not.toBe(key2);
      expect(key1.length).toBe(64); // 32 bytes = 64 hex chars
    });

    it('应该能够加密和解密文本', async () => {
      const plaintext = 'Hello, World!';
      const key = Encryption.generateKey();

      const encrypted = await Encryption.encrypt(plaintext, key);
      expect(encrypted).not.toBe(plaintext);

      const decrypted = await Encryption.decrypt(encrypted, key);
      expect(decrypted).toBe(plaintext);
    });

    it('应该能够哈希密码', async () => {
      const password = 'mySecurePassword123';
      const hash = await Encryption.hashPassword(password);

      expect(hash).not.toBe(password);
      expect(hash.length).toBe(64); // SHA-256 hash length

      // 相同密码应该产生相同哈希
      const hash2 = await Encryption.hashPassword(password);
      expect(hash).toBe(hash2);
    });
  });
});

describe('API安全测试', () => {
  describe('策略创建验证', () => {
    it('应该验证策略创建数据', async () => {
      const validData = {
        name: 'test_strategy',
        description: '这是一个测试策略，用于验证输入验证功能',
        isActive: true
      };

      const result = await validateInput(apiSchemas.createStrategy)(validData);
      expect(result.success).toBe(true);
    });

    it('应该拒绝无效的策略数据', async () => {
      const invalidData = {
        name: 'a', // 太短
        description: 'short', // 太短
        isActive: 'not-a-boolean'
      };

      const result = await validateInput(apiSchemas.createStrategy)(invalidData);
      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('市场数据查询验证', () => {
    it('应该验证市场数据查询参数', async () => {
      const validQuery = {
        symbol: 'AAPL',
        interval: '1d',
        limit: 100
      };

      const result = await validateInput(apiSchemas.getMarketData)(validQuery);
      expect(result.success).toBe(true);
    });

    it('应该拒绝无效的股票代码', async () => {
      const invalidQuery = {
        symbol: 'invalid@symbol',
        interval: '1d'
      };

      const result = await validateInput(apiSchemas.getMarketData)(invalidQuery);
      expect(result.success).toBe(false);
    });
  });
});

describe('批量验证测试', () => {
  it('应该验证批量数据', async () => {
    const items = ['user1', 'user2', 'user3', 'invalid user!'];
    const schema = apiSchemas.register.shape.username;

    const { valid, invalid } = await validateBatch(items, schema);

    expect(valid).toHaveLength(3);
    expect(invalid).toHaveLength(1);
    expect(invalid[0].index).toBe(3);
    expect(invalid[0].errors.length).toBeGreaterThan(0);
  });
});

describe('安全场景测试', () => {
  describe('XSS防护场景', () => {
    const xssPayloads = [
      '<script>alert("xss")</script>',
      '<img src=x onerror=alert(1)>',
      'javascript:alert(1)',
      '<svg onload=alert(1)>',
      '<iframe src="javascript:alert(1)"></iframe>'
    ];

    xssPayloads.forEach((payload, index) => {
      it(`应该防护XSS攻击 payload ${index + 1}`, () => {
        const sanitized = sanitizeInput(payload);
        const escaped = escapeHtml(payload);

        expect(sanitized).not.toContain('<script>');
        expect(sanitized).not.toContain('javascript:');
        expect(escaped).not.toContain('<script>');
        expect(escaped).not.toContain('onerror');
      });
    });
  });

  describe('SQL注入防护场景', () => {
    const sqlPayloads = [
      "'; DROP TABLE users; --",
      "' OR '1'='1",
      "'; UPDATE users SET password='hacked' WHERE '1'='1'; --",
      "' UNION SELECT * FROM passwords --"
    ];

    sqlPayloads.forEach((payload, index) => {
      it(`应该防护SQL注入 payload ${index + 1}`, () => {
        const escaped = escapeSql(payload);

        expect(escaped).not.toContain("'");
        expect(escaped).not.toContain('--');
        expect(escaped).not.toContain('DROP');
        expect(escaped).not.toContain('UNION');
      });
    });
  });

  describe('文件上传安全', () => {
    const maliciousFiles = [
      '../../../etc/passwd',
      '..\\..\\windows\\system32\\config\\sam',
      'file.php?eval($_POST[cmd])',
      'shell.jsp',
      'web.config.php'
    ];

    maliciousFiles.forEach((filename, index) => {
      it(`应该检测恶意文件名 ${index + 1}`, () => {
        const sanitized = sanitizeInput(filename);

        expect(sanitized).not.toContain('../');
        expect(sanitized).not.toContain('..\\');
        expect(sanitized).not.toContain('<?');
        expect(sanitized).not.toContain('<%');
      });
    });
  });
});