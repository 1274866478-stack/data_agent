import { formatNumeric } from './numberFormat'

const CURRENCY_KEYWORDS = [
  '销售额',
  '金额',
  '销售',
  '营收',
  '收入',
  '总收入',
  '总销售额',
  '成交额',
  'revenue',
  'sales',
  'total_sales',
  'sales_amount',
  'amount',
  'gmv',
]

function isCurrencyName(name?: string | number | null) {
  if (name === undefined || name === null) return false
  const text = String(name).toLowerCase()
  return CURRENCY_KEYWORDS.some(keyword => text.includes(keyword.toLowerCase()))
}

/**
 * 为金额类图表自动补充 tooltip 的“元”后缀，避免与现有 formatter 冲突
 */
export function applyCurrencyTooltip(option: any) {
  if (!option || typeof option !== 'object') return option

  const seriesArray = Array.isArray(option.series)
    ? option.series
    : option.series
      ? [option.series]
      : []

  const hasCurrencySeries = seriesArray.some((s: any) =>
    isCurrencyName(s?.name) || isCurrencyName(s?.yAxis?.name)
  )

  const yAxis = option.yAxis
  const hasCurrencyAxis = Array.isArray(yAxis)
    ? yAxis.some(axis => isCurrencyName(axis?.name))
    : isCurrencyName(yAxis?.name)

  if (!hasCurrencySeries && !hasCurrencyAxis) return option

  const tooltip = option.tooltip || {}
  const alreadyCustomized = tooltip.formatter || tooltip.valueFormatter
  if (!alreadyCustomized) {
    tooltip.valueFormatter = (val: any) => `${formatNumeric(val)} 元`
  }

  if (!tooltip.trigger) {
    tooltip.trigger = 'axis'
  }

  option.tooltip = tooltip
  return option
}
