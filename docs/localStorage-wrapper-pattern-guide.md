# localStorage包装模式使用指南

## 概述

localStorage包装模式是一种用于增强浏览器存储API可用性和测试友好性的设计模式。该模式通过包装原生localStorage API，提供统一的错误处理、SSR兼容性和测试支持。

## 核心优势

1. **测试友好** - 易于Mock和注入测试替身
2. **SSR兼容** - 在服务器端渲染环境中安全运行
3. **错误处理** - 统一的错误处理和降级策略
4. **类型安全** - TypeScript类型支持
5. **API一致性** - 保持与原生localStorage相同的接口

## 基础实现

### 1. 核心包装函数

```typescript
// localStorage wrapper for testability
const getLocalStorage = (): Storage => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage;
  }

  // Fallback for SSR or missing localStorage
  return {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
    clear: () => {},
    length: 0,
    key: () => null,
  };
};
```

**关键特性：**
- 环境检测：检查window和localStorage是否存在
- SSR兼容：在Node.js环境中提供安全的fallback
- API一致性：保持与原生localStorage相同的接口

### 2. 类型安全的存储键

```typescript
const STORAGE_KEYS = {
  USER_PREFERENCES: 'strategy_user_preferences',
  PARAMETERS_BACKUP: 'strategy_parameters_backup',
  LAST_USED: 'strategy_last_used_parameters',
  SESSION_TOKEN: 'auth_session_token',
  UI_SETTINGS: 'app_ui_settings',
} as const;

type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS];
```

**优势：**
- 类型安全：防止键名拼写错误
- 集中管理：所有存储键在一个地方定义
- 重构友好：修改键名时只需更新一处

### 3. 增强的存储操作

```typescript
class StorageManager {
  private storage: Storage;

  constructor() {
    this.storage = getLocalStorage();
  }

  // 安全的 getItem 操作
  getItem<T>(key: string, defaultValue: T | null = null): T | null {
    try {
      const item = this.storage.getItem(key);
      if (item === null) return defaultValue;

      const parsed = JSON.parse(item);
      return parsed !== null ? parsed : defaultValue;
    } catch (error) {
      console.warn(`Failed to parse storage item "${key}":`, error);
      return defaultValue;
    }
  }

  // 安全的 setItem 操作
  setItem<T>(key: string, value: T): boolean {
    try {
      const serialized = JSON.stringify(value);
      this.storage.setItem(key, serialized);
      return true;
    } catch (error) {
      console.error(`Failed to save storage item "${key}":`, error);
      return false;
    }
  }

  // 批量操作
  getMultiple<T extends Record<string, any>>(keys: string[]): Partial<T> {
    const result: Partial<T> = {};

    for (const key of keys) {
      const value = this.getItem(key);
      if (value !== null) {
        result[key as keyof T] = value;
      }
    }

    return result;
  }

  // 条件性更新
  updateItem<T>(key: string, updater: (current: T | null) => T): boolean {
    try {
      const current = this.getItem<T>(key);
      const updated = updater(current);
      return this.setItem(key, updated);
    } catch (error) {
      console.error(`Failed to update storage item "${key}":`, error);
      return false;
    }
  }

  // 清理过期数据
  cleanup(maxAge: number = 7 * 24 * 60 * 60 * 1000): void {
    const now = Date.now();

    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i);
      if (!key) continue;

      try {
        const item = this.storage.getItem(key);
        if (!item) continue;

        const parsed = JSON.parse(item);
        if (parsed.timestamp && (now - parsed.timestamp) > maxAge) {
          this.storage.removeItem(key);
        }
      } catch (error) {
        // 清理无法解析的项
        this.storage.removeItem(key);
      }
    }
  }
}

// 单例模式
export const storageManager = new StorageManager();
```

## 实际应用场景

### 1. 用户偏好设置持久化

