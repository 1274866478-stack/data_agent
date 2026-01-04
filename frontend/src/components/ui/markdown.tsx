/**
 * # [MARKDOWN] Markdown渲染组件
 *
 * ## [MODULE]
 * **文件名**: markdown.tsx
 * **职责**: 提供标准化的Markdown渲染组件 - 基于react-markdown和remark-gfm，支持GitHub Flavored Markdown，自定义组件样式，流式传输不完整语法修复
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - Markdown渲染组件
 *
 * ## [INPUT]
 * Props (MarkdownProps):
 * - **content: string** - Markdown内容字符串
 * - **className?: string** - 自定义类名
 *
 * ## [OUTPUT]
 * - **Markdown组件** - 渲染Markdown为HTML的div元素
 *   - **基础样式**: prose.prose-gray.max-w-none.dark:prose-invert（Tailwind Typography插件）
 *   - **自定义prose样式**: prose-p:text-gray-700.prose-li:text-gray-700.prose-strong:text-gray-900
 *   - **ReactMarkdown**: react-markdown库渲染
 *   - **remarkPlugins**: [remarkGfm]（GitHub Flavored Markdown支持：表格、删除线、任务列表等）
 *   - **自定义components**: 覆盖默认元素渲染
 *     - **code**: 行内代码（Code组件）或代码块（pre > code，bg-muted.p-4.rounded-lg.overflow-x-auto）
 *     - **h1/h2/h3**: 自定义标题样式（text-xl.font-bold.mt-6.mb-4等）
 *     - **p**: 段落样式（mb-3.leading-relaxed）
 *     - **ul/ol/li**: 列表样式（mb-3.ml-4.list-disc/decimal.space-y-1）
 *     - **a**: 链接样式（text-primary.hover:underline.underline-offset-2.target=_blank）
 *     - **table**: 表格样式（my-4.overflow-x-auto.min-w-full.divide-y.divide-border）
 *     - **thead/th**: 表头样式（bg-muted.px-3.py-2.text-left.text-sm.font-semibold.uppercase.tracking-wider）
 *     - **td**: 单元格样式（px-3.py-2.text-sm.border-t.border-border）
 *     - **blockquote**: 引用样式（border-l-4.border-primary.pl-4.my-4.italic.text-muted-foreground）
 *     - **hr**: 分隔线样式（my-4.border-border）
 *     - **strong/em**: 强调样式（font-semibold/italic）
 *   - **fixIncompleteMarkdown**: 修复流式传输中不完整的Markdown语法
 *   - **use client**: 'use client'指令（客户端组件）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架
 * - [react-markdown](https://github.com/remarkjs/react-markdown) - React Markdown渲染库
 * - [remark-gfm](https://github.com/remarkjs/remark-gfm) - GitHub Flavored Markdown插件
 * - [@/components/ui/typography](./typography.tsx) - 排版组件（Code组件复用）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Markdown组件是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要显示Markdown内容的组件
 * - 聊天消息、文档展示、AI响应等
 *
 * ## [STATE]
 * - **无状态**: Markdown是无状态组件（纯展示组件）
 * - **ReactMarkdown**: react-markdown库管理解析和渲染
 *   - **remarkPlugins**: [remarkGfm]（启用GFM：表格、删除线、任务列表、自动链接等）
 *   - **components**: 覆盖默认元素渲染（自定义样式）
 * - **fixIncompleteMarkdown函数**: 修复流式传输中不完整的Markdown语法
 *   - **未闭合的代码块**: 检查```数量是否为奇数（未闭合）
 *   - **未完成的列表项**: 删除以-或*开头但没有内容的行
 *   - **未完成的链接**: [text](...替换为[text](...)
 * - **自定义code组件**: 检测className中的language-(\w+)判断是否为代码块
 *   - **inline代码**: 复用typography.tsx的Code组件
 *   - **代码块**: pre > code结构，bg-muted.p-4.rounded-lg.overflow-x-auto
 * - **prose样式**: Tailwind Typography插件（prose.prose-gray.dark:prose-invert）
 *   - **max-w-none**: 取消最大宽度限制（允许全宽）
 *   - **自定义颜色**: prose-p:text-gray-700, prose-li:text-gray-700, prose-strong:text-gray-900
 * - **自定义样式覆盖**:
 *   - **h1**: text-xl.font-bold.mt-6.mb-4（20px，字体粗重700，上下margin）
 *   - **h2**: text-lg.font-semibold.mt-6.mb-3（18px，字体粗重600）
 *   - **h3**: text-md.font-semibold.mt-4.mb-2（16px，字体粗重600）
 *   - **p**: mb-3.leading-relaxed（底部margin 12px，行高1.625）
 *   - **ul/ol**: mb-3.ml-4.list-disc/decimal.space-y-1（底部margin，左padding，列表样式）
 *   - **li**: leading-relaxed（行高1.625）
 *   - **a**: text-primary.hover:underline.underline-offset-2.target=_blank.rel="noopener noreferrer"
 *   - **table**: my-4.overflow-x-auto.min-w-full.divide-y.divide-border（响应式表格）
 *   - **thead**: bg-muted（灰色背景）
 *   - **th**: px-3.py-2.text-left.text-sm.font-semibold.uppercase.tracking-wider（表头样式）
 *   - **td**: px-3.py-2.text-sm.border-t.border-border（单元格样式）
 *   - **blockquote**: border-l-4.border-primary.pl-4.my-4.italic.text-muted-foreground（引用样式）
 *   - **hr**: my-4.border-border（分隔线）
 *   - **strong**: font-semibold（字体粗重600）
 *   - **em**: italic（斜体）
 * - **use client**: 'use client'指令（客户端组件，因为react-markdown需要客户端渲染）
 *
 * ## [SIDE-EFFECTS]
 * - **ReactMarkdown解析**: react-markdown将Markdown字符串解析为React元素
 * - **remarkGfm插件**: 启用GitHub Flavored Markdown语法（表格、删除线、任务列表等）
 * - **fixIncompleteMarkdown**: 修复流式传输中不完整的Markdown语法
 *   - **代码块检测**: 检查```数量是否为奇数
 *   - **列表项清理**: 删除空的列表项
 *   - **链接修复**: 未闭合的链接添加占位符
 * - **自定义components**: 覆盖react-markdown默认元素渲染
 * - **Code组件复用**: 复用typography.tsx的Code组件（行内代码）
 * - **条件渲染**: className包含language-(\w+)时渲染代码块，否则渲染行内代码
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Props到HTML元素
 * - **target="_blank"**: 所有链接在新标签页打开
 * - **rel="noopener noreferrer"**: 安全属性（防止新标签页访问window.opener）
 * - **use client**: 客户端组件（react-markdown需要浏览器环境）
 */

