/**
 * UX (User Experience) 相关类型定义
 */

// 基础UX指标类型
export interface UXMetrics {
  id: string;
  timestamp: string;
  componentName: string;
  actionType:
    | 'render'
    | 'api_call'
    | 'user_interaction'
    | 'navigation'
    | 'error';
  componentRenderTime?: number; // ms
  apiResponseTime?: number; // ms
  userInteractionTime?: number; // ms
  memoryUsage?: number; // MB
  metadata?: Record<string, any>;
}

// 用户行为数据类型
export interface UserBehaviorData {
  id: string;
  sessionId: string;
  userId?: string;
  pagePath: string;
  actionType:
    | 'click'
    | 'scroll'
    | 'hover'
    | 'form_submit'
    | 'navigation'
    | 'search'
    | 'filter';
  elementId?: string;
  elementSelector?: string;
  timestamp: string;
  duration?: number; // ms
  coordinates?: { x: number; y: number };
  scrollPosition?: { x: number; y: number };
  metadata?: Record<string, any>;
}

// 性能阈值配置
export interface PerformanceThreshold {
  componentRenderTime: number; // ms
  apiResponseTime: number; // ms
  userInteractionTime: number; // ms
  memoryUsage: number; // MB
  firstContentfulPaint: number; // ms
  largestContentfulPaint: number; // ms
  cumulativeLayoutShift: number;
  firstInputDelay: number; // ms
}

// UX优化配置
export interface UXOptimizationConfig {
  enablePerformanceMonitoring: boolean;
  enableUserBehaviorTracking: boolean;
  enableErrorTracking: boolean;
  performanceThresholds: PerformanceThreshold;
  reportToService: boolean;
  debounceDelay: number;
  throttleDelay: number;
  cacheConfig: {
    defaultTTL: number; // ms
    maxSize: number;
    cleanupInterval: number; // ms
  };
  lazyLoadConfig: {
    rootMargin: string;
    threshold: number;
  };
}

// 错误信息类型
export interface UXError {
  id: string;
  timestamp: string;
  componentName?: string;
  errorType:
    | 'javascript_error'
    | 'network_error'
    | 'api_error'
    | 'render_error'
    | 'user_error';
  message: string;
  stack?: string;
  userAgent: string;
  pagePath: string;
  userId?: string;
  sessionId: string;
  metadata?: Record<string, any>;
  resolved: boolean;
  resolutionNotes?: string;
}

// 用户反馈类型
export interface UserFeedback {
  id: string;
  timestamp: string;
  userId?: string;
  sessionId: string;
  feedbackType:
    | 'bug_report'
    | 'feature_request'
    | 'general_feedback'
    | 'usability_issue';
  rating?: number; // 1-5
  category: 'performance' | 'ui_ux' | 'functionality' | 'error' | 'other';
  title: string;
  description: string;
  email?: string;
  attachments?: string[];
  pagePath: string;
  userAgent: string;
  metadata?: Record<string, any>;
  status: 'pending' | 'in_review' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
}

// 帮助文档类型
export interface HelpDocument {
  id: string;
  title: string;
  content: string;
  category:
    | 'getting_started'
    | 'features'
    | 'troubleshooting'
    | 'api'
    | 'tutorials'
    | 'faq';
  tags: string[];
  order: number;
  lastUpdated: string;
  author: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedReadTime: number; // minutes
  relatedDocuments: string[];
  searchableContent: string;
}

// FAQ项目类型
export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: string;
  tags: string[];
  popularity: number; // view count
  helpful: number; // helpful votes
  notHelpful: number; // not helpful votes
  lastUpdated: string;
  relatedQuestions: string[];
}

// 用户引导步骤类型
export interface UserGuideStep {
  id: string;
  title: string;
  content: string;
  targetSelector?: string; // CSS selector for target element
  position: 'top' | 'bottom' | 'left' | 'right' | 'center';
  type: 'tooltip' | 'modal' | 'highlight' | 'spotlight';
  actionRequired?: boolean;
  actionType?: 'click' | 'input' | 'scroll' | 'wait';
  actionTarget?: string;
  skipAllowed: boolean;
  order: number;
  imageUrl?: string;
  videoUrl?: string;
}

