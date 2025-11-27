# 状态管理最佳实践指南

## 概述

本文档定义了项目中React组件状态管理的最佳实践，包括本地状态、持久化状态、测试策略和性能优化指导原则。

## 核心原则

### 1. 状态管理分层架构

```
Local State (组件级) → Context (功能级) → Global (应用级)
     ↓                    ↓                    ↓
   useState            useContext            Zustand/Redux
```

#### 优先级顺序：
1. **本地状态优先** - 使用React `useState` 管理组件本地状态
2. **状态同步** - 实现正确的 `useEffect` 依赖关系防止闭包陷阱
3. **错误边界** - 将状态管理包装在try-catch块中增强错误恢复性
4. **状态不可变性** - 始终将状态视为不可变，使用函数式更新

### 2. 状态管理架构约束

#### 允许的模式：
- ✅ 使用React `useState` 管理组件本地状态
- ✅ 实现 `useEffect` 正确的依赖管理防止stale closures
- ✅ 在错误处理中使用try-catch块增强状态恢复性
- ✅ 始终将状态视为不可变，使用函数式更新

#### 禁止的模式：
- ❌ 为本地组件状态使用外部状态管理库（Redux, Zustand等）
- ❌ localStorage操作必须包装在错误处理中
- ❌ 状态更新必须触发适当的重新渲染
- ❌ 防止并发状态更新中的竞态条件

## 实现模式

### 1. localStorage包装模式

基于项目中的成功实现，推荐使用以下包装模式：

```typescript
// localStorage wrapper for testability
const getLocalStorage = () => {
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

**优势：**
- 支持测试时的Mock注入
- 提供SSR兼容性
- 统一错误处理
- 保持API一致性

### 2. 状态同步模式

```typescript
const [preferences, setPreferences] = useState<UserPreferencesType>(DEFAULT_PREFERENCES);
const [isLoading, setIsLoading] = useState(true);

// Proper localStorage integration
useEffect(() => {
  const loadPreferences = () => {
    try {
      const storage = getLocalStorage();
      const saved = storage.getItem('userPreferences');
      if (saved) {
        setPreferences(JSON.parse(saved));
      }
    } catch (error) {
      console.warn('Failed to load preferences:', error);
    } finally {
      setIsLoading(false);
    }
  };

  loadPreferences();
}, []);

// Auto-save functionality with debouncing
useEffect(() => {
  if (!isLoading) {
    const storage = getLocalStorage();
    storage.setItem('userPreferences', JSON.stringify(preferences));
  }
}, [preferences, isLoading]);
```

**关键特性：**
- 加载状态管理
- 错误处理和回退
- 自动保存机制
- 防止竞态条件

### 3. 防抖状态更新模式

```typescript
const debouncedSave = useCallback(
  debounce((newPreferences: UserPreferencesType) => {
    const storage = getLocalStorage();
    try {
      storage.setItem('userPreferences', JSON.stringify(newPreferences));
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  }, 500),
  []
);
```

**适用场景：**
- 频繁的状态更新
- localStorage持久化
- API调用优化
- 性能敏感操作

## 测试策略

### 1. 测试分层架构 (70/20/10 分层)

#### 单元测试 (70%)
```typescript
// 状态管理函数隔离测试
describe('preference update logic', () => {
  it('should update moving average period correctly', () => {
    const updatePeriod = (current: number, newPeriod: number) =>
      Math.max(1, Math.min(100, newPeriod));

    expect(updatePeriod(20, 30)).toBe(30);
    expect(updatePeriod(20, 150)).toBe(100); // Clamped
    expect(updatePeriod(20, -5)).toBe(1);   // Clamped
  });
});
```

**要求：**
- Jest + React Testing Library
- localStorage完整Mock支持
- 90%+ 业务逻辑覆盖率
- <100ms 每个测试执行时间

#### 集成测试 (20%)
```typescript
// 组件生命周期与localStorage集成
describe('UserPreferences Integration', () => {
  beforeEach(() => {
    const mockLocalStorage = createLocalStorageMock();
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage
    });
  });

  it('should persist preferences on component unmount', async () => {
    render(<UserPreferences {...mockProps} />);

    const saveButton = screen.getByText('保存设置');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'userPreferences',
        expect.stringContaining('"movingAveragePeriod":30')
      );
    });
  });
});
```

#### 端到端测试 (10%)
- 完整用户工作流程
- 跨组件状态同步
- 关键业务场景验证

### 2. localStorage测试最佳实践

#### 完整Mock实现
```typescript
const createLocalStorageMock = () => {
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
    _getStore: () => ({ ...store }), // Test helper
  };
};
```

#### 测试配置
```typescript
// jest.setup.js
const mockLocalStorage = createLocalStorageMock();
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

// beforeEach
beforeEach(() => {
  mockLocalStorage.clear();
  jest.clearAllMocks();
});
```

## 性能优化

### 1. 状态更新优化

```typescript
// ✅ 使用函数式更新避免依赖闭包
const handleParameterChange = useCallback((param: string, value: any) => {
  setPreferences(prev => ({
    ...prev,
    defaultParameters: {
      ...prev.defaultParameters,
      [param]: value
    }
  }));
}, []);

// ✅ 使用useMemo缓存计算结果
const formattedPreferences = useMemo(() => {
  return {
    ...preferences,
    formattedMovingAverage: `${preferences.defaultParameters.movingAveragePeriod}天`,
  };
}, [preferences.defaultParameters.movingAveragePeriod]);

