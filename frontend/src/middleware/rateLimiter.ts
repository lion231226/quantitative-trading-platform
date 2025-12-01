/**
 * API Rate Limiting 中间件
 *
 * 功能:
 * 1. 基于IP的API访问频率限制
 * 2. 配置不同端点的差异化限制策略
 * 3. 用户级别的速率控制
 * 4. 速率限制的监控和告警
 */

import { NextRequest, NextResponse } from 'next/server';

// 速率限制配置接口
interface RateLimitConfig {
  windowMs: number;    // 时间窗口（毫秒）
  max: number;         // 最大请求数
  message?: string;    // 错误消息
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
}

// 速率限制记录接口
interface RateLimitRecord {
  count: number;
  resetTime: number;
  lastAccess: number;
}

// 默认配置
const DEFAULT_CONFIG: RateLimitConfig = {
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 100,                 // 每个IP最多100个请求
  message: '请求过于频繁，请稍后再试',
  skipSuccessfulRequests: false,
  skipFailedRequests: false
};

// API端点差异化配置
const API_ENDPOINT_CONFIGS: Record<string, Partial<RateLimitConfig>> = {
  '/api/strategies': {
    windowMs: 60 * 1000,  // 1分钟
    max: 10,              // 策略API限制
    message: '策略API请求频率过高，请稍后再试'
  },
  '/api/market-data': {
    windowMs: 60 * 1000,  // 1分钟
    max: 50,              // 数据API限制
    message: '市场数据API请求频率过高，请稍后再试'
  },
  '/api/backtest': {
    windowMs: 60 * 1000,  // 1分钟
    max: 5,               // 回测API限制
    message: '回测API请求频率过高，请稍后再试'
  },
  '/api/auth': {
    windowMs: 15 * 60 * 1000, // 15分钟
    max: 20,                  // 认证API限制
    message: '认证请求频率过高，请稍后再试'
  },
  '/api/upload': {
    windowMs: 60 * 1000,  // 1分钟
    max: 3,               // 上传API限制
    message: '文件上传请求频率过高，请稍后再试'
  }
};

// 内存存储（生产环境应使用Redis等外部存储）
const rateLimitStore = new Map<string, RateLimitRecord>();

// 获取客户端IP地址
const getClientIP = (request: NextRequest): string => {
  // 检查各种可能的IP头部
  const forwardedFor = request.headers.get('x-forwarded-for');
  const realIP = request.headers.get('x-real-ip');
  const cfConnectingIP = request.headers.get('cf-connecting-ip'); // Cloudflare

  if (forwardedFor) {
    return forwardedFor.split(',')[0].trim();
  }

  if (realIP) {
    return realIP;
  }

  if (cfConnectingIP) {
    return cfConnectingIP;
  }

  // 回退到请求IP（在服务器环境中可能不可用）
  return '127.0.0.1';
};

// 生成限制键
const generateKey = (ip: string, endpoint: string, userId?: string): string => {
  if (userId) {
    return `user:${userId}:${endpoint}`;
  }
  return `ip:${ip}:${endpoint}`;
};

// 清理过期记录
const cleanupExpiredRecords = (): void => {
  const now = Date.now();

  for (const [key, record] of rateLimitStore.entries()) {
    if (now > record.resetTime) {
      rateLimitStore.delete(key);
    }
  }
};

// 速率限制器类
export class RateLimiter {
  private config: RateLimitConfig;

