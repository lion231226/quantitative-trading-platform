'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function HelpPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            帮助中心
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            了解如何使用量化交易策略分析平台，掌握单均线交易策略的核心概念
          </p>
          <div className="mt-6">
            <Link href="/">
              <Button variant="outline">
                返回首页
              </Button>
            </Link>
          </div>
        </div>

        {/* 快速导航 */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                🚀 新手入门
              </CardTitle>
              <CardDescription>
                30分钟掌握平台使用
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>• 了解单均线策略原理</li>
                <li>• 选择合适的期货品种</li>
                <li>• 配置策略参数</li>
                <li>• 解读回测结果</li>
              </ul>
              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => document.getElementById('tutorial-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                查看新手教程
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                📚 使用指南
              </CardTitle>
              <CardDescription>
                详细的功能说明
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>• 市场数据选择</li>
                <li>• 策略参数配置</li>
                <li>• 结果分析技巧</li>
                <li>• 最佳实践建议</li>
              </ul>
              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => document.getElementById('guide-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                查看使用指南
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                ❓ 常见问题
              </CardTitle>
              <CardDescription>
                解答使用中的疑问
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li>• 数据来源和准确性</li>
                <li>• 参数选择建议</li>
                <li>• 结果解读方法</li>
                <li>• 技术支持联系方式</li>
              </ul>
              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => document.getElementById('faq-section')?.scrollIntoView({ behavior: 'smooth' })}
              >
                查看常见问题
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* 新手教程 */}
        <Card className="mb-8" id="tutorial-section">
          <CardHeader>
            <CardTitle>🚀 新手教程</CardTitle>
            <CardDescription>
              跟随以下步骤，快速掌握量化交易策略分析
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    1
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">了解单均线策略</h3>
                    <p className="text-sm text-gray-600">
                      单均线策略是最基础的技术分析策略，通过比较价格与移动平均线的关系来判断买卖时机。
                      当价格上穿均线时买入，下穿均线时卖出。
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    2
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">选择期货品种</h3>
                    <p className="text-sm text-gray-600">
                      从期货品种选择器中选择您感兴趣的品种。建议新手从流动性好、波动适中的品种开始，
                      如螺纹钢、热卷等黑色系品种。
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    3
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">设置日期范围</h3>
                    <p className="text-sm text-gray-600">
                      选择合适的回测时间范围。建议选择至少6个月的历史数据，
                      这样能够包含不同市场环境，使回测结果更有参考价值。
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    4
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">配置策略参数</h3>
                    <p className="text-sm text-gray-600">
                      调整均线周期和初始资金。短期均线(5-20天)对价格变化更敏感，
                      长期均线(50-200天)更稳定。新手建议从20天均线开始。
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    5
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">运行策略回测</h3>
                    <p className="text-sm text-gray-600">
                      点击&ldquo;开始分析&rdquo;按钮，系统将自动执行策略回测。
                      根据数据量的不同，回测可能需要几分钟时间。
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
                    6
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">分析回测结果</h3>
                    <p className="text-sm text-gray-600">
                      查看收益率、胜率、最大回撤等关键指标。重点关注夏普比率，
                      该指标反映了风险调整后的收益水平，数值越高表示策略质量越好。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 使用指南 */}
        <Card className="mb-8" id="guide-section">
          <CardHeader>
            <CardTitle>📚 使用指南</CardTitle>
            <CardDescription>
              详细的功能说明和最佳实践
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h3 className="font-semibold mb-3">期货品种选择</h3>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-medium mb-2">推荐品种（适合新手）</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• 螺纹钢(RB)：流动性好，趋势性强</li>
                    <li>• 热卷(HC)：与螺纹钢相关性高</li>
                    <li>• 铁矿石(I)：波动适中，数据质量好</li>
                    <li>• 焦炭(J)：黑色系重要品种</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">选择建议</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• 选择日成交量较大的品种</li>
                    <li>• 避免价格过于活跃的品种</li>
                    <li>• 关注品种的基本面情况</li>
                    <li>• 建议从主力合约开始分析</li>
                  </ul>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-3">参数配置指南</h3>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-medium mb-2">均线周期选择</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• 短期(5-10天)：适合短线交易</li>
                    <li>• 中期(20-60天)：平衡风险收益</li>
                    <li>• 长期(120-200天)：趋势跟踪策略</li>
                    <li>• 建议：根据交易周期选择合适周期</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">初始资金设置</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• 小额(1-5万)：适合学习测试</li>
                    <li>• 中额(10-50万)：模拟实盘交易</li>
                    <li>• 大额(100万+)：机构资金管理</li>
                    <li>• 注意：资金规模影响交易成本</li>
                  </ul>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-3">结果解读技巧</h3>
              <div className="text-sm space-y-2 text-gray-600">
                <p><strong>总收益率：</strong>策略的整体收益表现，需要结合风险指标一起评估。</p>
                <p><strong>胜率：</strong>盈利交易的比例。高胜率不一定代表好策略，还需看盈亏比。</p>
                <p><strong>最大回撤：</strong>策略从峰值到谷值的最大跌幅，是重要的风险指标。</p>
                <p><strong>夏普比率：</strong>风险调整后的收益指标，&gt;1表示良好，&gt;2表示优秀。</p>
                <p><strong>波动率：</strong>收益的波动程度，低波动率通常意味着更稳定的收益。</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 常见问题 */}
        <Card id="faq-section">
          <CardHeader>
            <CardTitle>❓ 常见问题</CardTitle>
            <CardDescription>
              解答使用过程中的常见疑问
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Q: 数据来源是什么？准确性如何？</h3>
                <p className="text-sm text-gray-600">
                  A: 我们使用AKShare作为数据源，这是国内知名的金融数据接口。数据来源于交易所官方发布，
                  经过严格的清洗和处理，确保准确性。但历史数据可能存在少量缺失或错误，
                  建议在实际使用前进行数据验证。
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Q: 为什么某些品种的数据加载失败？</h3>
                <p className="text-sm text-gray-600">
                  A: 可能的原因包括：1) 品种已退市或暂停交易；2) 数据源临时故障；
                  3) 网络连接问题。建议稍后重试，或选择其他活跃品种进行分析。
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Q: 回测结果能代表未来表现吗？</h3>
                <p className="text-sm text-gray-600">
                  A: 历史回测结果仅供参考，不能保证未来表现。市场环境会发生变化，
                  建议结合多个时间段的回测结果，并考虑实盘交易中的滑点、手续费等成本因素。
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Q: 如何选择最佳的均线周期？</h3>
                <p className="text-sm text-gray-600">
                  A: 最佳周期因品种和市场环境而异。建议：1) 测试多个周期组合；
                  2) 考虑品种的历史波动特性；3) 结合自己的交易风格；
                  4) 定期重新评估和调整参数。
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Q: 策略运行失败怎么办？</h3>
                <p className="text-sm text-gray-600">
                  A: 首先检查网络连接，然后确认：1) 选择的品种在指定时间段内有数据；
                  2) 日期范围设置合理；3) 参数在有效范围内。如果问题持续，
                  请尝试刷新页面或联系技术支持。
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 返回顶部按钮 */}
        <div className="text-center mt-8">
          <Button
            variant="outline"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="px-6"
          >
            ↑ 返回顶部
          </Button>
        </div>
      </div>
    </main>
  );
}