// 用户引导流程类型
export interface UserGuide {
  id: string;
  name: string;
  description: string;
  category: 'onboarding' | 'feature_tour' | 'tutorial' | 'help';
  targetAudience: 'new_user' | 'returning_user' | 'power_user' | 'all';
  steps: UserGuideStep[];
  triggerConditions: {
    pagePath?: string;
    userRole?: string;
    previousActions?: string[];
    timeOnPage?: number; // seconds
  };
  isRequired: boolean;
  priority: number;
  showProgress: boolean;
  allowSkip: boolean;
  autoStart: boolean;
}

// 用户进度跟踪类型
export interface UserProgress {
  id: string;
  userId?: string;
  sessionId: string;
  guideId: string;
  currentStep: number;
  completedSteps: string[];
  startTime: string;
  lastActivityTime: string;
  completedTime?: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped' | 'abandoned';
  timeSpent: number; // seconds
  interactions: UserProgressInteraction[];
}

// 用户进度交互记录
export interface UserProgressInteraction {
  id: string;
  stepId: string;
  action: 'start' | 'complete' | 'skip' | 'back' | 'forward' | 'close';
  timestamp: string;
  duration?: number; // seconds
  metadata?: Record<string, any>;
}

// 成就系统类型
export interface Achievement {
  id: string;
  name: string;
  description: string;
  category: 'learning' | 'usage' | 'exploration' | 'social' | 'technical';
  type: 'milestone' | 'streak' | 'collection' | 'challenge';
  icon: string;
  points: number;
  requirements: AchievementRequirement[];
  rewards: AchievementReward[];
  hidden: boolean;
  order: number;
}

// 成就要求
export interface AchievementRequirement {
  type:
    | 'complete_guide'
    | 'use_feature'
    | 'time_spent'
    | 'actions_count'
    | 'visit_pages';
  target: string | number;
  operator: 'equals' | 'greater_than' | 'less_than' | 'at_least';
  description: string;
}

// 成就奖励
export interface AchievementReward {
  type: 'points' | 'badge' | 'title' | 'feature_unlock';
  value: string | number;
  description: string;
}

// 用户成就记录
export interface UserAchievement {
  id: string;
  userId?: string;
  achievementId: string;
  unlockedAt: string;
  progress: number; // 0-100 percentage
  metadata?: Record<string, any>;
}

// 设备信息类型
export interface DeviceInfo {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  userAgent: string;
  screenResolution: string;
  viewportSize: { width: number; height: number };
  pixelRatio: number;
  touchSupport: boolean;
  orientation: 'portrait' | 'landscape';
}

// 网络信息类型
export interface NetworkInfo {
  effectiveType?: 'slow-2g' | '2g' | '3g' | '4g';
  downlink?: number; // Mbps
  rtt?: number; // round-trip time in ms
  saveData?: boolean;
  online: boolean;
  connectionType?:
    | 'bluetooth'
    | 'cellular'
    | 'ethernet'
    | 'none'
    | 'wifi'
    | 'wimax'
    | 'other'
    | 'unknown';
}

// 浏览器信息类型
export interface BrowserInfo {
  name: string;
  version: string;
  engine: string;
  os: string;
  language: string;
  cookieEnabled: boolean;
  doNotTrack: boolean;
  onLine: boolean;
}

// 页面性能指标类型
export interface PagePerformanceMetrics {
  domContentLoaded: number; // ms
  loadComplete: number; // ms
  firstPaint: number; // ms
  firstContentfulPaint: number; // ms
  largestContentfulPaint: number; // ms
  firstInputDelay: number; // ms
  cumulativeLayoutShift: number;
  timeToInteractive: number; // ms
  totalBlockingTime: number; // ms
}

// 缓存项类型
export interface CacheItem<T = any> {
  key: string;
  data: T;
  timestamp: number;
  ttl: number;
  accessCount: number;
  lastAccessed: number;
  size: number; // bytes
}

