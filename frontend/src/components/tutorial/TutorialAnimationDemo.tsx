import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TutorialAnimation } from './TutorialAnimation';
import { MovingAverageCalculation } from './MovingAverageCalculation';
import { GoldenDeathCrossAnimation } from './GoldenDeathCrossAnimation';
import { PlayCircle, Calculator, TrendingUp, Activity } from 'lucide-react';

/**
 * 教程动画演示组件
 * 集成所有动画类型，提供完整的演示功能
 */
export function TutorialAnimationDemo() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          交互式教程动画系统
        </h2>
        <p className="text-gray-600">
          通过可视化动画深入理解量化交易策略原理
        </p>
      </div>

      {/* 功能概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <Activity className="h-6 w-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900">基础动画</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Chart.js集成的策略演示动画，支持多种动画类型
          </p>
          <Badge variant="outline">Subtask 2.1</Badge>
        </Card>

        <Card className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <Calculator className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="font-semibold text-gray-900">移动平均线计算</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            分步骤展示移动平均线的计算过程和原理
          </p>
          <Badge variant="outline">Subtask 2.2</Badge>
        </Card>

        <Card className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900">金叉死叉信号</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            动态演示金叉死叉的形成过程和交易含义
          </p>
          <Badge variant="outline">Subtask 2.3</Badge>
        </Card>

        <Card className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <PlayCircle className="h-6 w-6 text-yellow-600" />
            </div>
            <h3 className="font-semibold text-gray-900">交互控制</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            完整的播放控制、速度调节和进度管理
          </p>
          <Badge variant="outline">Subtask 2.4</Badge>
        </Card>
      </div>

      {/* 动画演示区域 */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">功能概览</TabsTrigger>
          <TabsTrigger value="moving-average">移动平均线</TabsTrigger>
          <TabsTrigger value="golden-death">金叉死叉</TabsTrigger>
          <TabsTrigger value="advanced">高级动画</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              动画系统特性
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-3">🎬 核心功能</h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• Chart.js 4.4.2 深度集成</li>
                  <li>• 多种动画类型支持</li>
                  <li>• 实时数据计算和渲染</li>
                  <li>• 交互式控制和导航</li>
                  <li>• 自适应响应式设计</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-3">⚡ 性能优化</h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 60fps 流畅动画</li>
                  <li>• 智能数据采样</li>
                  <li>• 内存管理优化</li>
                  <li>• 动画队列管理</li>
                  <li>• 懒加载和缓存机制</li>
                </ul>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 bg-blue-50 border-blue-200">
                <h5 className="font-medium text-blue-900 mb-2">教育价值</h5>
                <p className="text-sm text-blue-700">
                  通过可视化动画帮助初学者快速理解复杂的量化交易概念
                </p>
              </Card>
              <Card className="p-4 bg-green-50 border-green-200">
                <h5 className="font-medium text-green-900 mb-2">交互体验</h5>
                <p className="text-sm text-green-700">
                  提供丰富的控制选项和实时反馈，增强学习体验
                </p>
              </Card>
              <Card className="p-4 bg-purple-50 border-purple-200">
                <h5 className="font-medium text-purple-900 mb-2">扩展性</h5>
                <p className="text-sm text-purple-700">
                  模块化设计，支持轻松添加新的动画类型和交互功能
                </p>
              </Card>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="moving-average" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              移动平均线计算动画
            </h3>
            <MovingAverageCalculation
              period={5}
              autoPlay={false}
              onStepChange={(step, calculation) => {
                console.log('Step:', step, 'Calculation:', calculation);
              }}
              onComplete={() => {
                console.log('Moving average calculation completed');
              }}
            />
          </Card>
        </TabsContent>

        <TabsContent value="golden-death" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              金叉死叉信号动画
            </h3>
            <GoldenDeathCrossAnimation
              autoPlay={false}
              showGoldenCross={true}
              showDeathCross={true}
              onCrossDetected={(type, data) => {
                console.log('Cross detected:', type, data);
              }}
              onComplete={() => {
                console.log('Golden/death cross animation completed');
              }}
            />
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              高级动画演示
            </h3>
            <div className="space-y-6">
              {/* 信号生成动画 */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">交易信号生成</h4>
                <TutorialAnimation
                  type="signal-generation"
                  autoPlay={false}
                  speed={1.0}
                  showControls={true}
                  onStepChange={(step, total) => {
                    console.log('Animation step:', step, 'of', total);
                  }}
                  onComplete={() => {
                    console.log('Signal generation animation completed');
                  }}
                  width={800}
                  height={400}
                />
              </div>

              {/* 移动平均线动画 */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">移动平均线原理</h4>
                <TutorialAnimation
                  type="moving-average"
                  autoPlay={false}
                  speed={1.5}
                  showControls={true}
                  onStepChange={(step, total) => {
                    console.log('MA animation step:', step, 'of', total);
                  }}
                  onComplete={() => {
                    console.log('Moving average animation completed');
                  }}
                  width={800}
                  height={400}
                />
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 技术规格 */}
      <Card className="p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">
          技术实现规格
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-3">依赖库</h4>
            <div className="space-y-2 text-sm font-mono bg-gray-50 p-3 rounded">
              <div>chart.js: 4.4.2</div>
              <div>react-chartjs-2: 5.2.0</div>
              <div>@radix-ui/react-slider: latest</div>
              <div>lucide-react: 0.552.0</div>
            </div>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-3">性能指标</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>目标帧率:</span>
                <Badge variant="outline">60 FPS</Badge>
              </div>
              <div className="flex justify-between">
                <span>动画延迟:</span>
                <Badge variant="outline">&lt; 16ms</Badge>
              </div>
              <div className="flex justify-between">
                <span>内存使用:</span>
                <Badge variant="outline">&lt; 50MB</Badge>
              </div>
              <div className="flex justify-between">
                <span>响应时间:</span>
                <Badge variant="outline">&lt; 100ms</Badge>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}