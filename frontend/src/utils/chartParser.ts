/**
 * # [CHART_PARSER] ECharts图表配置解析工具
 *
 * ## [MODULE]
 * **文件名**: chartParser.ts
 * **职责**: 从AI返回的消息文本中提取和解析ECharts JSON配置
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **content: string** - 包含ECharts配置的消息文本内容
 *   - 格式: [CHART_START]{...ECharts JSON...}[CHART_END]
 *
 * ## [OUTPUT]
 * - **返回值: Record<string, any> | null** - 解析后的ECharts配置对象
 *   - 成功: 返回ECharts配置对象
 *   - 失败: 返回null（未找到标记或JSON解析失败）
 *
 * ## [LINK]
 * **上游依赖**:
 * - 无（独立工具函数）
 *
 * **下游依赖**:
 * - [../components/chat/EChartsRenderer.tsx](../components/chat/EChartsRenderer.tsx) - ECharts渲染组件
 * - [../components/chat/MessageList.tsx](../components/chat/MessageList.tsx) - 消息列表组件
 *
 * **调用方**:
 * - 聊天消息渲染组件
 *
 * ## [STATE]
 * - 无（纯函数工具）
 *
 * ## [SIDE-EFFECTS]
 * - 无（纯函数，无副作用）
 */

/**
 * 图表配置解析工具
 * 从消息文本中提取 ECharts JSON 配置
 */

/**
 * 从消息文本中提取 ECharts JSON 配置
 *
 * @param content - 消息文本内容
 * @returns 解析后的 ECharts 配置对象，如果未找到或解析失败则返回 null
 */
export function extractEChartsOption(content: string): Record<string, any> | null {
  if (!content) {
    return null
  }

  // 使用正则表达式匹配 [CHART_START]...{...}[CHART_END] 模式
  // 使用贪婪匹配，支持跨行匹配，忽略 JSON 前后的多余空格
  const chartPattern = /\[CHART_START\]\s*(\{[\s\S]*?\})\s*\[CHART_END\]/
  const match = content.match(chartPattern)

  if (!match) {
    return null
  }

  const jsonStr = match[1].trim()

  try {
    const option = JSON.parse(jsonStr)
    
    // 验证必需字段
    if (!option || typeof option !== 'object') {
      console.warn('ECharts option is not a valid object')
      return null
    }

    // 基本验证：检查是否有基本的图表结构
    // 注意：不强制要求所有字段，因为 ECharts 配置可以很灵活
    return option
  } catch (error) {
    console.warn('Failed to parse ECharts JSON configuration:', error)
    console.warn('JSON string:', jsonStr.substring(0, 200))
    return null
  }
}

/**
 * 从消息文本中移除图表配置标记
 * 
 * @param content - 消息文本内容
 * @returns 移除图表配置后的文本
 */
export function removeChartMarkers(content: string): string {
  if (!content) {
    return content
  }

  // 使用贪婪匹配，支持跨行匹配，忽略 JSON 前后的多余空格
  const chartPattern = /\[CHART_START\]\s*\{[\s\S]*?\}\s*\[CHART_END\]/g
  return content.replace(chartPattern, '').trim()
}