```typescript
interface UserPreferences {
  defaultParameters: StrategyParameters;
  autoSave: boolean;
  showAdvanced: boolean;
  chartPreferences: ChartPreferences;
  lastUpdated: number;
}

const PREFERENCES_KEY = STORAGE_KEYS.USER_PREFERENCES;

class UserPreferencesManager {
  private static readonly DEFAULT_PREFERENCES: UserPreferences = {
    defaultParameters: {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
    autoSave: true,
    showAdvanced: false,
    chartPreferences: {
      showGrid: true,
      showVolume: false,
      animationDuration: 300,
    },
    lastUpdated: Date.now(),
  };

  static loadPreferences(): UserPreferences {
    const preferences = storageManager.getItem<UserPreferences>(
      PREFERENCES_KEY,
      this.DEFAULT_PREFERENCES
    );

    // 合并默认值，确保所有字段都存在
    return {
      ...this.DEFAULT_PREFERENCES,
      ...preferences,
      defaultParameters: {
        ...this.DEFAULT_PREFERENCES.defaultParameters,
        ...preferences?.defaultParameters,
      },
      chartPreferences: {
        ...this.DEFAULT_PREFERENCES.chartPreferences,
        ...preferences?.chartPreferences,
      },
    };
  }

  static savePreferences(preferences: UserPreferences): boolean {
    const updatedPreferences = {
      ...preferences,
      lastUpdated: Date.now(),
    };

    return storageManager.setItem(PREFERENCES_KEY, updatedPreferences);
  }

  static updatePreferences(
    updates: Partial<UserPreferences>
  ): boolean {
    return storageManager.updateItem<UserPreferences>(
      PREFERENCES_KEY,
      (current) => ({
        ...this.DEFAULT_PREFERENCES,
        ...current,
        ...updates,
        lastUpdated: Date.now(),
      })
    );
  }

  static resetPreferences(): boolean {
    return storageManager.setItem(PREFERENCES_KEY, this.DEFAULT_PREFERENCES);
  }
}
```

### 2. 会话状态管理

```typescript
interface SessionState {
  isAuthenticated: boolean;
  userId: string | null;
  token: string | null;
  loginTime: number | null;
  lastActivity: number | null;
}

const SESSION_KEY = STORAGE_KEYS.SESSION_TOKEN;

class SessionManager {
  private static readonly SESSION_TIMEOUT = 30 * 60 * 1000; // 30分钟

  static getSession(): SessionState {
    return storageManager.getItem<SessionState>(SESSION_KEY, {
      isAuthenticated: false,
      userId: null,
      token: null,
      loginTime: null,
      lastActivity: null,
    });
  }

  static createSession(userId: string, token: string): boolean {
    const session: SessionState = {
      isAuthenticated: true,
      userId,
      token,
      loginTime: Date.now(),
      lastActivity: Date.now(),
    };

    return storageManager.setItem(SESSION_KEY, session);
  }

  static updateActivity(): boolean {
    return storageManager.updateItem<SessionState>(
      SESSION_KEY,
      (session) => ({
        ...session!,
        lastActivity: Date.now(),
      })
    );
  }

  static isSessionValid(): boolean {
    const session = this.getSession();

    if (!session.isAuthenticated || !session.lastActivity) {
      return false;
    }

    const now = Date.now();
    const timeSinceActivity = now - session.lastActivity;

    return timeSinceActivity < this.SESSION_TIMEOUT;
  }

  static clearSession(): boolean {
    storageManager.removeItem(SESSION_KEY);
    return true;
  }
}
```

### 3. 缓存管理

```typescript
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  version: string;
}

class CacheManager {
  private static readonly DEFAULT_TTL = 5 * 60 * 1000; // 5分钟

  static set<T>(
    key: string,
    data: T,
    ttl: number = this.DEFAULT_TTL,
    version: string = '1.0'
  ): boolean {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
      version,
    };

    return storageManager.setItem(`cache_${key}`, entry);
  }

  static get<T>(key: string, version?: string): T | null {
    const entry = storageManager.getItem<CacheEntry<T>>(`cache_${key}`);

    if (!entry) return null;

    // 版本检查
    if (version && entry.version !== version) {
      storageManager.removeItem(`cache_${key}`);
      return null;
    }

    // TTL检查
    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      storageManager.removeItem(`cache_${key}`);
      return null;
    }

    return entry.data;
  }

  static invalidate(key: string): void {
    storageManager.removeItem(`cache_${key}`);
  }

  static clearExpired(): void {
    storageManager.cleanup(0); // 立即清理所有过期项
  }
}
```

## React Hook集成

### 1. 通用localStorage Hook

```typescript
import { useState, useEffect, useCallback } from 'react';

interface UseLocalStorageOptions<T> {
  defaultValue: T;
  serializer?: {
    read: (value: string) => T;
    write: (value: T) => string;
  };
  onError?: (error: Error) => void;
}

function useLocalStorage<T>(
  key: string,
  options: UseLocalStorageOptions<T>
) {
  const { defaultValue, serializer, onError } = options;

  const [value, setValue] = useState<T>(() => {
    try {
      const item = getLocalStorage().getItem(key);
      if (item === null) return defaultValue;

      if (serializer) {
        return serializer.read(item);
      }

      return JSON.parse(item);
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      onError?.(error as Error);
      return defaultValue;
    }
  });

  const setStoredValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        const newValue = value instanceof Function ? value(value) : value;

        setValue(newValue);

        const serialized = serializer
          ? serializer.write(newValue)
          : JSON.stringify(newValue);

        getLocalStorage().setItem(key, serialized);
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
        onError?.(error as Error);
      }
    },
    [key, serializer, onError]
  );

  const removeValue = useCallback(() => {
    try {
      setValue(defaultValue);
      getLocalStorage().removeItem(key);
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error);
      onError?.(error as Error);
    }
  }, [key, defaultValue, onError]);

  return [value, setStoredValue, removeValue] as const;
}
```

