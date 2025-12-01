/**
 * 颜色对比度工具
 * 提供WCAG 2.1 AA级别的颜色对比度分析和修复功能
 */

/**
 * 颜色格式转换接口
 */
export interface RGBColor {
  r: number;
  g: number;
  b: number;
}

export interface HSLColor {
  h: number;
  s: number;
  l: number;
}

export interface ContrastResult {
  /** 对比度比值 */
  ratio: number;
  /** 是否通过AA级别 */
  passesAA: boolean;
  /** 是否通过AAA级别 */
  passesAAA: boolean;
  /** WCAG级别 */
  level: 'AA' | 'AAA' | 'FAIL';
  /** 建议的前景色 */
  suggestedForeground?: string;
  /** 建议的背景色 */
  suggestedBackground?: string;
}

/**
 * 将十六进制颜色转换为RGB
 */
export const hexToRgb = (hex: string): RGBColor | null => {
  // 移除#号
  const cleanHex = hex.replace('#', '');

  // 验证格式
  if (!/^[0-9A-Fa-f]{6}$/.test(cleanHex)) {
    return null;
  }

  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);

  return { r, g, b };
};

/**
 * 将RGB转换为十六进制颜色
 */
export const rgbToHex = (rgb: RGBColor): string => {
  const toHex = (n: number) => {
    const hex = Math.round(Math.max(0, Math.min(255, n))).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
};

/**
 * 将RGB转换为HSL
 */
export const rgbToHsl = (rgb: RGBColor): HSLColor => {
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }

  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  };
};

/**
 * 将HSL转换为RGB
 */
export const hslToRgb = (hsl: HSLColor): RGBColor => {
  const h = hsl.h / 360;
  const s = hsl.s / 100;
  const l = hsl.l / 100;

  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  };

  let r, g, b;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }

  return {
    r: Math.round(r * 255),
    g: Math.round(g * 255),
    b: Math.round(b * 255),
  };
};

/**
 * 计算相对亮度
 * 根据WCAG 2.1标准计算
 */
export const getRelativeLuminance = (rgb: RGBColor): number => {
  const normalize = (c: number): number => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };

  const r = normalize(rgb.r);
  const g = normalize(rgb.g);
  const b = normalize(rgb.b);

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

/**
 * 计算颜色对比度
 */
export const getContrastRatio = (color1: string, color2: string): ContrastResult => {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);

  if (!rgb1 || !rgb2) {
    return {
      ratio: 0,
      passesAA: false,
      passesAAA: false,
      level: 'FAIL',
    };
  }

  const lum1 = getRelativeLuminance(rgb1);
  const lum2 = getRelativeLuminance(rgb2);

  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);

  const ratio = (lighter + 0.05) / (darker + 0.05);

  return {
    ratio: Math.round(ratio * 100) / 100,
    passesAA: ratio >= 4.5,
    passesAAA: ratio >= 7,
    level: ratio >= 7 ? 'AAA' : ratio >= 4.5 ? 'AA' : 'FAIL',
  };
};

/**
 * 生成符合对比度要求的颜色
 */
export const generateContrastColor = (
  backgroundColor: string,
  targetRatio: number = 4.5
): string => {
  const bgRgb = hexToRgb(backgroundColor);
  if (!bgRgb) return '#000000';

  let bestColor = '#000000';
  let bestRatio = 0;

  // 尝试不同的亮度级别
  for (let lightness = 0; lightness <= 100; lightness += 5) {
    // 生成候选颜色（保持色调，调整亮度）
    const bgHsl = rgbToHsl(bgRgb);
    const candidateHsl: HSLColor = {
      h: bgHsl.h,
      s: Math.max(0, bgHsl.s - 30), // 降低饱和度
      l: lightness,
    };
    const candidateRgb = hslToRgb(candidateHsl);
    const candidateHex = rgbToHex(candidateRgb);

    const ratio = getContrastRatio(candidateHex, backgroundColor).ratio;

    if (ratio > bestRatio) {
      bestRatio = ratio;
      bestColor = candidateHex;
    }

    if (ratio >= targetRatio) {
      return candidateHex;
    }
  }

  return bestColor;
};

/**
 * 调整颜色以达到目标对比度
 */
export const adjustColorForContrast = (
  foreground: string,
  background: string,
  targetRatio: number = 4.5,
  preferDarker: boolean = false
): ContrastResult => {
  const bgRgb = hexToRgb(background);
  if (!bgRgb) {
    return {
      ratio: 0,
      passesAA: false,
      passesAAA: false,
      level: 'FAIL',
    };
  }

  const initialResult = getContrastRatio(foreground, background);

  // 如果已经满足要求，返回原结果
  if (initialResult.ratio >= targetRatio) {
    return initialResult;
  }

  let bestColor = foreground;
  let bestResult = initialResult;

  // 生成调整后的颜色
  const adjustedColor = generateContrastColor(background, targetRatio);
  const adjustedResult = getContrastRatio(adjustedColor, background);

  if (adjustedResult.ratio > bestResult.ratio) {
    bestColor = adjustedColor;
    bestResult = adjustedResult;
  }

  // 如果preferDarker为true，尝试生成更深的颜色
  if (preferDarker) {
    const bgLuminance = getRelativeLuminance(bgRgb);

    // 如果背景较暗，生成更亮的文本
    if (bgLuminance < 0.5) {
      const lightColor = generateContrastColor(background, targetRatio);
      const lightResult = getContrastRatio(lightColor, background);

      if (lightResult.ratio > bestResult.ratio) {
        bestColor = lightColor;
        bestResult = lightResult;
      }
    }
  }

  return {
    ...bestResult,
    suggestedForeground: bestColor !== foreground ? bestColor : undefined,
  };
};

