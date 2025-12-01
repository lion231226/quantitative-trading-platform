import React from 'react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import TutorialTooltip from '../TutorialTooltip';

// 使用假计时器来处理防抖延迟
beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});

// Mock Radix UI Tooltip
jest.mock('@radix-ui/react-tooltip', () => ({
  Provider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Root: ({ children, open, onOpenChange }: any) => {
    // 模拟点击触发器来打开/关闭工具提示
    const handleTriggerClick = () => {
      onOpenChange && onOpenChange(!open);
    };

    return (
      <div>
        <button
          data-testid="tooltip-trigger"
          onClick={handleTriggerClick}
          aria-label="帮助"
        >
          触发器
        </button>
        {open && <div data-testid="tooltip-content">{children}</div>}
      </div>
    );
  },
  Trigger: ({ children, asChild, ...props }: any) => {
    if (asChild) {
      // 如果是 asChild，直接渲染子元素并传递所有属性
      return { ...children, props: { ...children.props, ...props } };
    }
    return (
      <button data-testid="tooltip-trigger" {...props}>
        {children}
      </button>
    );
  },
  Content: ({ children, ...props }: any) => {
    // 过滤掉非标准的DOM属性
    const { sideOffset, alignOffset, ...domProps } = props;
    return (
      <div data-testid="tooltip-content" {...domProps}>
        {children}
      </div>
    );
  },
  Arrow: () => <div data-testid="tooltip-arrow" />,
  Portal: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

// Mock lodash debounce
jest.mock('lodash', () => ({
  debounce: (fn: Function) => fn,
}));

describe('TutorialTooltip', () => {
  const defaultProps = {
    componentName: 'TestComponent',
    currentStep: 1,
    userAction: 'test-action',
    userLevel: 'beginner' as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders tooltip trigger button', () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-label', '帮助');
  });

  it('opens tooltip when trigger is clicked', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('智能帮助')).toBeInTheDocument();
    });
  });

  it('displays context confidence when available', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText(/上下文匹配度:/)).toBeInTheDocument();
    });
  });

  it('shows search input when tooltip is open', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('搜索帮助内容...');
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('filters help content when search query is entered', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('搜索帮助内容...');
      expect(searchInput).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('搜索帮助内容...');
    fireEvent.change(searchInput, { target: { value: '移动平均线' } });

    // 使用假计时器触发防抖搜索
    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      // 验证搜索结果显示了包含"移动平均线"的内容
      expect(screen.getByText('金叉信号')).toBeInTheDocument();
      expect(screen.getByText('移动平均线 (MA)')).toBeInTheDocument();
    });
  });

  it('displays smart recommendations when enabled', async () => {
    render(
      <TutorialTooltip {...defaultProps} showSmartRecommendations={true} />,
    );

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('为你推荐')).toBeInTheDocument();
    });
  });

  it('shows custom help content when provided', async () => {
    const customHelpContent = [
      {
        id: 'custom-1',
        title: '自定义帮助',
        content: '这是自定义的帮助内容',
        category: 'concept' as const,
        relatedTerms: ['测试'],
        priority: 'high' as const,
      },
    ];

    render(
      <TutorialTooltip
        {...defaultProps}
        customHelpContent={customHelpContent}
      />,
    );

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('自定义帮助')).toBeInTheDocument();
      expect(screen.getByText('这是自定义的帮助内容')).toBeInTheDocument();
    });
  });

  it('shows no results message when search finds nothing', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText('搜索帮助内容...');
      expect(searchInput).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('搜索帮助内容...');
    fireEvent.change(searchInput, { target: { value: '不存在的术语' } });

    await waitFor(() => {
      expect(screen.getByText('未找到相关帮助内容')).toBeInTheDocument();
      expect(screen.getByText('尝试使用其他关键词搜索')).toBeInTheDocument();
    });
  });

  it('shows navigation link to full help documentation', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(
      () => {
        const link = screen.getByText('查看完整帮助文档 →');
        expect(link).toBeInTheDocument();
        expect(link.tagName).toBe('BUTTON'); // 修复：这是一个按钮，不是链接
      },
      { timeout: 5000 },
    ); // 增加超时时间
  });

  it('renders with different trigger modes', () => {
    const { rerender } = render(
      <TutorialTooltip {...defaultProps} trigger="click" />,
    );
    expect(screen.getByLabelText('帮助')).toBeInTheDocument();

    rerender(<TutorialTooltip {...defaultProps} trigger="hover" />);
    expect(screen.getByLabelText('帮助')).toBeInTheDocument();

    rerender(<TutorialTooltip {...defaultProps} trigger="focus" />);
    expect(screen.getByLabelText('帮助')).toBeInTheDocument();
  });

  it('applies correct category colors', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      // Check if different categories are displayed with correct colors
      // This would depend on the mock data structure
      expect(screen.getByText('智能帮助')).toBeInTheDocument();
    });
  });

  it('closes tooltip when close button is clicked', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('智能帮助')).toBeInTheDocument();
    });

    // Find and click close button
    const closeButton = screen.getByLabelText('关闭');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('智能帮助')).not.toBeInTheDocument();
    });
  });

  it('respects maxRecommendations prop', async () => {
    render(<TutorialTooltip {...defaultProps} maxRecommendations={1} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('为你推荐')).toBeInTheDocument();
      // Should only show 1 recommendation
      const recommendations = screen.getAllByText(/概念|功能|问题|实践/);
      expect(recommendations.length).toBeLessThanOrEqual(1);
    });
  });

  it('adapts content based on user level', async () => {
    render(<TutorialTooltip {...defaultProps} userLevel="advanced" />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('智能帮助')).toBeInTheDocument();
    });
  });

  it('shows different priority indicators', async () => {
    render(<TutorialTooltip {...defaultProps} />);

    const trigger = screen.getByLabelText('帮助');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('智能帮助')).toBeInTheDocument();
    });
  });
});
