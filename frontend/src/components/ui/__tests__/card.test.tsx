import React from 'react';
import { render, screen } from '@testing-library/react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../card';

describe('Card Components', () => {
  it('renders Card correctly', () => {
    render(
      <Card data-testid="card">
        <p>Card content</p>
      </Card>,
    );

    const card = screen.getByTestId('card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveClass('rounded-lg', 'border', 'bg-card', 'shadow-sm');
  });

  it('renders CardHeader correctly', () => {
    render(
      <CardHeader>
        <CardTitle>Test Title</CardTitle>
        <CardDescription>Test Description</CardDescription>
      </CardHeader>,
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('renders CardTitle with correct heading level', () => {
    render(<CardTitle>Test Title</CardTitle>);

    const title = screen.getByText('Test Title');
    expect(title.tagName).toBe('H3');
    expect(title).toHaveClass('text-2xl', 'font-semibold');
  });

  it('renders CardDescription with correct styling', () => {
    render(<CardDescription>Test Description</CardDescription>);

    const description = screen.getByText('Test Description');
    expect(description.tagName).toBe('P');
    expect(description).toHaveClass('text-sm', 'text-muted-foreground');
  });

  it('renders CardContent correctly', () => {
    render(
      <CardContent>
        <p>Content here</p>
      </CardContent>,
    );

    const content = screen.getByText('Content here');
    expect(content).toBeInTheDocument();
  });

  it('renders CardFooter correctly', () => {
    render(
      <CardFooter>
        <button>Footer Button</button>
      </CardFooter>,
    );

    const button = screen.getByRole('button', { name: /footer button/i });
    expect(button).toBeInTheDocument();
  });

  it('renders complete Card structure', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card Description</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main content goes here</p>
        </CardContent>
        <CardFooter>
          <button>Action</button>
        </CardFooter>
      </Card>,
    );

    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card Description')).toBeInTheDocument();
    expect(screen.getByText('Main content goes here')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument();
  });
});