/**
 * 分析主题中的颜色对比度
 */
export const analyzeThemeColors = (theme: Record<string, string>): Array<{
  name: string;
  foreground: string;
  background: string;
  result: ContrastResult;
  type: 'text' | 'border' | 'background';
}> => {
  const analyses = [];

  // 分析文本颜色
  const textPairs = [
    { name: '主标题', fg: theme.primary || '#000000', bg: theme.background || '#ffffff' },
    { name: '副标题', fg: theme.secondary || '#666666', bg: theme.background || '#ffffff' },
    { name: '主体文本', fg: theme.text || '#333333', bg: theme.background || '#ffffff' },
    { name: '提示文本', fg: theme.muted || '#999999', bg: theme.background || '#ffffff' },
    { name: '链接', fg: theme.link || '#0066cc', bg: theme.background || '#ffffff' },
  ];

  textPairs.forEach(pair => {
    const result = getContrastRatio(pair.fg, pair.bg);
    analyses.push({
      name: pair.name,
      foreground: pair.fg,
      background: pair.bg,
      result,
      type: 'text' as const,
    });
  });

  // 分析边框颜色
  const borderPairs = [
    { name: '输入框边框', fg: theme.border || '#cccccc', bg: theme.background || '#ffffff' },
    { name: '卡片边框', fg: theme.cardBorder || '#e0e0e0', bg: theme.card || '#ffffff' },
  ];

  borderPairs.forEach(pair => {
    const result = getContrastRatio(pair.fg, pair.bg);
    analyses.push({
      name: pair.name,
      foreground: pair.fg,
      background: pair.bg,
      result,
      type: 'border' as const,
    });
  });

  return analyses;
};

/**
 * 生成高对比度主题
 */
export const generateHighContrastTheme = (baseTheme: Record<string, string>): Record<string, string> => {
  const background = baseTheme.background || '#ffffff';
  const isDarkBg = getRelativeLuminance(hexToRgb(background) || { r: 255, g: 255, b: 255 }) < 0.5;

  const highContrastTheme = { ...baseTheme };

  if (isDarkBg) {
    // 深色主题
    highContrastTheme.background = '#000000';
    highContrastTheme.text = '#ffffff';
    highContrastTheme.primary = '#ffffff';
    highContrastTheme.secondary = '#cccccc';
    highContrastTheme.muted = '#999999';
    highContrastTheme.border = '#ffffff';
    highContrastTheme.card = '#000000';
  } else {
    // 浅色主题
    highContrastTheme.background = '#ffffff';
    highContrastTheme.text = '#000000';
    highContrastTheme.primary = '#000000';
    highContrastTheme.secondary = '#666666';
    highContrastTheme.muted = '#333333';
    highContrastTheme.border = '#000000';
    highContrastTheme.card = '#ffffff';
  }

  // 确保所有颜色对比度都符合要求
  Object.keys(highContrastTheme).forEach(key => {
    if (key !== 'background') {
      const color = highContrastTheme[key];
      if (color && typeof color === 'string') {
        const adjustedResult = adjustColorForContrast(color, highContrastTheme.background, 7);
        if (adjustedResult.suggestedForeground) {
          highContrastTheme[key] = adjustedResult.suggestedForeground;
        }
      }
    }
  });

  return highContrastTheme;
};

/**
 * 检测用户的对比度偏好
 */
export const detectContrastPreference = (): 'normal' | 'high' | 'custom' => {
  // 检测prefers-contrast媒体查询
  if (typeof window !== 'undefined' && window.matchMedia) {
    const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
    if (highContrastQuery.matches) {
      return 'high';
    }

    const reducedContrastQuery = window.matchMedia('(prefers-contrast: low)');
    if (reducedContrastQuery.matches) {
      return 'normal';
    }
  }

  return 'normal';
};

/**
 * 获取颜色对比度建议
 */
export const getContrastRecommendations = (result: ContrastResult): string[] => {
  const recommendations: string[] = [];

  if (result.level === 'FAIL') {
    if (result.ratio < 3) {
      recommendations.push('对比度严重不足，建议使用完全不同的颜色组合');
    } else if (result.ratio < 4.5) {
      recommendations.push('对比度未达到WCAG AA标准，建议增加颜色差异');
    }
    recommendations.push(`当前对比度: ${result.ratio}:1，需要至少4.5:1`);
    recommendations.push('考虑使用在线颜色对比度检查工具进行微调');
  } else if (result.level === 'AA') {
    recommendations.push('对比度符合WCAG AA标准');
    if (result.ratio < 7) {
      recommendations.push('可以考虑进一步提高对比度以符合AAA标准');
    }
  } else {
    recommendations.push('对比度符合WCAG AAA最高标准');
  }

  return recommendations;
};