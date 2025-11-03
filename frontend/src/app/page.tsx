'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  const handleStrategyClick = () => {
    console.log('Navigating to strategy...');
    router.push('/strategy');
  };

  const handleHelpClick = () => {
    console.log('Navigating to help...');
    router.push('/help');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
  
      <main className="flex-1">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              量化交易策略分析平台
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              通过直观的界面和详细的教程，快速掌握量化交易策略的核心概念
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="w-full sm:w-auto" onClick={handleStrategyClick}>
                开始策略分析
              </Button>
              <Button variant="outline" size="lg" className="w-full sm:w-auto" onClick={handleHelpClick}>
                查看帮助
              </Button>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-16">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  📊 实时数据分析
                </CardTitle>
                <CardDescription>
                  基于AKShare获取真实期货市场数据
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  支持能源、金属、农产品、化工等多个版块的期货品种分析
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  📈 策略回测
                </CardTitle>
                <CardDescription>
                  量化交易策略历史表现分析
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  计算关键指标：总收益率、最大回撤、夏普比率、胜率等
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🎓 教育导向
                </CardTitle>
                <CardDescription>
                  交互式学习体验
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  详细的概念解释和逐步指导，适合量化交易初学者
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900 mb-8">
              核心特性
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-3xl mb-2">⚡</div>
                <h3 className="font-semibold mb-2">快速响应</h3>
                <p className="text-sm text-gray-600">
                  API响应时间 &lt; 500ms
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🔒</div>
                <h3 className="font-semibold mb-2">类型安全</h3>
                <p className="text-sm text-gray-600">
                  端到端TypeScript支持
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">📱</div>
                <h3 className="font-semibold mb-2">响应式设计</h3>
                <p className="text-sm text-gray-600">
                  支持桌面和移动设备
                </p>
              </div>
              <div className="text-center">
                <div className="text-3xl mb-2">🎯</div>
                <h3 className="font-semibold mb-2">易于学习</h3>
                <p className="text-sm text-gray-600">
                  30分钟掌握核心概念
                </p>
              </div>
            </div>
          </div>
        </div>
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