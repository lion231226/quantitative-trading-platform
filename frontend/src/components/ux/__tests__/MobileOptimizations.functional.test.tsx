import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  MobileChartContainer,
  MobileContainer,
  MobileForm,
  MobileNavigation,
  MobileTable,
  ResponsiveLayout,
} from '../MobileOptimizations';

// Mock window properties (not defined in jest.setup.js)
Object.defineProperty(window, 'innerWidth', {
  writable: true,
  configurable: true,
  value: 1024,
});

Object.defineProperty(window, 'innerHeight', {
  writable: true,
  configurable: true,
  value: 768,
});

Object.defineProperty(screen, 'width', {
  writable: true,
  configurable: true,
  value: 1024,
});

Object.defineProperty(screen, 'height', {
  writable: true,
  configurable: true,
  value: 768,
});

Object.defineProperty(window, 'devicePixelRatio', {
  writable: true,
  configurable: true,
  value: 1,
});

Object.defineProperty(navigator, 'userAgent', {
  writable: true,
  configurable: true,
  value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
});

describe('MobileNavigation', () => {
  const navItems = [
    {
      id: 'home',
      label: '首页',
      icon: '🏠',
      onClick: jest.fn(),
      active: true,
    },
    {
      id: 'settings',
      label: '设置',
      icon: '⚙️',
      onClick: jest.fn(),
      active: false,
    },
  ];

  it('renders navigation items', () => {
    // Set mobile screen size
    (window as any).innerWidth = 500;

    render(<MobileNavigation items={navItems} />);

    expect(screen.getByText('首页')).toBeInTheDocument();
    expect(screen.getByText('设置')).toBeInTheDocument();
    expect(screen.getByText('🏠')).toBeInTheDocument();
    expect(screen.getByText('⚙️')).toBeInTheDocument();
  });

  it('does not render on desktop', () => {
    // Set desktop screen size
    (window as any).innerWidth = 1200;

    render(<MobileNavigation items={navItems} />);

    expect(screen.queryByText('首页')).not.toBeInTheDocument();
    expect(screen.queryByText('设置')).not.toBeInTheDocument();
  });

  it('calls onClick when item is clicked', () => {
    // Set mobile screen size
    (window as any).innerWidth = 500;

    render(<MobileNavigation items={navItems} />);

    fireEvent.click(screen.getByText('首页'));
    expect(navItems[0].onClick).toHaveBeenCalled();
  });

  it('shows menu button when more than 5 items', () => {
    const manyItems = Array.from({ length: 7 }, (_, i) => ({
      id: `item-${i}`,
      label: `Item ${i}`,
      onClick: jest.fn(),
      active: false,
    }));

    // Set mobile screen size
    (window as any).innerWidth = 500;

    render(<MobileNavigation items={manyItems} />);

    expect(screen.getByText('📋')).toBeInTheDocument();
  });
});

describe('MobileContainer', () => {
  it('renders children', () => {
    render(
      <MobileContainer>
        <div>Test Content</div>
      </MobileContainer>,
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <MobileContainer className="custom-class">
        <div>Test Content</div>
      </MobileContainer>,
    );

    const container = screen.getByText('Test Content').parentElement;
    expect(container).toHaveClass('custom-class');
  });
});

describe('MobileChartContainer', () => {
  it('renders title and description', () => {
    render(
      <MobileChartContainer title="Test Chart" description="Test Description">
        <div>Chart Content</div>
      </MobileChartContainer>,
    );

    expect(screen.getByText('Test Chart')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('Chart Content')).toBeInTheDocument();
  });

  it('renders actions', () => {
    render(
      <MobileChartContainer
        title="Test Chart"
        actions={<button>Action Button</button>}
      >
        <div>Chart Content</div>
      </MobileChartContainer>,
    );

    expect(screen.getByText('Action Button')).toBeInTheDocument();
  });
});

describe('MobileTable', () => {
  const testData = [
    { id: 1, name: 'John', age: 25, city: 'New York' },
    { id: 2, name: 'Jane', age: 30, city: 'London' },
  ];

  const columns = [
    { key: 'name', title: 'Name' },
    { key: 'age', title: 'Age' },
    { key: 'city', title: 'City' },
  ];

  it('renders table data', () => {
    render(<MobileTable data={testData} columns={columns} />);

    expect(screen.getByText('John')).toBeInTheDocument();
    expect(screen.getByText('Jane')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <MobileTable
        data={testData}
        columns={columns}
        className="custom-class"
      />,
    );

    const table = screen.getByText('John').closest('[class*="custom-class"]');
    expect(table).toBeInTheDocument();
  });
});

describe('MobileForm', () => {
  it('renders form children', () => {
    render(
      <MobileForm>
        <input placeholder="Test Input" />
        <button>Submit</button>
      </MobileForm>,
    );

    expect(screen.getByPlaceholderText('Test Input')).toBeInTheDocument();
    expect(screen.getByText('Submit')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <MobileForm className="custom-class">
        <div>Form Content</div>
      </MobileForm>,
    );

    const form = screen.getByText('Form Content').parentElement;
    expect(form).toHaveClass('custom-class');
  });
});

describe('ResponsiveLayout', () => {
  it('renders header, sidebar, and content', () => {
    render(
      <ResponsiveLayout header={<div>Header</div>} sidebar={<div>Sidebar</div>}>
        <div>Main Content</div>
      </ResponsiveLayout>,
    );

    expect(screen.getByText('Header')).toBeInTheDocument();
    expect(screen.getByText('Sidebar')).toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <ResponsiveLayout className="custom-class">
        <div>Content</div>
      </ResponsiveLayout>,
    );

    const layout = screen
      .getByText('Content')
      .closest('[class*="custom-class"]');
    expect(layout).toBeInTheDocument();
  });
});
