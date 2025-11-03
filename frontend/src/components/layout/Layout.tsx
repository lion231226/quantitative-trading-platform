'use client';

import { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const router = useRouter();

  const handleHomeClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Layout: Navigating to home...');
    window.location.href = '/';
  };

  const handleStrategyClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Layout: Navigating to strategy...');
    window.location.href = '/strategy';
  };

  const handleHelpClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Layout: Navigating to help...');
    window.location.href = '/help';
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <div className="mr-4 hidden md:flex">
            <div
              onClick={handleHomeClick}
              className="mr-6 flex items-center space-x-2 cursor-pointer"
            >
              <span className="hidden font-bold sm:inline-block">
                量化交易策略分析平台
              </span>
            </div>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <button
                onClick={handleHomeClick}
                className="transition-colors hover:text-foreground/80 text-foreground bg-transparent border-none cursor-pointer text-sm font-medium"
              >
                首页
              </button>
              <button
                onClick={handleStrategyClick}
                className="transition-colors hover:text-foreground/80 text-foreground/60 bg-transparent border-none cursor-pointer text-sm font-medium"
              >
                策略分析
              </button>
              <button
                onClick={handleHelpClick}
                className="transition-colors hover:text-foreground/80 text-foreground/60 bg-transparent border-none cursor-pointer text-sm font-medium"
              >
                帮助
              </button>
            </nav>
          </div>
          <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
            <div className="w-full flex-1 md:w-auto md:flex-none">
              {/* 搜索或工具栏可以放在这里 */}
            </div>
            <nav className="flex items-center">
              <Button variant="outline" size="sm" onClick={handleStrategyClick}>
                开始分析
              </Button>
            </nav>
          </div>
        </div>
      </header>
      <main className="flex-1">
        {children}
      </main>
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <div className="flex flex-col items-center gap-4 px-8 md:flex-row md:gap-2 md:px-0">
            <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
              Built with Next.js, FastAPI, and Tailwind CSS.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
