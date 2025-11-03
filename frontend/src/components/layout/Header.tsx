import Link from 'next/link';
import { Button } from '@/components/ui/button';

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 hidden md:flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <span className="hidden font-bold sm:inline-block">
              量化交易策略分析平台
            </span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <Link
              href="/"
              className="transition-colors hover:text-foreground/80 text-foreground"
            >
              首页
            </Link>
            <Link
              href="/strategy"
              className="transition-colors hover:text-foreground/80 text-foreground/60"
            >
              策略分析
            </Link>
            <Link
              href="/help"
              className="transition-colors hover:text-foreground/80 text-foreground/60"
            >
              帮助
            </Link>
          </nav>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <div className="w-full flex-1 md:w-auto md:flex-none">
            {/* 搜索或工具栏可以放在这里 */}
          </div>
          <nav className="flex items-center">
            <Link href="/strategy">
              <Button variant="outline" size="sm">
                开始分析
              </Button>
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
