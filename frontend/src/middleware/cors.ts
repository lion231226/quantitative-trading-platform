/**
 * CORS 策略中间件
 *
 * 功能:
 * 1. 配置严格的CORS白名单策略
 * 2. 实现预检请求的安全处理
 * 3. 配置安全的方法和头部白名单
 * 4. 支持动态CORS策略更新
 */

import { NextRequest, NextResponse } from 'next/server';

// CORS配置接口
interface CorsConfig {
  origins: string[];          // 允许的源
  methods: string[];          // 允许的HTTP方法
  allowedHeaders: string[];   // 允许的请求头
  exposedHeaders: string[];   // 暴露的响应头
  credentials: boolean;       // 是否允许凭证
  maxAge: number;            // 预检请求缓存时间
  optionsSuccessStatus: number; // OPTIONS响应状态码
}

// 默认CORS配置
const DEFAULT_CORS_CONFIG: CorsConfig = {
  origins: [
    'http://localhost:3000',
    'http://localhost:3001',
    'https://yourdomain.com',
    'https://www.yourdomain.com'
  ],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'Accept',
    'Origin',
    'Cache-Control',
    'X-API-Key'
  ],
  exposedHeaders: [
    'X-Total-Count',
    'X-Page-Count',
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset'
  ],
  credentials: true,
  maxAge: 86400, // 24小时
  optionsSuccessStatus: 204
};

// 动态CORS配置（可从环境变量或数据库加载）
let dynamicCorsConfig: Partial<CorsConfig> = {};

// 环境特定的CORS配置
const getEnvironmentConfig = (): Partial<CorsConfig> => {
  const env = process.env.NODE_ENV;

  switch (env) {
    case 'development':
      return {
        origins: [
          'http://localhost:3000',
          'http://localhost:3001',
          'http://127.0.0.1:3000',
          'http://127.0.0.1:3001'
        ],
        credentials: true
      };

    case 'production':
      return {
        origins: [
          process.env.FRONTEND_URL || 'https://yourdomain.com',
          ...(process.env.ADDITIONAL_ORIGINS?.split(',') || [])
        ],
        credentials: true
      };

    case 'test':
      return {
        origins: ['*'], // 测试环境允许所有源
        credentials: false
      };

    default:
      return {};
  }
};

// 合并配置
const getCorsConfig = (): CorsConfig => {
  const envConfig = getEnvironmentConfig();
  return {
    ...DEFAULT_CORS_CONFIG,
    ...envConfig,
    ...dynamicCorsConfig
  };
};

// 检查源是否被允许
const isOriginAllowed = (origin: string, allowedOrigins: string[]): boolean => {
  if (allowedOrigins.includes('*')) {
    return true;
  }

  return allowedOrigins.some(allowedOrigin => {
    // 支持通配符匹配
    if (allowedOrigin.includes('*')) {
      const pattern = allowedOrigin.replace(/\*/g, '.*');
      const regex = new RegExp(`^${pattern}$`);
      return regex.test(origin);
    }

    return allowedOrigin === origin;
  });
};

// CORS中间件类
export class CorsMiddleware {
  private config: CorsConfig;

  constructor(config: Partial<CorsConfig> = {}) {
    this.config = { ...DEFAULT_CORS_CONFIG, ...config };
  }

