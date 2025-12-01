import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TutorialAnimationDemo } from './TutorialAnimationDemo';
import { InteractiveGlossary } from './InteractiveGlossary';
import { MarketDataCaseStudy } from './MarketDataCaseStudy';
import { ParameterImpactComparison } from './ParameterImpactComparison';
import {
  BarChart3,
  BookOpen,
  Calculator,
  PlayCircle,
  Settings,
  Star,
  Target,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';

/**
 * 教程系统演示组件
 * 展示交互式教程系统的所有功能模块
 */
export function TutorialDemo() {
  const [activeModule, setActiveModule] = useState('overview');

  // 模拟教程系统数据
  const stats = {
    totalTutorials: 12,
    completedUsers: 1500,
    averageRating: 4.8,
    completionRate: 85,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <BookOpen className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  量化交易交互式教程系统
                </h1>
                <p className="text-sm text-gray-500">Story 2.4 实现演示</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="text-green-600">
                核心功能已完成
              </Badge>
              <Badge variant="default">v1.0.0</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs
          value={activeModule}
          onValueChange={setActiveModule}
          className="w-full"
        >
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">功能概览</TabsTrigger>
            <TabsTrigger value="animation">动画演示</TabsTrigger>
            <TabsTrigger value="glossary">术语库</TabsTrigger>
            <TabsTrigger value="cases">案例分析</TabsTrigger>
            <TabsTrigger value="parameters">参数对比</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-8">
            {/* 系统介绍 */}
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                交互式教程系统
              </h2>
              <p className="text-xl text-gray-600 mb-6">
                为量化交易初学者设计的沉浸式学习体验
              </p>
              <div className="flex justify-center space-x-8">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {stats.totalTutorials}
                  </div>
                  <div className="text-sm text-gray-500">教程数量</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">
                    {stats.completedUsers}
                  </div>
                  <div className="text-sm text-gray-500">完成用户</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-600">
                    {stats.averageRating}
                  </div>
                  <div className="text-sm text-gray-500">用户评分</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-orange-600">
                    {stats.completionRate}%
                  </div>
                  <div className="text-sm text-gray-500">完成率</div>
                </div>
              </div>
            </div>

            {/* 功能模块展示 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
              <Card
                className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => setActiveModule('animation')}
              >
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <PlayCircle className="h-6 w-6 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">动画演示系统</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  Chart.js驱动的策略动画，直观展示金叉死叉和移动平均线计算过程
                </p>
                <div className="flex items-center justify-between">
                  <Badge variant="outline">AC 2</Badge>
                  <Star className="h-4 w-4 text-yellow-500" />
                </div>
              </Card>

              <Card
                className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => setActiveModule('glossary')}
              >
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <BookOpen className="h-6 w-6 text-green-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">交互式术语库</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  丰富的量化交易术语库，支持搜索、收藏和关联学习
                </p>
                <div className="flex items-center justify-between">
                  <Badge variant="outline">AC 3</Badge>
                  <Users className="h-4 w-4 text-green-500" />
                </div>
              </Card>

              <Card
                className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => setActiveModule('cases')}
              >
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                    <BarChart3 className="h-6 w-6 text-purple-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">市场数据案例</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  基于真实历史数据的策略案例分析，验证策略有效性
                </p>
                <div className="flex items-center justify-between">
                  <Badge variant="outline">AC 3</Badge>
                  <TrendingUp className="h-4 w-4 text-purple-500" />
                </div>
              </Card>

              <Card
                className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => setActiveModule('parameters')}
              >
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                    <Settings className="h-6 w-6 text-orange-600" />
                  </div>
                  <h3 className="font-semibold text-gray-900">参数影响对比</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  实时调整策略参数，观察对性能指标的影响和优化建议
                </p>
                <div className="flex items-center justify-between">
                  <Badge variant="outline">AC 3</Badge>
                  <Calculator className="h-4 w-4 text-orange-500" />
                </div>
              </Card>
            </div>

            {/* 验收标准完成情况 */}
            <Card className="p-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                验收标准完成情况
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Target className="h-5 w-5 text-green-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">
                        AC 1: 分步骤交互式教程
                      </h4>
                      <p className="text-sm text-gray-600">
                        线性流程导航、前进/后退按钮、步骤跳过功能和完成状态反馈
                      </p>
                    </div>
                  </div>
                  <Badge variant="default" className="bg-green-600">
                    已完成
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Zap className="h-5 w-5 text-green-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">
                        AC 2: 策略原理动画演示
                      </h4>
                      <p className="text-sm text-gray-600">
                        金叉死叉可视化、移动平均线计算过程展示、交易信号生成动画和速度控制
                      </p>
                    </div>
                  </div>
                  <Badge variant="default" className="bg-green-600">
                    已完成
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <BookOpen className="h-5 w-5 text-green-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">
                        AC 3: 概念解释和示例展示
                      </h4>
                      <p className="text-sm text-gray-600">
                        交互式术语库、真实市场数据案例分析、参数影响实时演示和最佳实践指导
                      </p>
                    </div>
                  </div>
                  <Badge variant="default" className="bg-green-600">
                    已完成
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <BarChart3 className="h-5 w-5 text-blue-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">
                        AC 4: 学习进度跟踪
                      </h4>
                      <p className="text-sm text-gray-600">
                        记录完成度和学习时间，支持进度可视化、断点续学和学习成就系统
                      </p>
                    </div>
                  </div>
                  <Badge variant="default" className="bg-blue-600">
                    已完成
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Users className="h-5 w-5 text-gray-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">
                        AC 5: 上下文帮助系统
                      </h4>
                      <p className="text-sm text-gray-600">
                        嵌入式帮助提示、智能推荐、搜索功能和FAQ链接
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">待实现</Badge>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="animation">
            <TutorialAnimationDemo />
          </TabsContent>

          <TabsContent value="glossary">
            <InteractiveGlossary />
          </TabsContent>

          <TabsContent value="cases">
            <MarketDataCaseStudy />
          </TabsContent>

          <TabsContent value="parameters">
            <ParameterImpactComparison />
          </TabsContent>
        </Tabs>
      </div>

      {/* 底部信息 */}
      <div className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-500">
            <p>量化交易策略分析平台 - 交互式教程系统</p>
            <p className="mt-2">
              Story 2.4 实现 | 基于React + Chart.js + TypeScript
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
