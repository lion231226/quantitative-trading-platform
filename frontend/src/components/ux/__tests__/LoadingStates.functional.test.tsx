import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { LazyLoad, Skeleton, VirtualList } from '../LoadingStates';

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock performance.now
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
  },
});

describe('Skeleton Component', () => {
  it('renders with default props', () => {
    render(<Skeleton />);
    const skeleton = screen.getByRole('status');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('renders with custom variant', () => {
    render(<Skeleton variant="circular" width={50} height={50} />);
    const skeleton = screen.getByRole('status');
    expect(skeleton).toHaveClass('rounded-full');
  });

  it('renders multiple lines for text variant', () => {
    render(<Skeleton variant="text" lines={3} />);
    const skeleton = screen.getByRole('status');
    expect(skeleton).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Skeleton className="custom-class" />);
    const skeleton = screen.getByRole('status');
    expect(skeleton).toHaveClass('custom-class');
  });
});

describe('LazyLoad Component', () => {
  it('renders fallback initially', () => {
    render(
      <LazyLoad fallback={<div>Fallback</div>}>
        <div>Content</div>
      </LazyLoad>,
    );

    expect(screen.getByText('Fallback')).toBeInTheDocument();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('renders content when trigger is true', () => {
    render(
      <LazyLoad trigger={true}>
        <div>Content</div>
      </LazyLoad>,
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('calls IntersectionObserver', () => {
    render(
      <LazyLoad>
        <div>Content</div>
      </LazyLoad>,
    );

    expect(mockIntersectionObserver).toHaveBeenCalled();
  });
});

describe('VirtualList Component', () => {
  const items = Array.from({ length: 1000 }, (_, i) => ({
    id: i,
    name: `Item ${i}`,
  }));

  const renderItem = (item: { id: number; name: string }) => (
    <div key={item.id}>{item.name}</div>
  );

  it('renders visible items only', () => {
    render(
      <VirtualList
        items={items}
        itemHeight={50}
        containerHeight={200}
        renderItem={renderItem}
      />,
    );

    // Should render a subset of items (overscan * 2 + visible)
    const renderedItems = screen.getAllByText(/Item \d+/);
    expect(renderedItems.length).toBeLessThan(20); // Much less than 1000
    expect(renderedItems.length).toBeGreaterThan(0);
  });

  it('handles scroll events', () => {
    const { container } = render(
      <VirtualList
        items={items}
        itemHeight={50}
        containerHeight={200}
        renderItem={renderItem}
      />,
    );

    const scrollContainer = container.querySelector('.overflow-auto');
    expect(scrollContainer).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <VirtualList
        items={items}
        itemHeight={50}
        containerHeight={200}
        renderItem={renderItem}
        className="custom-class"
      />,
    );

    const container = document.querySelector('.custom-class');
    expect(container).toBeInTheDocument();
  });
});