### 2. 用户偏好Hook

```typescript
function useUserPreferences() {
  const [preferences, setPreferences, resetPreferences] = useLocalStorage(
    STORAGE_KEYS.USER_PREFERENCES,
    {
      defaultValue: UserPreferencesManager.DEFAULT_PREFERENCES,
      onError: (error) => {
        console.error('Failed to load user preferences:', error);
      },
    }
  );

  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setPreferences(prev => ({ ...prev, ...updates }));
  }, [setPreferences]);

  const updateParameter = useCallback((param: string, value: any) => {
    setPreferences(prev => ({
      ...prev,
      defaultParameters: {
        ...prev.defaultParameters,
        [param]: value,
      },
    }));
  }, [setPreferences]);

  return {
    preferences,
    updatePreferences,
    updateParameter,
    resetPreferences,
  };
}
```

### 3. 使用示例

```typescript
function UserSettingsComponent() {
  const { preferences, updatePreferences, updateParameter } = useUserPreferences();

  const handleAutoSaveToggle = (enabled: boolean) => {
    updatePreferences({ autoSave: enabled });
  };

  const handleMovingAverageChange = (period: number) => {
    updateParameter('movingAveragePeriod', period);
  };

  return (
    <div>
      <Switch
        checked={preferences.autoSave}
        onCheckedChange={handleAutoSaveToggle}
      >
        自动保存
      </Switch>

      <NumberInput
        value={preferences.defaultParameters.movingAveragePeriod}
        onChange={handleMovingAverageChange}
        min={1}
        max={100}
      />
    </div>
  );
}
```

## 测试策略

### 1. Mock实现

```typescript
// localStorage Mock for testing
export const createLocalStorageMock = () => {
  let store: Record<string, string> = {};

  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index: number) =>
      Object.keys(store)[index] || null
    ),
    // Test helpers
    _getStore: () => ({ ...store }),
    _setStore: (newStore: Record<string, string>) => {
      store = newStore;
    },
  };
};
```

### 2. 测试配置

```typescript
// jest.setup.js
const mockLocalStorage = createLocalStorageMock();
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// 在每个测试前重置
beforeEach(() => {
  mockLocalStorage.clear();
  jest.clearAllMocks();
});
```

### 3. 组件测试示例

```typescript
describe('UserPreferences', () => {
  let mockLocalStorage: ReturnType<typeof createLocalStorageMock>;

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock();
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
    });
  });

  it('should load preferences from localStorage', () => {
    const testPreferences = {
      autoSave: false,
      showAdvanced: true,
      defaultParameters: { movingAveragePeriod: 30 },
    };

    mockLocalStorage.setItem('userPreferences', JSON.stringify(testPreferences));

    render(<UserPreferencesComponent />);

    expect(screen.getByRole('switch', { name: '自动保存' })).not.toBeChecked();
    expect(screen.getByDisplayValue('30')).toBeInTheDocument();
  });

  it('should save preferences to localStorage', async () => {
    render(<UserPreferencesComponent />);

    const autoSaveSwitch = screen.getByRole('switch', { name: '自动保存' });
    fireEvent.click(autoSaveSwitch);

    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'userPreferences',
        expect.stringContaining('"autoSave":false')
      );
    });
  });
});
```

## 性能优化

### 1. 防抖更新

```typescript
import { debounce } from 'lodash';

class OptimizedStorageManager extends StorageManager {
  private debouncedSetItem = debounce(this.setItem.bind(this), 300);

  setItemDebounced<T>(key: string, value: T): void {
    this.debouncedSetItem(key, value);
  }

  // 取消防抖调用
  flushDebouncedUpdates(): void {
    this.debouncedSetItem.flush();
  }
}
```

### 2. 批量操作

```typescript
class BatchStorageManager extends StorageManager {
  private batchQueue: Array<() => void> = [];
  private batchTimeout: NodeJS.Timeout | null = null;

  batchOperation(operation: () => void): void {
    this.batchQueue.push(operation);

    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
    }

    this.batchTimeout = setTimeout(() => {
      this.flushBatch();
    }, 50);
  }

  private flushBatch(): void {
    for (const operation of this.batchQueue) {
      operation();
    }
    this.batchQueue = [];
    this.batchTimeout = null;
  }

  // 组件卸载时确保执行所有批量操作
  cleanup(): void {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.flushBatch();
    }
  }
}
```

### 3. 内存优化