  /**
   * 更新CORS配置
   */
  updateConfig(newConfig: Partial<CorsConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * 获取当前配置
   */
  getConfig(): CorsConfig {
    return { ...this.config };
  }

  /**
   * 处理预检请求（OPTIONS）
   */
  private handleOptions(request: NextRequest, origin: string): NextResponse {
    const response = new NextResponse(null, {
      status: this.config.optionsSuccessStatus
    });

    this.setCorsHeaders(response, origin);
    response.headers.set('Content-Length', '0');

    return response;
  }

  /**
   * 设置CORS头
   */
  private setCorsHeaders(response: NextResponse, origin: string): void {
    const config = this.config;

    // 设置Vary头以支持缓存
    response.headers.set('Vary', 'Origin');

    // 如果源被允许，设置Access-Control-Allow-Origin
    if (isOriginAllowed(origin, config.origins)) {
      if (config.origins.includes('*')) {
        response.headers.set('Access-Control-Allow-Origin', '*');
      } else {
        response.headers.set('Access-Control-Allow-Origin', origin);
      }

      // 凭证头
      if (config.credentials) {
        response.headers.set('Access-Control-Allow-Credentials', 'true');
      }

      // 暴露头
      if (config.exposedHeaders.length > 0) {
        response.headers.set(
          'Access-Control-Expose-Headers',
          config.exposedHeaders.join(', ')
        );
      }
    }

    // 其他CORS头（无论源是否被允许都设置）
    response.headers.set(
      'Access-Control-Allow-Methods',
      config.methods.join(', ')
    );

    response.headers.set(
      'Access-Control-Allow-Headers',
      config.allowedHeaders.join(', ')
    );

    response.headers.set(
      'Access-Control-Max-Age',
      config.maxAge.toString()
    );
  }

  /**
   * 验证请求方法
   */
  private isMethodAllowed(method: string): boolean {
    return this.config.methods.includes(method.toUpperCase());
  }

  /**
   * 验证请求头
   */
  private areHeadersAllowed(requestHeaders: string[]): boolean {
    if (this.config.allowedHeaders.includes('*')) {
      return true;
    }

    return requestHeaders.every(header =>
      this.config.allowedHeaders.some(allowedHeader =>
        allowedHeader.toLowerCase() === header.toLowerCase()
      )
    );
  }

  /**
   * 记录CORS违规
   */
  private logCorsViolation(
    type: 'origin' | 'method' | 'headers',
    details: string,
    request: NextRequest
  ): void {
    const violation = {
      timestamp: new Date().toISOString(),
      type,
      details,
      origin: request.headers.get('origin'),
      method: request.method,
      url: request.url,
      userAgent: request.headers.get('user-agent'),
      ip: request.headers.get('x-forwarded-for') ||
          request.headers.get('x-real-ip') ||
          '127.0.0.1'
    };

    console.warn('CORS Violation:', violation);

    // 在生产环境中，可以发送到监控服务
    if (process.env.NODE_ENV === 'production') {
      // sendToMonitoringService(violation);
    }
  }

  /**
   * 主中间件处理函数
   */
  middleware(request: NextRequest): NextResponse {
    const origin = request.headers.get('origin') || '';
    const method = request.method;
    const config = this.config;

    // 更新配置（支持动态更新）
    this.config = { ...config, ...getEnvironmentConfig(), ...dynamicCorsConfig };

    // 如果没有Origin头，说明不是跨域请求，直接通过
    if (!origin) {
      return NextResponse.next();
    }

    // 处理预检请求
    if (method === 'OPTIONS') {
      const requestHeaders = request.headers.get('access-control-request-headers');
      const requestMethod = request.headers.get('access-control-request-method');

      // 检查方法是否被允许
      if (requestMethod && !this.isMethodAllowed(requestMethod)) {
        this.logCorsViolation('method', `Method ${requestMethod} not allowed`, request);
        return new NextResponse('Method not allowed', { status: 405 });
      }

      // 检查头是否被允许
      if (requestHeaders) {
        const headers = requestHeaders.split(',').map(h => h.trim());
        if (!this.areHeadersAllowed(headers)) {
          this.logCorsViolation('headers', `Headers not allowed: ${headers.join(', ')}`, request);
          return new NextResponse('Headers not allowed', { status: 400 });
        }
      }

      return this.handleOptions(request, origin);
    }

    // 检查源是否被允许
    if (!isOriginAllowed(origin, config.origins)) {
      this.logCorsViolation('origin', `Origin ${origin} not allowed`, request);
      return new NextResponse('Origin not allowed', { status: 403 });
    }

    // 对于实际请求，添加CORS头并继续
    const response = NextResponse.next();
    this.setCorsHeaders(response, origin);

    return response;
  }
}

// 默认CORS中间件实例
export const defaultCorsMiddleware = new CorsMiddleware();

// 创建自定义CORS中间件
export const createCorsMiddleware = (config: Partial<CorsConfig>): CorsMiddleware => {
  return new CorsMiddleware(config);
};

// 动态更新CORS配置的函数
export const updateCorsConfig = (newConfig: Partial<CorsConfig>): void => {
  dynamicCorsConfig = { ...dynamicCorsConfig, ...newConfig };
  defaultCorsMiddleware.updateConfig(newConfig);
};

// 获取当前CORS配置
export const getCurrentCorsConfig = (): CorsConfig => {
  return defaultCorsMiddleware.getConfig();
};

// 验证CORS配置的函数
export const validateCorsConfig = (config: Partial<CorsConfig>): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (config.origins) {
    if (!Array.isArray(config.origins)) {
      errors.push('origins must be an array');
    } else {
      config.origins.forEach(origin => {
        if (typeof origin !== 'string') {
          errors.push(`Invalid origin: ${origin}`);
        } else if (!origin.startsWith('http://') && !origin.startsWith('https://') && origin !== '*') {
          errors.push(`Origin must start with http:// or https://: ${origin}`);
        }
      });
    }
  }

  if (config.methods) {
    if (!Array.isArray(config.methods)) {
      errors.push('methods must be an array');
    } else {
      const validMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'];
      config.methods.forEach(method => {
        if (!validMethods.includes(method.toUpperCase())) {
          errors.push(`Invalid HTTP method: ${method}`);
        }
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};

export default CorsMiddleware;