/**
 * Web Vitals Dashboard Component
 *
 * Displays real-time Core Web Vitals metrics and performance insights
 */

import React, { useState, useEffect } from 'react';
import { webVitalsService, WebVitalsMetrics, PerformanceScore } from '@/services/webVitalsService';

interface WebVitalsDashboardProps {
  className?: string;
  showDetails?: boolean;
  refreshInterval?: number;
}

export const WebVitalsDashboard: React.FC<WebVitalsDashboardProps> = ({
  className = '',
  showDetails = false,
  refreshInterval = 30000, // 30 seconds
}) => {
  const [metrics, setMetrics] = useState<WebVitalsMetrics | null>(null);
  const [score, setScore] = useState<PerformanceScore | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    const collectMetrics = async () => {
      try {
        setIsLoading(true);
        const webVitalsMetrics = await webVitalsService.trackWebVitals();
        setMetrics(webVitalsMetrics);
        setScore(webVitalsService.getPerformanceScore(webVitalsMetrics));
        setLastUpdated(new Date());
      } catch (error) {
        console.error('Failed to collect Web Vitals:', error);
      } finally {
        setIsLoading(false);
      }
    };

    // Initial collection
    collectMetrics();

    // Set up periodic refresh
    if (refreshInterval > 0) {
      const interval = setInterval(collectMetrics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [refreshInterval]);

  const getScoreColor = (score: 'good' | 'needs-improvement' | 'poor'): string => {
    switch (score) {
      case 'good':
        return 'text-green-600 bg-green-100';
      case 'needs-improvement':
        return 'text-yellow-600 bg-yellow-100';
      case 'poor':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getScoreIcon = (score: 'good' | 'needs-improvement' | 'poor'): string => {
    switch (score) {
      case 'good':
        return '✅';
      case 'needs-improvement':
        return '⚠️';
      case 'poor':
        return '❌';
      default:
        return '❓';
    }
  };

  const formatValue = (value: number, metric: string): string => {
    switch (metric) {
      case 'cls':
        return value.toFixed(3);
      case 'lcp':
      case 'fid':
      case 'fcp':
      case 'ttfb':
        return `${Math.round(value)}ms`;
      default:
        return value.toString();
    }
  };

  if (isLoading && !metrics) {
    return (
      <div className={`p-4 bg-white rounded-lg shadow ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-3 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-4 bg-white rounded-lg shadow ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">性能指标监控</h3>
        <div className="flex items-center space-x-2">
          {lastUpdated && (
            <span className="text-xs text-gray-500">
              更新时间: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          {isLoading && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          )}
        </div>
      </div>

      {metrics && score && (
        <div className="space-y-4">
          {/* Overall Score */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">总体评分</span>
              {getScoreIcon(score.overall)}
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(score.overall)}`}>
              {score.overall === 'good' ? '良好' : score.overall === 'needs-improvement' ? '需改进' : '较差'}
            </span>
          </div>

          {/* Individual Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* LCP - Largest Contentful Paint */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">LCP</div>
                <div className="text-xs text-gray-500">最大内容绘制</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono">{formatValue(metrics.lcp, 'lcp')}</div>
                <span className={`text-xs px-1 py-0.5 rounded ${getScoreColor(score.lcp)}`}>
                  {getScoreIcon(score.lcp)}
                </span>
              </div>
            </div>

            {/* FID - First Input Delay */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">FID</div>
                <div className="text-xs text-gray-500">首次输入延迟</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono">{formatValue(metrics.fid, 'fid')}</div>
                <span className={`text-xs px-1 py-0.5 rounded ${getScoreColor(score.fid)}`}>
                  {getScoreIcon(score.fid)}
                </span>
              </div>
            </div>

            {/* CLS - Cumulative Layout Shift */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">CLS</div>
                <div className="text-xs text-gray-500">累积布局偏移</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono">{formatValue(metrics.cls, 'cls')}</div>
                <span className={`text-xs px-1 py-0.5 rounded ${getScoreColor(score.cls)}`}>
                  {getScoreIcon(score.cls)}
                </span>
              </div>
            </div>

            {/* FCP - First Contentful Paint */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">FCP</div>
                <div className="text-xs text-gray-500">首次内容绘制</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono">{formatValue(metrics.fcp, 'fcp')}</div>
                <span className={`text-xs px-1 py-0.5 rounded ${getScoreColor(score.fcp)}`}>
                  {getScoreIcon(score.fcp)}
                </span>
              </div>
            </div>

            {/* TTFB - Time to First Byte */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="text-sm font-medium text-gray-900">TTFB</div>
                <div className="text-xs text-gray-500">首字节时间</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono">{formatValue(metrics.ttfb, 'ttfb')}</div>
                <span className={`text-xs px-1 py-0.5 rounded ${getScoreColor(score.ttfb)}`}>
                  {getScoreIcon(score.ttfb)}
                </span>
              </div>
            </div>
          </div>

          {/* Performance Insights */}
          {showDetails && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <h4 className="text-sm font-medium text-blue-900 mb-2">性能建议</h4>
              <div className="space-y-1 text-xs text-blue-800">
                {score.lcp === 'poor' && (
                  <div>• LCP过慢：优化图片加载，使用CDN，减少服务器响应时间</div>
                )}
                {score.fid === 'poor' && (
                  <div>• FID过高：减少JavaScript执行时间，分割代码，优化第三方脚本</div>
                )}
                {score.cls === 'poor' && (
                  <div>• CLS过高：为图片设置明确尺寸，避免动态内容插入，优化字体加载</div>
                )}
                {score.fcp === 'poor' && (
                  <div>• FCP过慢：优化关键渲染路径，内联关键CSS，减少阻塞性资源</div>
                )}
                {score.ttfb === 'poor' && (
                  <div>• TTFB过慢：优化服务器配置，使用缓存，减少网络延迟</div>
                )}
                {score.overall === 'good' && (
                  <div>🎉 性能表现良好！继续保持当前优化策略。</div>
                )}
              </div>
            </div>
          )}

          {/* Threshold Reference */}
          {showDetails && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-900 mb-2">性能阈值参考</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-gray-600">
                <div>LCP: 良好(&lt;2.5s) | 需改进(&lt;4s) | 较差(&gt;4s)</div>
                <div>FID: 良好(&lt;100ms) | 需改进(&lt;300ms) | 较差(&gt;300ms)</div>
                <div>CLS: 良好(&lt;0.1) | 需改进(&lt;0.25) | 较差(&gt;0.25)</div>
                <div>FCP: 良好(&lt;1.8s) | 需改进(&lt;3s) | 较差(&gt;3s)</div>
                <div>TTFB: 良好(&lt;800ms) | 需改进(&lt;1.8s) | 较差(&gt;1.8s)</div>
              </div>
            </div>
          )}
        </div>
      )}

      {!metrics && !isLoading && (
        <div className="text-center py-8 text-gray-500">
          <p>暂无性能数据</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            刷新页面
          </button>
        </div>
      )}
    </div>
  );
};

export default WebVitalsDashboard;