// ✅ 使用useCallback缓存事件处理器
const savePreferences = useCallback(async () => {
  setIsSaving(true);
  try {
    await saveToServer(preferences);
    showMessage('success', '保存成功');
  } catch (error) {
    showMessage('error', '保存失败');
  } finally {
    setIsSaving(false);
  }
}, [preferences]);
```

### 2. 渲染优化

```typescript
// ✅ 使用React.memo防止不必要的重新渲染
const PreferencePanel = React.memo<PreferencePanelProps>(({
  preferences,
  onChange
}) => {
  return (
    <div>
      {/* 组件内容 */}
    </div>
  );
});

// ✅ 使用useMemo优化复杂计算
const expensiveCalculation = useMemo(() => {
  return preferences.parameters.reduce((acc, param) => {
    return acc + complexCalculation(param);
  }, 0);
}, [preferences.parameters]);
```

## 错误处理模式

### 1. 渐进式降级

```typescript
const loadPreferences = useCallback(() => {
  try {
    // 主要逻辑
    const storage = getLocalStorage();
    const stored = storage.getItem(STORAGE_KEYS.PREFERENCES);
    if (stored) {
      const parsedPreferences = JSON.parse(stored);
      setPreferences({ ...DEFAULT_PREFERENCES, ...parsedPreferences });
    }
  } catch (error) {
    console.error('加载用户偏好失败:', error);
    // 降级到默认设置
    setPreferences(DEFAULT_PREFERENCES);
    // 可选：显示用户友好的错误消息
    showMessage('error', '加载用户偏好失败，使用默认设置');
  } finally {
    setIsLoading(false);
  }
}, []);
```

### 2. 状态恢复机制

```typescript
const savePreferencesWithBackup = useCallback(async (preferences: UserPreferencesType) => {
  try {
    // 主要保存
    await saveToLocalStorage(preferences);
  } catch (error) {
    console.error('Primary save failed:', error);
    try {
      // 备份方案
      await saveToSessionStorage(preferences);
      showMessage('warning', '设置已临时保存');
    } catch (backupError) {
      console.error('Backup save also failed:', backupError);
      showMessage('error', '无法保存设置');
    }
  }
}, []);
```

## 类型安全

### 1. TypeScript接口定义

```typescript
interface UserPreferencesType {
  defaultParameters: StrategyParameters;
  favoritePresets: string[];
  autoSave: boolean;
  showAdvanced: boolean;
  chartPreferences: ChartPreferences;
}

interface ChartPreferences {
  showGrid: boolean;
  showVolume: boolean;
  animationDuration: number;
  colorScheme: 'light' | 'dark' | 'auto';
}

interface PreferencesState {
  preferences: UserPreferencesType;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
}
```

### 2. 类型安全的更新操作

```typescript
// ✅ 使用类型安全的更新函数
const updateChartPreferences = useCallback((
  updates: Partial<ChartPreferences>
) => {
  setPreferences(prev => ({
    ...prev,
    chartPreferences: {
      ...prev.chartPreferences,
      ...updates
    }
  }));
}, []);

// ✅ 使用类型验证
const validatePreferences = (preferences: any): preferences is UserPreferencesType => {
  return (
    preferences &&
    typeof preferences === 'object' &&
    'defaultParameters' in preferences &&
    'chartPreferences' in preferences &&
    typeof preferences.autoSave === 'boolean'
  );
};
```

## 状态管理最佳实践清单

### ✅ 推荐实践

1. **状态分层**：组件级 → 功能级 → 应用级
2. **本地状态优先**：优先使用React内置状态管理
3. **正确依赖管理**：useEffect依赖数组包含所有使用的变量
4. **不可变更新**：始终返回新的状态对象，不修改现有状态
5. **错误处理**：包装状态操作在try-catch中，提供优雅降级
6. **性能优化**：使用useMemo、useCallback、React.memo
7. **类型安全**：完整的TypeScript类型定义
8. **测试覆盖**：单元测试覆盖率90%+，包含边界条件

### ❌ 避免实践

1. **过度抽象**：为简单的组件状态引入复杂的状态管理
2. **状态泄漏**：在组件间不当地共享状态
3. **竞态条件**：并发状态更新导致的不一致
4. **内存泄漏**：未清理的订阅、定时器、事件监听器
5. **深层嵌套**：过深的状态结构导致更新困难
6. **直接修改**：直接修改状态对象而不是创建新对象
7. **忽略类型**：使用`any`类型绕过TypeScript检查

## 参考实现

### 完整的状态管理组件示例

参考 `src/components/controls/UserPreferences.tsx` 中的实现，该组件展示了：

- ✅ localStorage包装模式的实际应用
- ✅ 状态同步和持久化
- ✅ 错误处理和用户反馈
- ✅ 防抖优化
- ✅ TypeScript类型安全
- ✅ 测试友好的设计

### 测试示例

参考 `src/components/controls/__tests__/UserPreferences.test.tsx` 中的测试，包括：

- ✅ localStorage Mock的完整实现
- ✅ 复杂交互场景测试
- ✅ 边界条件和错误处理测试
- ✅ 性能和异步操作测试

---

**文档版本:** 1.0
**最后更新:** 2025-11-25
**维护者:** 开发团队
**适用范围:** 所有React组件和状态管理实现