  constructor(config: Partial<RateLimitConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 检查请求是否超过限制
   */
  isAllowed(key: string): { allowed: boolean; remaining: number; resetTime: number } {
    const now = Date.now();
    const record = rateLimitStore.get(key);

    if (!record || now > record.resetTime) {
      // 新记录或已过期
      const newRecord: RateLimitRecord = {
        count: 1,
        resetTime: now + this.config.windowMs,
        lastAccess: now
      };

      rateLimitStore.set(key, newRecord);

      return {
        allowed: true,
        remaining: this.config.max - 1,
        resetTime: newRecord.resetTime
      };
    }

    // 更新现有记录
    record.count++;
    record.lastAccess = now;

    const remaining = Math.max(0, this.config.max - record.count);
    const allowed = record.count <= this.config.max;

    return {
      allowed,
      remaining,
      resetTime: record.resetTime
    };
  }

  /**
   * 中间件处理函数
   */
  middleware(request: NextRequest): NextResponse | null {
    // 定期清理过期记录
    if (Math.random() < 0.01) { // 1%的概率执行清理
      cleanupExpiredRecords();
    }

    const pathname = request.nextUrl.pathname;
    const ip = getClientIP(request);

    // 检查是否跳过某些路径
    if (this.shouldSkipPath(pathname)) {
      return null;
    }

    // 获取端点特定配置
    const endpointConfig = API_ENDPOINT_CONFIGS[pathname] || {};
    const config = { ...this.config, ...endpointConfig };

    // 获取用户ID（如果有认证）
    const userId = this.getUserId(request);
    const key = generateKey(ip, pathname, userId);

    // 临时更新配置进行检查
    this.config = config;
    const result = this.isAllowed(key);

    if (!result.allowed) {
      return this.createRateLimitResponse(config);
    }

    // 在响应头中添加速率限制信息
    const response = NextResponse.next();
    this.addRateLimitHeaders(response, result, config);

    return response;
  }

  /**
   * 检查是否应该跳过路径
   */
  private shouldSkipPath(pathname: string): boolean {
    const skipPaths = [
      '/_next/',
      '/api/health',
      '/api/status',
      '/favicon.ico',
      '/robots.txt'
    ];

    return skipPaths.some(path => pathname.startsWith(path));
  }

  /**
   * 获取用户ID（从JWT token或session中）
   */
  private getUserId(request: NextRequest): string | undefined {
    const authHeader = request.headers.get('authorization');

    if (authHeader && authHeader.startsWith('Bearer ')) {
      try {
        // 这里应该解析JWT token获取用户ID
        // 简化实现，实际应该使用JWT库
        const token = authHeader.substring(7);
        // const decoded = jwt.verify(token, process.env.JWT_SECRET!);
        // return decoded.userId;
        return undefined; // 暂时返回undefined
      } catch (error) {
        return undefined;
      }
    }

    return undefined;
  }

  /**
   * 创建速率限制响应
   */
  private createRateLimitResponse(config: RateLimitConfig): NextResponse {
    return NextResponse.json(
      {
        error: 'Too Many Requests',
        message: config.message || '请求过于频繁，请稍后再试',
        retryAfter: Math.ceil(config.windowMs / 1000)
      },
      {
        status: 429,
        headers: {
          'Retry-After': Math.ceil(config.windowMs / 1000).toString(),
          'X-RateLimit-Limit': config.max.toString(),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': new Date(Date.now() + config.windowMs).toISOString()
        }
      }
    );
  }

  /**
   * 添加速率限制头
   */
  private addRateLimitHeaders(
    response: NextResponse,
    result: { allowed: boolean; remaining: number; resetTime: number },
    config: RateLimitConfig
  ): void {
    response.headers.set('X-RateLimit-Limit', config.max.toString());
    response.headers.set('X-RateLimit-Remaining', result.remaining.toString());
    response.headers.set('X-RateLimit-Reset', new Date(result.resetTime).toISOString());
  }

  /**
   * 获取当前速率限制状态
   */
  getStatus(key: string): { count: number; remaining: number; resetTime: number } | null {
    const record = rateLimitStore.get(key);

    if (!record || Date.now() > record.resetTime) {
      return null;
    }

    return {
      count: record.count,
      remaining: Math.max(0, this.config.max - record.count),
      resetTime: record.resetTime
    };
  }

  /**
   * 重置特定键的限制
   */
  reset(key: string): void {
    rateLimitStore.delete(key);
  }
}

// 默认速率限制器实例
export const defaultRateLimiter = new RateLimiter();

// 创建特定配置的速率限制器
export const createRateLimiter = (config: Partial<RateLimitConfig>): RateLimiter => {
  return new RateLimiter(config);
};

// 导出配置常量
export { DEFAULT_CONFIG, API_ENDPOINT_CONFIGS };