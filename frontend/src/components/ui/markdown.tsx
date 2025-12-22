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

          // 自定义表格渲染
          table: ({ children, ...props }) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-border" {...props}>
                {children}
              </table>
            </div>
          ),

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