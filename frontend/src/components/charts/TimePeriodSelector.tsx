import React from 'react'
import { TimePeriodSelectorProps, TimePeriod } from '../../types/kline.types'
import { getTimePeriodDisplayName, isValidTimePeriod } from '../../utils/klineHelpers'

export const TimePeriodSelector: React.FC<TimePeriodSelectorProps> = ({
  currentPeriod,
  availablePeriods,
  onPeriodChange,
  className = '',
  disabled = false
}) => {
  // 时间周期的显示顺序和分组
  const getGroupedPeriods = (periods: TimePeriod[]) => {
    const groups = {
      minutes: [] as TimePeriod[],
      hours: [] as TimePeriod[],
      days: [] as TimePeriod[],
      months: [] as TimePeriod[]
    }

    periods.forEach(period => {
      if (period.includes('m')) {
        groups.minutes.push(period)
      } else if (period.includes('h')) {
        groups.hours.push(period)
      } else if (period === '1d') {
        groups.days.push(period)
      } else if (period.includes('M')) {
        groups.months.push(period)
      }
    })

    return groups
  }

  // 获取按钮样式
  const getButtonStyles = (period: TimePeriod) => {
    const isActive = period === currentPeriod
    const baseStyles = 'px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200'

    if (disabled) {
      return `${baseStyles} text-gray-400 bg-gray-100 cursor-not-allowed`
    }

    if (isActive) {
      return `${baseStyles} text-white bg-blue-600 shadow-md transform scale-105`
    }

    return `${baseStyles} text-gray-700 bg-white border border-gray-300 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700`
  }

  const groups = getGroupedPeriods(availablePeriods)

  return (
    <div className={`time-period-selector ${className}`}>
      <div className="flex flex-wrap gap-2">
        {/* 分钟级别 */}
        {groups.minutes.length > 0 && (
          <div className="flex gap-1">
            {groups.minutes.map(period => (
              <button
                key={period}
                onClick={() => !disabled && onPeriodChange(period)}
                disabled={disabled}
                className={getButtonStyles(period)}
                title={getTimePeriodDisplayName(period)}
              >
                {period.replace('m', '分')}
              </button>
            ))}
          </div>
        )}

        {/* 小时级别 */}
        {groups.hours.length > 0 && (
          <div className="flex gap-1">
            {groups.hours.map(period => (
              <button
                key={period}
                onClick={() => !disabled && onPeriodChange(period)}
                disabled={disabled}
                className={getButtonStyles(period)}
                title={getTimePeriodDisplayName(period)}
              >
                {period.replace('h', '时')}
              </button>
            ))}
          </div>
        )}

        {/* 日级别 */}
        {groups.days.length > 0 && (
          <div className="flex gap-1">
            {groups.days.map(period => (
              <button
                key={period}
                onClick={() => !disabled && onPeriodChange(period)}
                disabled={disabled}
                className={getButtonStyles(period)}
                title={getTimePeriodDisplayName(period)}
              >
                日线
              </button>
            ))}
          </div>
        )}

        {/* 月级别 */}
        {groups.months.length > 0 && (
          <div className="flex gap-1">
            {groups.months.map(period => (
              <button
                key={period}
                onClick={() => !disabled && onPeriodChange(period)}
                disabled={disabled}
                className={getButtonStyles(period)}
                title={getTimePeriodDisplayName(period)}
              >
                周线
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 当前选择显示 */}
      <div className="mt-2 text-sm text-gray-600">
        当前选择: <span className="font-medium">{getTimePeriodDisplayName(currentPeriod)}</span>
      </div>
    </div>
  )
}

export default TimePeriodSelector