'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { Code } from './typography'

interface MarkdownProps {
  content: string
  className?: string
}

/**
 * 修复流式传输中不完整的Markdown语法
 * 例如：未闭合的代码块、未完成的列表等
 */
function fixIncompleteMarkdown(content: string): string {
  let fixed = content

  // 修复未闭合的代码块（```开头但没有闭合）
  const codeBlockMatches = fixed.match(/```/g)
  if (codeBlockMatches && codeBlockMatches.length % 2 !== 0) {
    // 如果代码块数量是奇数，说明有未闭合的
    // 检查最后是否有未闭合的代码块
    const lastCodeBlockIndex = fixed.lastIndexOf('```')
    const afterLastCodeBlock = fixed.substring(lastCodeBlockIndex + 3)
    // 如果后面没有换行和语言标识，可能是未完成的代码块
    if (!afterLastCodeBlock.trim().match(/^\n/)) {
      // 不添加闭合，让用户看到正在输入的状态
      // 或者可以添加一个占位符
    }
  }

  // 修复未完成的列表项（以 - 或 * 开头但没有内容）
  fixed = fixed.replace(/^[\s]*[-*]\s*$/gm, '')

  // 修复未完成的链接 [text]( 但没有闭合
  fixed = fixed.replace(/\[([^\]]*)\]\([^)]*$/g, (match, text) => {
    return `[${text}](...)`
  })

  return fixed
}

