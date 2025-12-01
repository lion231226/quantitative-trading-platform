/**
 * 安全头配置中间件
 *
 * 功能:
 * 1. 实现严格的CSP头部配置
 * 2. 配置脚本和样式白名单
 * 3. 实现inline script的nonce保护
 * 4. 建立CSP违规报告和监控
 */

import { NextRequest, NextResponse } from 'next/server';

// CSP配置接口
interface CSPConfig {
  'default-src'?: string[];
  'script-src'?: string[];
  'style-src'?: string[];
  'img-src'?: string[];
  'font-src'?: string[];
  'connect-src'?: string[];
  'frame-src'?: string[];
  'frame-ancestors'?: string[];
  'base-uri'?: string[];
  'form-action'?: string[];
  'object-src'?: string[];
  'media-src'?: string[];
  'manifest-src'?: string[];
  'worker-src'?: string[];
}

// 默认安全头配置
const SECURITY_HEADERS = {
  'X-DNS-Prefetch-Control': 'on',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin'
};

// 默认CSP配置
const DEFAULT_CSP: CSPConfig = {
  'default-src': ["'self'"],
  'script-src': ["'self'", "'unsafe-eval'", "'unsafe-inline'", 'https://vercel.live'],
  'style-src': ["'self'", "'unsafe-inline'", 'fonts.googleapis.com'],
  'img-src': ["'self'", 'data:', 'https:', 'blob:'],
  'font-src': ["'self'", 'fonts.gstatic.com'],
  'connect-src': ["'self'", 'https://api.coindesk.com', 'https://akshare.akfamily.xyz'],
  'frame-src': ["'none'"],
  'frame-ancestors': ["'none'"],
  'base-uri': ["'self'"],
  'form-action': ["'self'"],
  'object-src': ["'none'"],
  'media-src': ["'self'"],
  'manifest-src': ["'self'"],
  'worker-src': ["'self'"]
};

// 生成CSP头部
const generateCSP = (config: CSPConfig, nonce?: string): string => {
  const directives: string[] = [];

  for (const [directive, sources] of Object.entries(config)) {
    if (sources && sources.length > 0) {
      let directiveValue = sources.join(' ');

      // 为script-src添加nonce
      if (directive === 'script-src' && nonce) {
        directiveValue += ` 'nonce-${nonce}'`;
      }

      directives.push(`${directive} ${directiveValue}`);
    }
  }

  // 添加报告URI（如果配置了）
  if (process.env.CSP_REPORT_URI) {
    directives.push(`report-uri ${process.env.CSP_REPORT_URI}`);
    directives.push(`report-to csp-endpoint`);
  }

  return directives.join('; ');
};

// 生成随机nonce
const generateNonce = (): string => {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

// 安全头中间件
export class SecurityHeadersMiddleware {
  private config: CSPConfig;
  private customHeaders: Record<string, string>;

  constructor(config: Partial<CSPConfig> = {}, customHeaders: Record<string, string> = {}) {
    this.config = { ...DEFAULT_CSP, ...config };
    this.customHeaders = { ...SECURITY_HEADERS, ...customHeaders };
  }

  /**
   * 中间件处理函数
   */
  middleware(request: NextRequest): NextResponse {
    const response = NextResponse.next();
    const nonce = generateNonce();

    // 设置CSP头
    const cspValue = generateCSP(this.config, nonce);
    response.headers.set('Content-Security-Policy', cspValue);

    // 设置其他安全头
    for (const [header, value] of Object.entries(this.customHeaders)) {
      response.headers.set(header, value);
    }

    // 设置CSP报告端点
    if (process.env.CSP_REPORT_URI) {
      response.headers.set('Report-To', JSON.stringify({
        group: 'csp-endpoint',
        max_age: 10886400,
        endpoints: [{ url: process.env.CSP_REPORT_URI }]
      }));
    }

    // 在响应中添加nonce供客户端使用
    response.headers.set('X-Nonce', nonce);

    return response;
  }

  /**
   * 更新CSP配置
   */
  updateCSPConfig(newConfig: Partial<CSPConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * 更新自定义头
   */
  updateCustomHeaders(newHeaders: Record<string, string>): void {
    this.customHeaders = { ...this.customHeaders, ...newHeaders };
  }
}

// 默认实例
export const defaultSecurityHeaders = new SecurityHeadersMiddleware();

// CSP违规报告处理
export const handleCSPViolation = async (violationReport: any): Promise<void> => {
  console.warn('CSP Violation:', violationReport);

  // 在生产环境中发送到监控服务
  if (process.env.NODE_ENV === 'production' && process.env.CSP_WEBHOOK_URL) {
    try {
      await fetch(process.env.CSP_WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          type: 'csp_violation',
          timestamp: new Date().toISOString(),
          report: violationReport
        })
      });
    } catch (error) {
      console.error('Failed to send CSP violation report:', error);
    }
  }
};

export default SecurityHeadersMiddleware;