// 加载状态类型
export interface LoadingState {
  isLoading: boolean;
  loadingText?: string;
  progress?: number; // 0-100
  stage?: 'initializing' | 'loading' | 'processing' | 'finalizing';
  error?: string;
}

// 骨架屏配置类型
export interface SkeletonConfig {
  variant: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  lines?: number;
  animation: 'pulse' | 'wave' | 'none';
  className?: string;
}

// API响应包装类型
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp: string;
  requestId?: string;
  metadata?: Record<string, any>;
}

// UX事件类型
export interface UXEvent {
  type: 'performance' | 'error' | 'interaction' | 'navigation' | 'feedback';
  data: any;
  timestamp: string;
  sessionId: string;
  userId?: string;
  metadata?: Record<string, any>;
}

// 搜索结果类型
export interface SearchResult<T = any> {
  item: T;
  score: number;
  matches: Array<{
    field: string;
    value: string;
    indices: Array<[number, number]>;
  }>;
}

// 分页信息类型
export interface PaginationInfo {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// 排序配置类型
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
  type: 'string' | 'number' | 'date';
}

// 过滤配置类型
export interface FilterConfig {
  field: string;
  operator:
    | 'equals'
    | 'contains'
    | 'startsWith'
    | 'endsWith'
    | 'greaterThan'
    | 'lessThan'
    | 'between';
  value: any;
  valueType: 'string' | 'number' | 'date' | 'boolean' | 'array';
}

// 表格列配置类型
export interface TableColumn<T = any> {
  key: string;
  title: string;
  dataIndex: keyof T;
  width?: number | string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, record: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  fixed?: 'left' | 'right';
  ellipsis?: boolean;
}

// 通知类型
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number; // ms, 0 for persistent
  action?: {
    label: string;
    onClick: () => void;
  };
  timestamp: string;
  read: boolean;
}

// 模态框配置类型
export interface ModalConfig {
  title?: string;
  content: React.ReactNode;
  width?: number | string;
  height?: number | string;
  closable?: boolean;
  maskClosable?: boolean;
  centered?: boolean;
  footer?: React.ReactNode;
  className?: string;
  onClose?: () => void;
  onOk?: () => void;
  onCancel?: () => void;
}

// 抽屉配置类型
export interface DrawerConfig {
  title?: string;
  content: React.ReactNode;
  placement: 'top' | 'right' | 'bottom' | 'left';
  width?: number | string;
  height?: number | string;
  closable?: boolean;
  maskClosable?: boolean;
  className?: string;
  onClose?: () => void;
}

// 主题配置类型
export interface ThemeConfig {
  mode: 'light' | 'dark' | 'auto';
  primaryColor: string;
  backgroundColor: string;
  textColor: string;
  borderColor: string;
  borderRadius: number;
  fontSize: {
    small: number;
    medium: number;
    large: number;
  };
  spacing: {
    small: number;
    medium: number;
    large: number;
  };
}

// 导出所有类型
export type {
  // 核心类型
  UXMetrics,
  UserBehaviorData,
  PerformanceThreshold,
  UXOptimizationConfig,

  // 错误和反馈
  UXError,
  UserFeedback,

  // 帮助系统
  HelpDocument,
  FAQItem,

  // 用户引导
  UserGuideStep,
  UserGuide,
  UserProgress,
  UserProgressInteraction,

  // 成就系统
  Achievement,
  AchievementRequirement,
  AchievementReward,
  UserAchievement,

  // 设备和环境信息
  DeviceInfo,
  NetworkInfo,
  BrowserInfo,
  PagePerformanceMetrics,

  // 缓存和加载
  CacheItem,
  LoadingState,
  SkeletonConfig,

  // API和响应
  APIResponse,
  UXEvent,

  // 搜索和分页
  SearchResult,
  PaginationInfo,
  SortConfig,
  FilterConfig,

  // UI组件配置
  TableColumn,
  Notification,
  ModalConfig,
  DrawerConfig,
  ThemeConfig,
};
