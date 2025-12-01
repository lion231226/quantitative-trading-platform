import { ColorblindConfig, ColorblindMode } from '../types/theme.types';

/**
 * 色盲辅助工具函数
 */

// 色盲模式对应的涨跌图案
export const COLORBLIND_PATTERNS = {
  protanopia: {
    // 红色盲：使用三角形
    bullish: { shape: 'triangle', symbol: '▲', rotation: 0 },
    bearish: { shape: 'triangle', symbol: '▼', rotation: 180 },
  },
  deuteranopia: {
    // 绿色盲：使用圆形和菱形
    bullish: { shape: 'circle', symbol: '●', rotation: 0 },
    bearish: { shape: 'diamond', symbol: '◆', rotation: 45 },
  },
  tritanopia: {
    // 蓝色盲：使用方形和六边形
    bullish: { shape: 'square', symbol: '■', rotation: 0 },
    bearish: { shape: 'hexagon', symbol: '⬢', rotation: 0 },
  },
  achromatopsia: {
    // 全色盲：使用线条和纹理
    bullish: { shape: 'line', symbol: '━', rotation: 0 },
    bearish: { shape: 'line', symbol: '┃', rotation: 90 },
  },
} as const;

// 图案类型定义
export type PatternShape =
  | 'triangle'
  | 'circle'
  | 'diamond'
  | 'square'
  | 'hexagon'
  | 'line';

// 信号图案接口
export interface SignalPattern {
  shape: PatternShape;
  symbol: string;
  rotation: number;
}

/**
 * 获取色盲模式下的信号图案
 */
export function getSignalPattern(
  signalType: 'bullish' | 'bearish',
  colorblindMode: ColorblindMode,
  usePatterns: boolean = true,
): SignalPattern | null {
  if (!usePatterns || colorblindMode === 'none') {
    return null;
  }

  const patterns = COLORBLIND_PATTERNS[colorblindMode];
  return patterns?.[signalType] || null;
}

/**
 * 生成色盲友好的Canvas纹理
 */
export function createColorblindTexture(
  canvas: HTMLCanvasElement,
  pattern: SignalPattern,
  color: string,
  intensity: number = 0.7,
): CanvasPattern | null {
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // 设置画布尺寸
  canvas.width = 20;
  canvas.height = 20;

  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 设置基础颜色
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 根据图案类型绘制纹理
  ctx.save();
  ctx.translate(10, 10); // 移动到画布中心
  ctx.rotate((pattern.rotation * Math.PI) / 180);

  switch (pattern.shape) {
    case 'triangle':
      drawTriangleTexture(ctx, intensity);
      break;
    case 'circle':
      drawCircleTexture(ctx, intensity);
      break;
    case 'diamond':
      drawDiamondTexture(ctx, intensity);
      break;
    case 'square':
      drawSquareTexture(ctx, intensity);
      break;
    case 'hexagon':
      drawHexagonTexture(ctx, intensity);
      break;
    case 'line':
      drawLineTexture(
        ctx,
        pattern.symbol === '━' ? 'horizontal' : 'vertical',
        intensity,
      );
      break;
  }

  ctx.restore();

  // 创建图案
  return ctx.createPattern(canvas, 'repeat');
}

/**
 * 绘制三角形纹理
 */
function drawTriangleTexture(
  ctx: CanvasRenderingContext2D,
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  for (let i = -15; i <= 15; i += 10) {
    for (let j = -15; j <= 15; j += 10) {
      ctx.beginPath();
      ctx.moveTo(i, j - 3);
      ctx.lineTo(i - 3, j + 3);
      ctx.lineTo(i + 3, j + 3);
      ctx.closePath();
      ctx.stroke();
    }
  }
}

/**
 * 绘制圆形纹理
 */
