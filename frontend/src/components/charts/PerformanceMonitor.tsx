import React, { useCallback, useEffect, useRef, useState } from 'react';
import { PerformanceMonitorProps } from '../../types/kline.types';

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  dataPoints,
  renderTime,
  fps,
  memoryUsage,
  className = '',
  showDetails = false,
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [alerts, setAlerts] = useState<string[]>([]);
  const previousMetrics = useRef({ fps: 60, memory: 0 });

  // 性能阈值配置
  const THRESHOLDS = {
    fps: {
      excellent: 60,
      good: 30,
      warning: 15,
      critical: 10,
    },
    renderTime: {
      excellent: 16, // ~60fps
      good: 33, // ~30fps
      warning: 66, // ~15fps
      critical: 100, // ~10fps
    },
    memoryUsage: {
      good: 50 * 1024 * 1024, // 50MB
      warning: 100 * 1024 * 1024, // 100MB
      critical: 200 * 1024 * 1024, // 200MB
    },
  };

  // 性能评估函数
  const getPerformanceLevel = (
    metric: number,
    thresholds: typeof THRESHOLDS.fps,
  ): {
    level: 'excellent' | 'good' | 'warning' | 'critical';
    color: string;
    icon: string;
  } => {
    if (metric >= thresholds.excellent) {
      return { level: 'excellent', color: 'text-green-600', icon: '🟢' };
    } else if (metric >= thresholds.warning) {
      return { level: 'good', color: 'text-blue-600', icon: '🔵' };
    } else if (metric >= thresholds.critical) {
      return { level: 'warning', color: 'text-yellow-600', icon: '🟡' };
    } else {
      return { level: 'critical', color: 'text-red-600', icon: '🔴' };
    }
  };

  // 格式化内存大小
  const formatMemorySize = (bytes: number): string => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)}GB`;
    } else if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    } else if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(0)}KB`;
    } else {
      return `${bytes}B`;
    }
  };

  // 性能警报检查
  useEffect(() => {
    const newAlerts: string[] = [];

    // FPS检查
    if (fps < THRESHOLDS.fps.critical) {
      newAlerts.push(
        `严重性能问题: FPS ${fps.toFixed(1)} 低于 ${THRESHOLDS.fps.critical}`,
      );
    } else if (fps < THRESHOLDS.fps.warning) {
      newAlerts.push(
        `性能警告: FPS ${fps.toFixed(1)} 低于建议值 ${THRESHOLDS.fps.warning}`,
      );
    }

    // 渲染时间检查
    if (renderTime > THRESHOLDS.renderTime.critical) {
      newAlerts.push(`渲染时间过长: ${renderTime.toFixed(1)}ms 超过临界值`);
    }

    // 内存使用检查
    if (memoryUsage > THRESHOLDS.memoryUsage.critical) {
      newAlerts.push(`内存使用过高: ${formatMemorySize(memoryUsage)}`);
    }

    // 数据量检查
    if (dataPoints > 50000) {
      newAlerts.push(
        `数据量过大: ${dataPoints.toLocaleString()} 数据点可能影响性能`,
      );
    }

    // FPS下降检测
    const fpsDrop = previousMetrics.current.fps - fps;
    if (fpsDrop > 20) {
      newAlerts.push(
        `FPS显著下降: 从 ${previousMetrics.current.fps.toFixed(1)} 降至 ${fps.toFixed(1)}`,
      );
    }

    setAlerts(newAlerts);
    previousMetrics.current = { fps, memory: memoryUsage };
  }, [dataPoints, renderTime, fps, memoryUsage]);

  // 获取FPS状态
  const fpsStatus = getPerformanceLevel(fps, THRESHOLDS.fps);
  const renderTimeStatus = getPerformanceLevel(
    1000 / renderTime,
    THRESHOLDS.fps,
  ); // 转换为等效FPS
  const memoryStatus = getPerformanceLevel(
    THRESHOLDS.memoryUsage.good / (memoryUsage || 1), // 反向计算，内存越少越好
    { ...THRESHOLDS.fps, excellent: 2, good: 1.5, warning: 1.2, critical: 1 },
  );

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 right-4 bg-blue-500 text-white p-2 rounded-full shadow-lg hover:bg-blue-600 transition-colors"
        title="显示性能监控"
      >
        📊
      </button>
    );
  }

  return (
    <div className={`performance-monitor ${className}`}>
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm">
        {/* 头部 */}
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center">
            <span className="mr-2">📊</span>
            性能监控
          </h3>
          <button
            onClick={() => setIsVisible(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="隐藏监控面板"
          >
            ✕
          </button>
        </div>

        {/* 核心指标 */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {/* FPS */}
          <div className="text-center p-2 bg-gray-50 rounded">
            <div className={`text-2xl font-bold ${fpsStatus.color}`}>
              {fps.toFixed(1)}
            </div>
            <div className="text-xs text-gray-600">FPS</div>
            <div className="text-xs">{fpsStatus.icon}</div>
          </div>

          {/* 渲染时间 */}
          <div className="text-center p-2 bg-gray-50 rounded">
            <div className={`text-2xl font-bold ${renderTimeStatus.color}`}>
              {renderTime < 1
                ? `${(renderTime * 1000).toFixed(0)}ms`
                : `${renderTime.toFixed(1)}s`}
            </div>
            <div className="text-xs text-gray-600">渲染时间</div>
            <div className="text-xs">{renderTimeStatus.icon}</div>
          </div>

          {/* 数据点 */}
          <div className="text-center p-2 bg-gray-50 rounded">
            <div className="text-lg font-bold text-gray-700">
              {dataPoints > 1000
                ? `${(dataPoints / 1000).toFixed(1)}K`
                : dataPoints}
            </div>
            <div className="text-xs text-gray-600">数据点</div>
            <div className="text-xs">📈</div>
          </div>
        </div>

        {/* 详细信息 */}
        {showDetails && (
          <div className="space-y-3 mb-4">
            {/* 内存使用 */}
            <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
              <span className="text-sm text-gray-600">内存使用</span>
              <div className="flex items-center">
                <span className={`text-sm font-medium ${memoryStatus.color}`}>
                  {formatMemorySize(memoryUsage)}
                </span>
                <span className="ml-1 text-xs">{memoryStatus.icon}</span>
              </div>
            </div>

            {/* 性能评分 */}
            <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
              <span className="text-sm text-gray-600">性能评分</span>
              <span className={`text-sm font-medium ${fpsStatus.color}`}>
                {fpsStatus.level === 'excellent'
                  ? '优秀'
                  : fpsStatus.level === 'good'
                    ? '良好'
                    : fpsStatus.level === 'warning'
                      ? '一般'
                      : '需优化'}
              </span>
            </div>

            {/* 建议操作 */}
            <div className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
              {fps < 30 && renderTime > 33 && (
                <div>💡 建议减少数据点数量或启用数据采样</div>
              )}
              {memoryUsage > THRESHOLDS.memoryUsage.warning && (
                <div>💡 建议清理内存或优化数据处理逻辑</div>
              )}
              {dataPoints > 10000 && (
                <div>💡 大数据量场景，建议启用智能采样</div>
              )}
              {fps >= 60 && renderTime <= 16 && (
                <div>✅ 性能表现良好，一切正常</div>
              )}
            </div>
          </div>
        )}

        {/* 警报 */}
        {alerts.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-red-800 mb-1">
              ⚠️ 性能警报
            </div>
            {alerts.map((alert, index) => (
              <div
                key={index}
                className="text-xs bg-red-50 border border-red-200 text-red-700 p-2 rounded"
              >
                {alert}
              </div>
            ))}
          </div>
        )}

        {/* 切换详情按钮 */}
        <div className="mt-4 text-center">
          <button
            onClick={() => setIsVisible(false)}
            className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
          >
            收起监控面板
          </button>
        </div>
      </div>
    </div>
  );
};

export default PerformanceMonitor;