```typescript
class MemoryEfficientStorage {
  private cache = new Map<string, any>();
  private maxCacheSize = 100;

  private evictOldest(): void {
    if (this.cache.size >= this.maxCacheSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  get<T>(key: string): T | null {
    if (this.cache.has(key)) {
      return this.cache.get(key);
    }

    try {
      const item = getLocalStorage().getItem(key);
      if (item === null) return null;

      const parsed = JSON.parse(item);

      // 缓存解析结果
      this.evictOldest();
      this.cache.set(key, parsed);

      return parsed;
    } catch (error) {
      console.warn(`Failed to parse storage item "${key}":`, error);
      return null;
    }
  }
}
```

## 错误处理和监控

### 1. 存储错误监控

```typescript
class StorageMonitor {
  private errorCounts = new Map<string, number>();
  private maxErrors = 3;

  recordError(operation: string, error: Error): void {
    const count = this.errorCounts.get(operation) || 0;
    this.errorCounts.set(operation, count + 1);

    // 错误过多时降级到内存存储
    if (count + 1 >= this.maxErrors) {
      console.warn(`Storage operation "${operation}" failed ${count + 1} times, switching to memory storage`);
      this.enableMemoryFallback(operation);
    }
  }

  private enableMemoryFallback(operation: string): void {
    // 实现内存存储fallback逻辑
  }

  reset(): void {
    this.errorCounts.clear();
  }
}
```

### 2. 存储配额管理

```typescript
class StorageQuotaManager {
  private static readonly QUOTA_LIMIT = 5 * 1024 * 1024; // 5MB
  private static readonly WARNING_THRESHOLD = 0.8; // 80%

  static checkQuota(): { used: number; available: number; usage: number } {
    let totalSize = 0;

    for (let key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        const value = localStorage.getItem(key);
        if (value) {
          totalSize += new Blob([value]).size;
        }
      }
    }

    const used = totalSize;
    const available = this.QUOTA_LIMIT - used;
    const usage = used / this.QUOTA_LIMIT;

    return { used, available, usage };
  }

  static isNearQuotaLimit(): boolean {
    const { usage } = this.checkQuota();
    return usage > this.WARNING_THRESHOLD;
  }

  static cleanupOldData(): void {
    const { usage } = this.checkQuota();

    if (usage > this.WARNING_THRESHOLD) {
      // 清理旧数据
      const cutoff = Date.now() - (7 * 24 * 60 * 60 * 1000); // 7天前

      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          try {
            const item = localStorage.getItem(key);
            if (item) {
              const parsed = JSON.parse(item);
              if (parsed.timestamp && parsed.timestamp < cutoff) {
                localStorage.removeItem(key);
              }
            }
          } catch (error) {
            // 清理无法解析的项
            localStorage.removeItem(key);
          }
        }
      }
    }
  }
}
```

## 最佳实践清单

### ✅ 推荐实践

1. **环境检测** - 始终检查localStorage可用性
2. **错误处理** - 包装所有存储操作在try-catch中
3. **类型安全** - 使用TypeScript接口定义数据结构
4. **默认值** - 为所有存储项提供合理的默认值
5. **序列化** - 使用JSON序列化，避免存储复杂对象
6. **测试友好** - 设计易于Mock和测试的接口
7. **性能优化** - 使用防抖、缓存和批量操作
8. **内存管理** - 定期清理过期和无效数据

### ❌ 避免实践

1. **同步存储** - 避免在主线程中进行大量存储操作
2. **直接依赖** - 不要直接依赖localStorage，使用包装器
3. **存储敏感信息** - 不要在localStorage中存储密码、令牌等敏感信息
4. **忽略错误** - 不要忽略存储错误，要有适当的错误处理
5. **过度存储** - 避免存储过大的数据集
6. **版本兼容** - 考虑数据格式的向后兼容性
7. **竞态条件** - 避免并发读写导致的数据不一致

## 故障排除

### 常见问题和解决方案

1. **QuotaExceededError**
   ```typescript
   try {
     localStorage.setItem(key, value);
   } catch (error) {
     if (error.name === 'QuotaExceededError') {
       // 清理旧数据或使用sessionStorage
       StorageQuotaManager.cleanupOldData();
     }
   }
   ```

2. **SecurityError (隐私模式)**
   ```typescript
   try {
     localStorage.setItem(key, value);
   } catch (error) {
     if (error.name === 'SecurityError') {
       // 使用内存存储作为fallback
       memoryStorage.set(key, value);
     }
   }
   ```

3. **JSON解析错误**
   ```typescript
   try {
     const parsed = JSON.parse(item);
     return parsed;
   } catch (error) {
     console.warn('Invalid JSON in localStorage:', error);
     localStorage.removeItem(key);
     return defaultValue;
   }
   ```

---

**文档版本:** 1.0
**最后更新:** 2025-11-25
**维护者:** 开发团队
**相关文档:** [状态管理最佳实践](./state-management-best-practices.md)