function drawCircleTexture(
  ctx: CanvasRenderingContext2D,
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  for (let i = -15; i <= 15; i += 10) {
    for (let j = -15; j <= 15; j += 10) {
      ctx.beginPath();
      ctx.arc(i, j, 2, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

/**
 * 绘制菱形纹理
 */
function drawDiamondTexture(
  ctx: CanvasRenderingContext2D,
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  for (let i = -15; i <= 15; i += 10) {
    for (let j = -15; j <= 15; j += 10) {
      ctx.beginPath();
      ctx.moveTo(i, j - 3);
      ctx.lineTo(i - 3, j);
      ctx.lineTo(i, j + 3);
      ctx.lineTo(i + 3, j);
      ctx.closePath();
      ctx.stroke();
    }
  }
}

/**
 * 绘制方形纹理
 */
function drawSquareTexture(
  ctx: CanvasRenderingContext2D,
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  for (let i = -15; i <= 15; i += 10) {
    for (let j = -15; j <= 15; j += 10) {
      ctx.strokeRect(i - 2, j - 2, 4, 4);
    }
  }
}

/**
 * 绘制六边形纹理
 */
function drawHexagonTexture(
  ctx: CanvasRenderingContext2D,
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  for (let i = -15; i <= 15; i += 15) {
    for (let j = -15; j <= 15; j += 15) {
      drawHexagon(ctx, i, j, 3);
    }
  }
}

/**
 * 绘制六边形
 */
function drawHexagon(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
): void {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i;
    const px = x + size * Math.cos(angle);
    const py = y + size * Math.sin(angle);
    if (i === 0) {
      ctx.moveTo(px, py);
    } else {
      ctx.lineTo(px, py);
    }
  }
  ctx.closePath();
  ctx.stroke();
}

/**
 * 绘制线条纹理
 */
function drawLineTexture(
  ctx: CanvasRenderingContext2D,
  direction: 'horizontal' | 'vertical',
  intensity: number,
): void {
  ctx.strokeStyle = `rgba(0, 0, 0, ${intensity})`;
  ctx.lineWidth = 1;

  if (direction === 'horizontal') {
    for (let i = -15; i <= 15; i += 5) {
      ctx.beginPath();
      ctx.moveTo(-15, i);
      ctx.lineTo(15, i);
      ctx.stroke();
    }
  } else {
    for (let i = -15; i <= 15; i += 5) {
      ctx.beginPath();
      ctx.moveTo(i, -15);
      ctx.lineTo(i, 15);
      ctx.stroke();
    }
  }
}

/**
 * 获取色盲模式的对比色
 */
export function getColorblindContrastColor(
  color: string,
  colorblindMode: ColorblindMode,
  isBullish: boolean,
): string {
  // 根据色盲模式调整颜色以提高对比度
  const baseColors = {
    protanopia: {
      bullish: '#10b981', // 绿色替代红色
      bearish: '#3b82f6', // 蓝色保持
    },
    deuteranopia: {
      bullish: '#3b82f6', // 蓝色替代绿色
      bearish: '#8b5cf6', // 紫色替代红色
    },
    tritanopia: {
      bullish: '#ef4444', // 红色保持
      bearish: '#22c55e', // 绿色保持
    },
    achromatopsia: {
      bullish: '#000000', // 黑色
      bearish: '#ffffff', // 白色
    },
  };

  if (colorblindMode === 'none') {
    return color;
  }

  const modeColors = baseColors[colorblindMode];
  return modeColors?.[isBullish ? 'bullish' : 'bearish'] || color;
}

/**
 * 验证色盲辅助配置
 */
export function validateColorblindConfig(config: ColorblindConfig): {
  isValid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  // 验证纹理强度范围
  if (config.textureIntensity < 0 || config.textureIntensity > 1) {
    errors.push('纹理强度必须在0到1之间');
  }

  // 验证模式
  const validModes: ColorblindMode[] = [
    'none',
    'protanopia',
    'deuteranopia',
    'tritanopia',
    'achromatopsia',
  ];
  if (!validModes.includes(config.mode)) {
    errors.push(`无效的色盲模式: ${config.mode}`);
  }

  // 警告
  if (config.enabled && config.mode === 'none') {
    warnings.push('已启用色盲辅助但模式为无，请选择具体的色盲类型');
  }

  if (config.usePatterns && config.textureIntensity < 0.3) {
    warnings.push('纹理强度过低可能影响识别效果');
  }

  if (!config.usePatterns && !config.useShapes && config.enabled) {
    warnings.push('未启用任何辅助方式（图案或形状），建议至少启用一种');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * 生成色盲友好的CSS类名
 */
export function getColorblindCSSClass(
  signalType: 'bullish' | 'bearish',
  config: ColorblindConfig,
): string {
  if (!config.enabled || config.mode === 'none') {
    return signalType;
  }

  const baseClass = signalType;
  const modeClass = `colorblind-${config.mode}`;
  const patternClass = config.usePatterns ? 'with-pattern' : '';
  const shapeClass = config.useShapes ? 'with-shape' : '';

  return [baseClass, modeClass, patternClass, shapeClass]
    .filter(Boolean)
    .join(' ');
}
