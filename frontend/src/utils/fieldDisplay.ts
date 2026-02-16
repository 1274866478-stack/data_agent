const FIELD_NAME_MAP: Record<string, string> = {
  month: '月份',
  order_count: '订单数量',
  total_sales: '总销售额',
}

function titleCase(text: string) {
  return text
    .split(' ')
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function friendlyFieldName(field: string): string {
  if (!field) return field

  const lower = field.toLowerCase()
  if (FIELD_NAME_MAP[lower]) return FIELD_NAME_MAP[lower]

  // 如果已经是中文字段名，直接返回
  if (/[\u4e00-\u9fa5]/.test(field)) return field

  // 兜底：将下划线转为空格并首字母大写，提升可读性
  const cleaned = field.replace(/_/g, ' ').trim()
  return cleaned ? titleCase(cleaned) : field
}
