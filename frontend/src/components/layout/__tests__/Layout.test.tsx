import { render, screen } from '@testing-library/react';
import { Layout } from '../Layout';

describe('Layout Component', () => {
  it('renders header with navigation', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
    );

    expect(screen.getByText('量化交易策略分析平台')).toBeInTheDocument();
    expect(screen.getByText('首页')).toBeInTheDocument();
    expect(screen.getByText('策略分析')).toBeInTheDocument();
    expect(screen.getByText('帮助')).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <Layout>
        <div data-testid="test-content">Test Content</div>
      </Layout>,
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders footer', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
    );

    expect(screen.getByText(/Built with Next.js, FastAPI, and Tailwind CSS/)).toBeInTheDocument();
  });

  it('navigation elements are clickable buttons', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
    );

    expect(screen.getByText('首页').closest('button')).toBeInTheDocument();
    expect(screen.getByText('策略分析').closest('button')).toBeInTheDocument();
    expect(screen.getByText('帮助').closest('button')).toBeInTheDocument();
  });

  it('start analysis button is clickable', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
    );

    const startButton = screen.getByText('开始分析');
    expect(startButton.closest('button')).toBeInTheDocument();
  });
});