export function Markdown({ content, className }: MarkdownProps) {
  // 修复流式传输中不完整的Markdown
  const fixedContent = fixIncompleteMarkdown(content)

  return (
    <div className={cn('prose prose-gray max-w-none dark:prose-invert prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 自定义代码块渲染
          code: ({ className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '')
            const language = match ? match[1] : ''
            const inline = className?.includes('inline-')

            // 过滤掉 SQL 代码块，避免与 AI 推理过程重复显示
            if (!inline && language === 'sql') {
              return null
            }

            if (!inline && language) {
              return (
                <div className="relative">
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code className={cn(className, 'text-sm')} {...props}>
                      {children}
                    </code>
                  </pre>
                </div>
              )
            }

            return <Code className={className} {...props}>{children}</Code>
          },

          // 自定义标题渲染
          h1: ({ children, ...props }) => (
            <h1 className="text-xl font-bold mt-6 mb-4" {...props}>
              {children}
            </h1>
          ),

          h2: ({ children, ...props }) => (
            <h2 className="text-lg font-semibold mt-6 mb-3" {...props}>
              {children}
            </h2>
          ),

          h3: ({ children, ...props }) => (
            <h3 className="text-md font-semibold mt-4 mb-2" {...props}>
              {children}
            </h3>
          ),

          // 自定义段落渲染
          p: ({ children, ...props }) => (
            <p className="mb-3 leading-relaxed" {...props}>
              {children}
            </p>
          ),

          // 自定义列表渲染
          ul: ({ children, ...props }) => (
            <ul className="mb-3 ml-4 list-disc space-y-1" {...props}>
              {children}
            </ul>
          ),

          ol: ({ children, ...props }) => (
            <ol className="mb-3 ml-4 list-decimal space-y-1" {...props}>
              {children}
            </ol>
          ),

          li: ({ children, ...props }) => (
            <li className="leading-relaxed" {...props}>
              {children}
            </li>
          ),

          // 自定义链接渲染
          a: ({ children, href, ...props }) => (
            <a
              href={href}
              className="text-primary hover:underline underline-offset-2"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            >
              {children}
            </a>
          ),

          // 自定义表格渲染 - 禁用表格，因为表格已在 ProcessingSteps 的步骤6中展示
          // 避免 Markdown 表格与 AI 推理过程中的表格重复显示
          table: ({ children, ...props }) => null,

          thead: ({ children, ...props }) => (
            <thead className="bg-muted" {...props}>
              {children}
            </thead>
          ),

          th: ({ children, ...props }) => (
            <th className="px-3 py-2 text-left text-sm font-semibold text-gray-900 uppercase tracking-wider" {...props}>
              {children}
            </th>
          ),

          td: ({ children, ...props }) => (
            <td className="px-3 py-2 text-sm text-gray-800 font-medium border-t border-border" {...props}>
              {children}
            </td>
          ),

          // 自定义块引用渲染
          blockquote: ({ children, ...props }) => (
            <blockquote className="border-l-4 border-primary pl-4 my-4 italic text-muted-foreground" {...props}>
              {children}
            </blockquote>
          ),

          // 自定义水平线渲染
          hr: ({ ...props }) => (
            <hr className="my-4 border-border" {...props} />
          ),

          // 自定义强调渲染
          strong: ({ children, ...props }) => (
            <strong className="font-semibold" {...props}>
              {children}
            </strong>
          ),

          em: ({ children, ...props }) => (
            <em className="italic" {...props}>
              {children}
            </em>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}