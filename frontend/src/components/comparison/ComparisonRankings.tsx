'use client';

import { useMemo, useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { VarietyRanking } from '@/types/comparison.types';
import { cn } from '@/lib/utils';
import { Award, Medal, Shield, Target, TrendingUp, Trophy } from 'lucide-react';

interface ComparisonRankingsProps {
  rankings: VarietyRanking[];
  className?: string;
}

type RankingType =
  | 'overall'
  | 'returns'
  | 'risk'
  | 'riskAdjusted'
  | 'consistency';

export function ComparisonRankings({
  rankings,
  className,
}: ComparisonRankingsProps) {
  const [selectedRanking, setSelectedRanking] =
    useState<RankingType>('overall');

  // 根据不同类型排序
  const sortedRankings = useMemo(() => {
    switch (selectedRanking) {
      case 'returns':
        return [...rankings].sort(
          (a, b) => a.metrics.returnRank - b.metrics.returnRank,
        );
      case 'risk':
        return [...rankings].sort(
          (a, b) => a.metrics.riskRank - b.metrics.riskRank,
        );
      case 'riskAdjusted':
        return [...rankings].sort(
          (a, b) =>
            a.metrics.riskAdjustedReturnRank - b.metrics.riskAdjustedReturnRank,
        );
      case 'consistency':
        return [...rankings].sort(
          (a, b) => a.metrics.consistencyRank - b.metrics.consistencyRank,
        );
      case 'overall':
      default:
        return [...rankings].sort((a, b) => a.rank - b.rank);
    }
  }, [rankings, selectedRanking]);

  // 获取排名图标
  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className="h-5 w-5 text-yellow-500" />;
      case 2:
        return <Medal className="h-5 w-5 text-gray-400" />;
      case 3:
        return <Award className="h-5 w-5 text-amber-600" />;
      default:
        return (
          <span className="h-5 w-5 flex items-center justify-center text-sm font-bold text-muted-foreground">
            {rank}
          </span>
        );
    }
  };

  // 获取排名徽章颜色
  const getRankBadgeColor = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 2:
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 3:
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  // 获取指标进度条颜色
  const getProgressColor = (rank: number, total: number) => {
    const percentage = ((total - rank + 1) / total) * 100;
    if (percentage >= 80) return 'bg-green-500';
    if (percentage >= 60) return 'bg-blue-500';
    if (percentage >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // 排名类型配置
  const rankingTypes = [
    { value: 'overall', label: '综合排名', icon: Trophy },
    { value: 'returns', label: '收益率排名', icon: TrendingUp },
    { value: 'risk', label: '风险控制排名', icon: Shield },
    { value: 'riskAdjusted', label: '风险调整收益排名', icon: Target },
    { value: 'consistency', label: '稳定性排名', icon: Target },
  ] as const;

  return (
    <div className={cn('space-y-6', className)}>
      <Card>
        <CardHeader>
          <CardTitle>排名分析</CardTitle>
          <CardDescription>
            基于多个维度的品种排名分析，帮助您找到最优投资品种
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={selectedRanking}
            onValueChange={(value) => setSelectedRanking(value as RankingType)}
          >
            <TabsList className="grid w-full grid-cols-2 md:grid-cols-5">
              {rankingTypes.map((type) => {
                const Icon = type.icon;
                return (
                  <TabsTrigger
                    key={type.value}
                    value={type.value}
                    className="flex items-center gap-2"
                  >
                    <Icon className="h-4 w-4" />
                    <span className="hidden sm:inline">{type.label}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {rankingTypes.map((type) => (
              <TabsContent
                key={type.value}
                value={type.value}
                className="space-y-4"
              >
                <div className="space-y-4">
                  {sortedRankings.slice(0, 10).map((ranking, index) => (
                    <RankingCard
                      key={ranking.symbol}
                      ranking={ranking}
                      position={index + 1}
                      type={selectedRanking}
                      getRankIcon={getRankIcon}
                      getRankBadgeColor={getRankBadgeColor}
                      getProgressColor={getProgressColor}
                    />
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      {/* 排名分析总结 */}
      <RankingSummary rankings={rankings} />
    </div>
  );
}

// 单个排名卡片组件
function RankingCard({
  ranking,
  position,
  type,
  getRankIcon,
  getRankBadgeColor,
  getProgressColor,
}: {
  ranking: VarietyRanking;
  position: number;
  type: RankingType;
  getRankIcon: (rank: number) => React.ReactNode;
  getRankBadgeColor: (rank: number) => string;
  getProgressColor: (rank: number, total: number) => string;
}) {
  const getMetricValue = (type: RankingType) => {
    switch (type) {
      case 'returns':
        return ranking.metrics.returnRank;
      case 'risk':
        return ranking.metrics.riskRank;
      case 'riskAdjusted':
        return ranking.metrics.riskAdjustedReturnRank;
      case 'consistency':
        return ranking.metrics.consistencyRank;
      case 'overall':
      default:
        return ranking.rank;
    }
  };

  const metricValue = getMetricValue(type);
  const score = ranking.score;

  return (
    <Card
      className={cn(
        'transition-all hover:shadow-md',
        position <= 3 && 'border-2 border-yellow-200',
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* 排名图标 */}
            <div className="flex items-center justify-center w-10 h-10">
              {getRankIcon(position)}
            </div>

            {/* 品种信息 */}
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-medium text-lg">{ranking.symbol}</span>
                <Badge
                  variant="outline"
                  className={getRankBadgeColor(position)}
                >
                  #{position}
                </Badge>
              </div>
              <div className="text-sm text-muted-foreground">
                {ranking.name} · {ranking.sector}
              </div>
            </div>
          </div>

          {/* 评分和进度条 */}
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-lg font-bold">
                {(score * 100).toFixed(1)}
              </div>
              <div className="text-xs text-muted-foreground">综合评分</div>
            </div>
            <div className="w-24">
              <Progress value={score * 100} className="h-2" />
            </div>
          </div>
        </div>

        {/* 高亮信息 */}
        {ranking.highlights.length > 0 && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex flex-wrap gap-1">
              {ranking.highlights.map((highlight, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {highlight}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// 排名总结组件
function RankingSummary({ rankings }: { rankings: VarietyRanking[] }) {
  const summary = useMemo(() => {
    // 计算各版块的平均排名
    const sectorStats = rankings.reduce(
      (acc, ranking) => {
        if (!acc[ranking.sector]) {
          acc[ranking.sector] = { total: 0, count: 0, bestRank: Infinity };
        }
        acc[ranking.sector].total += ranking.rank;
        acc[ranking.sector].count += 1;
        acc[ranking.sector].bestRank = Math.min(
          acc[ranking.sector].bestRank,
          ranking.rank,
        );
        return acc;
      },
      {} as Record<string, { total: number; count: number; bestRank: number }>,
    );

    const sectorAverages = Object.entries(sectorStats)
      .map(([sector, stats]) => ({
        sector,
        averageRank: stats.total / stats.count,
        bestRank: stats.bestRank,
        count: stats.count,
      }))
      .sort((a, b) => a.averageRank - b.averageRank);

    // 计算TOP 3的版块分布
    const top3Distribution = rankings.slice(0, 3).reduce(
      (acc, ranking) => {
        acc[ranking.sector] = (acc[ranking.sector] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      totalVarieties: rankings.length,
      sectorAverages,
      top3Distribution,
      bestPerformer: rankings[0],
      mostConsistent: rankings.sort(
        (a, b) => a.metrics.consistencyRank - b.metrics.consistencyRank,
      )[0],
      bestRiskAdjusted: rankings.sort(
        (a, b) =>
          a.metrics.riskAdjustedReturnRank - b.metrics.riskAdjustedReturnRank,
      )[0],
    };
  }, [rankings]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* 总体统计 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">总体统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">总品种数</span>
              <span className="font-medium">{summary.totalVarieties}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                最佳表现品种
              </span>
              <Badge variant="secondary">{summary.bestPerformer.symbol}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">最稳定品种</span>
              <Badge variant="secondary">{summary.mostConsistent.symbol}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                最佳风险调整收益
              </span>
              <Badge variant="secondary">
                {summary.bestRiskAdjusted.symbol}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 版块表现 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">版块平均排名</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {summary.sectorAverages.slice(0, 5).map((item, index) => (
              <div
                key={item.sector}
                className="flex items-center justify-between"
              >
                <div className="flex items-center space-x-2">
                  <Badge variant="outline" className="text-xs">
                    #{index + 1}
                  </Badge>
                  <span className="text-sm">{item.sector}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium">
                    {item.averageRank.toFixed(1)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    (最佳: #{item.bestRank})
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* TOP 3版块分布 */}
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle className="text-lg">TOP 3版块分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {Object.entries(summary.top3Distribution).map(([sector, count]) => (
              <div key={sector} className="flex items-center space-x-2">
                <Badge variant="outline">{sector}</Badge>
                <span className="text-sm font-medium">{count}个品种</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
