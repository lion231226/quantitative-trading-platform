'use client';

import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

export default function TestPage() {
  const router = useRouter();

  const handleStrategyClick = () => {
    console.log('Test: Navigating to strategy...');
    router.push('/strategy');
  };

  const handleHelpClick = () => {
    console.log('Test: Navigating to help...');
    router.push('/help');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">测试页面</h1>

      <div className="space-y-4">
        <p className="text-lg text-gray-600">这是一个简单的测试页面，用于验证导航功能。</p>

        <div className="flex gap-4">
          <Button size="lg" onClick={handleStrategyClick}>
            开始策略分析
          </Button>
          <Button variant="outline" size="lg" onClick={handleHelpClick}>
            查看帮助
          </Button>
        </div>

        <p className="text-sm text-gray-500 mt-4">
          打开浏览器控制台查看点击日志。
        </p>
      </div>
    </div>
  );
}