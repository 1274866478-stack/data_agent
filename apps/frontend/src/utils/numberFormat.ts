/**
 * 数值格式化工具
 * 规则：
 * - 仅对可解析为数字且小数位超过2位的值进行四舍五入保留2位
 * - 整数或已是 <=2 位小数的字符串保持原样
 * - 处理科学计数法与字符串数值；null/undefined/非数字直接原样返回空串或原值
 */
export interface FormatNumericOptions {
  /**
   * 是否保留千分位分隔符（默认 false）
   */
  thousandSeparator?: boolean
}

export function formatNumeric(value: unknown, options: FormatNumericOptions = {}): string {
  const { thousandSeparator = false } = options

  if (value === null || value === undefined) return ''

  // 已经是字符串的非数字直接返回
  const raw = typeof value === 'string' ? value.trim() : value

  // 尝试解析为数字
  const num = Number(raw)
  if (!Number.isFinite(num)) {
    return typeof value === 'string' ? value : ''
  }

  // 判断小数位数
  const decimalPart = Math.abs(num % 1)
  const decimalDigits =
    decimalPart === 0 ? 0 : (num.toString().split('.')[1] || '').length

  const formattedNum =
    decimalDigits > 2 ? Number(num.toFixed(2)) : num

  let result = formattedNum.toString()

  // 处理千分位
  if (thousandSeparator && Math.abs(formattedNum) >= 1000) {
    const [intPart, decPart] = result.split('.')
    result = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (decPart ? `.${decPart}` : '')
  }

  return result
}

/**
 * 批量格式化表格行的数值（浅拷贝，不修改原对象）
 */
export function formatTableRow(row: any[], thousandSeparator = false): any[] {
  return row.map((cell) => formatNumeric(cell, { thousandSeparator }) || formatNumeric(cell))
}
