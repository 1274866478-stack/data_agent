'use client'

import { cn } from '@/lib/utils'
import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Code } from './typography'

interface MarkdownProps {
  content: string
  className?: string
}

/**
 * 解析 Markdown 表格为结构化数据
 */
interface ParsedTable {
  headers: string[]
  rows: string[][]
  startIndex: number
  endIndex: number
}

function parseMarkdownTables(content: string): { tables: ParsedTable[], textParts: string[] } {
  const lines = content.split('\n')
  const tables: ParsedTable[] = []
  const textParts: string[] = []
  
  let i = 0
  let currentTextStart = 0
  
  while (i < lines.length) {
    const line = lines[i].trim()
    
    // 检测表格头（以 | 开头和结尾）
    if (line.startsWith('|') && line.endsWith('|')) {
      // 检查下一行是否是分隔行（|---|---|）
      const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : ''
      const isSeparatorLine = nextLine.startsWith('|') && 
                              nextLine.endsWith('|') && 
                              nextLine.includes('-')
      
      if (isSeparatorLine) {
        // 找到表格，保存之前的文本
        if (i > currentTextStart) {
          textParts.push(lines.slice(currentTextStart, i).join('\n'))
        }
        
        // 解析表头
        const headers = line
          .slice(1, -1)  // 移除首尾的 |
          .split('|')
          .map(h => h.trim())
        
        // 跳过分隔行
        let j = i + 2
        const rows: string[][] = []
        
        // 解析数据行
        while (j < lines.length) {
          const rowLine = lines[j].trim()
          if (rowLine.startsWith('|') && rowLine.endsWith('|')) {
            const cells = rowLine
              .slice(1, -1)
              .split('|')
              .map(c => c.trim())
            rows.push(cells)
            j++
          } else {
            break
          }
        }
        
        tables.push({
          headers,
          rows,
          startIndex: textParts.length,
          endIndex: textParts.length
        })
        
        // 添加表格占位符
        textParts.push(`__TABLE_${tables.length - 1}__`)
        
        i = j
        currentTextStart = j
        continue
      }
    }
    
    i++
  }
  
  // 添加剩余文本
  if (currentTextStart < lines.length) {
    textParts.push(lines.slice(currentTextStart).join('\n'))
  }
  
  return { tables, textParts }
}

/**
 * 渲染单个表格（使用与 ProcessingSteps 一致的样式）
 */
function TableRenderer({ table }: { table: ParsedTable }) {
  return (
    <div className="my-4 rounded-md border border-gray-200 dark:border-slate-700 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
        <span className="text-xs font-medium text-gray-700">数据表格</span>
        <span className="text-xs text-gray-500">
          {table.rows.length} 行 × {table.headers.length} 列
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-gray-50 dark:bg-slate-800 sticky top-0">
            <tr>
              {table.headers.map((header, idx) => (
                <th
                  key={idx}
                  className="px-3 py-2 border-b border-gray-200 dark:border-slate-700 text-left font-medium text-gray-700 whitespace-nowrap bg-gray-50 dark:bg-slate-800"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIdx) => (
              <tr key={rowIdx} className="odd:bg-white even:bg-gray-50 dark:bg-slate-800/60 hover:bg-blue-50/30">
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className="px-3 py-1.5 border-b border-gray-100 text-gray-800 align-top"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/**
 * 修复流式传输中不完整的Markdown语法
 */
function fixIncompleteMarkdown(content: string): string {
  let fixed = content

  // 修复未闭合的代码块
  const codeBlockMatches = fixed.match(/```/g)
  if (codeBlockMatches && codeBlockMatches.length % 2 !== 0) {
    const lastCodeBlockIndex = fixed.lastIndexOf('```')
    const afterLastCodeBlock = fixed.substring(lastCodeBlockIndex + 3)
    if (!afterLastCodeBlock.trim().match(/^\n/)) {
      // 保持原样
    }
  }

  // 修复未完成的列表项
  fixed = fixed.replace(/^[\s]*[-*]\s*$/gm, '')

  // 修复未完成的链接
  fixed = fixed.replace(/\[([^\]]*)\]\([^)]*$/g, (match, text) => {
    return `[${text}](...)`
  })

  return fixed
}

export function Markdown({ content, className }: MarkdownProps) {
  // 解析表格
  const { tables, textParts } = useMemo(() => parseMarkdownTables(content), [content])
  
  // 如果没有表格，直接使用 ReactMarkdown
  if (tables.length === 0) {
    const fixedContent = fixIncompleteMarkdown(content)
    return (
      <div className={cn('prose prose-gray max-w-none dark:prose-invert prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900', className)}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code: ({ className, children, ...props }: any) => {
              const match = /language-(\w+)/.exec(className || '')
              const language = match ? match[1] : ''
              const inline = className?.includes('inline-')

              if (!inline && language === 'sql') {
                return null
              }

              if (!inline && language) {
                return (
                  <code className={cn(className, 'text-sm')} {...props}>
                    {children}
                  </code>
                )
              }

              return <Code className={className} {...props}>{children}</Code>
            },
            pre: ({ children, ...props }) => {
              if (!children) return null
              if (Array.isArray(children)) {
                const hasValidContent = children.some(child => {
                  if (child === null || child === undefined) return false
                  if (typeof child === 'string' && !child.trim()) return false
                  return true
                })
                if (!hasValidContent) return null
              }
              if (typeof children === 'string' && !children.trim()) return null
              return (
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto" {...props}>
                  {children}
                </pre>
              )
            },
            h1: ({ children, ...props }) => (
              <h1 className="text-xl font-bold mt-6 mb-4" {...props}>{children}</h1>
            ),
            h2: ({ children, ...props }) => (
              <h2 className="text-lg font-semibold mt-6 mb-3" {...props}>{children}</h2>
            ),
            h3: ({ children, ...props }) => (
              <h3 className="text-md font-semibold mt-4 mb-2" {...props}>{children}</h3>
            ),
            p: ({ children, ...props }) => (
              <p className="mb-3 leading-relaxed" {...props}>{children}</p>
            ),
            ul: ({ children, ...props }) => (
              <ul className="mb-3 ml-4 list-disc space-y-1" {...props}>{children}</ul>
            ),
            ol: ({ children, ...props }) => (
              <ol className="mb-3 ml-4 list-decimal space-y-1" {...props}>{children}</ol>
            ),
            li: ({ children, ...props }) => (
              <li className="leading-relaxed" {...props}>{children}</li>
            ),
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
            blockquote: ({ children, ...props }) => (
              <blockquote className="border-l-4 border-primary pl-4 my-4 italic text-muted-foreground" {...props}>
                {children}
              </blockquote>
            ),
            hr: ({ ...props }) => (
              <hr className="my-4 border-border" {...props} />
            ),
            strong: ({ children, ...props }) => (
              <strong className="font-semibold" {...props}>{children}</strong>
            ),
            em: ({ children, ...props }) => (
              <em className="italic" {...props}>{children}</em>
            ),
            img: ({ src, alt, ...props }: any) => {
              // 支持 base64 图片和外部 URL
              if (src && (src.startsWith('data:') || src.startsWith('http'))) {
                return (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={src}
                    alt={alt || '图表'}
                    className="max-w-full h-auto rounded-lg my-2"
                    {...props}
                  />
                )
              }
              // 无效的图片源，显示 alt 文本
              return <span className="text-muted-foreground">{alt || src}</span>
            },
          }}
        >
          {fixedContent}
        </ReactMarkdown>
      </div>
    )
  }

  // 有表格时，分段渲染
  return (
    <div className={cn('prose prose-gray max-w-none dark:prose-invert prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900', className)}>
      {textParts.map((part, idx) => {
        // 检查是否是表格占位符
        const tableMatch = part.match(/^__TABLE_(\d+)__$/)
        if (tableMatch) {
          const tableIdx = parseInt(tableMatch[1])
          return <TableRenderer key={`table-${tableIdx}`} table={tables[tableIdx]} />
        }

        // 普通文本，使用 ReactMarkdown 渲染
        const fixedPart = fixIncompleteMarkdown(part)
        if (!fixedPart.trim()) return null

        return (
          <ReactMarkdown
            key={`text-${idx}`}
            remarkPlugins={[remarkGfm]}
            components={{
              code: ({ className, children, ...props }: any) => {
                const match = /language-(\w+)/.exec(className || '')
                const language = match ? match[1] : ''
                const inline = className?.includes('inline-')

                if (!inline && language === 'sql') return null

                if (!inline && language) {
                  return (
                    <code className={cn(className, 'text-sm')} {...props}>
                      {children}
                    </code>
                  )
                }

                return <Code className={className} {...props}>{children}</Code>
              },
              pre: ({ children, ...props }) => {
                if (!children) return null
                if (Array.isArray(children)) {
                  const hasValidContent = children.some(child => {
                    if (child === null || child === undefined) return false
                    if (typeof child === 'string' && !child.trim()) return false
                    return true
                  })
                  if (!hasValidContent) return null
                }
                if (typeof children === 'string' && !children.trim()) return null
                return (
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto" {...props}>
                    {children}
                  </pre>
                )
              },
              h1: ({ children, ...props }) => (
                <h1 className="text-xl font-bold mt-6 mb-4" {...props}>{children}</h1>
              ),
              h2: ({ children, ...props }) => (
                <h2 className="text-lg font-semibold mt-6 mb-3" {...props}>{children}</h2>
              ),
              h3: ({ children, ...props }) => (
                <h3 className="text-md font-semibold mt-4 mb-2" {...props}>{children}</h3>
              ),
              p: ({ children, ...props }) => (
                <p className="mb-3 leading-relaxed" {...props}>{children}</p>
              ),
              ul: ({ children, ...props }) => (
                <ul className="mb-3 ml-4 list-disc space-y-1" {...props}>{children}</ul>
              ),
              ol: ({ children, ...props }) => (
                <ol className="mb-3 ml-4 list-decimal space-y-1" {...props}>{children}</ol>
              ),
              li: ({ children, ...props }) => (
                <li className="leading-relaxed" {...props}>{children}</li>
              ),
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
              blockquote: ({ children, ...props }) => (
                <blockquote className="border-l-4 border-primary pl-4 my-4 italic text-muted-foreground" {...props}>
                  {children}
                </blockquote>
              ),
              hr: ({ ...props }) => (
                <hr className="my-4 border-border" {...props} />
              ),
              strong: ({ children, ...props }) => (
                <strong className="font-semibold" {...props}>{children}</strong>
              ),
              em: ({ children, ...props }) => (
                <em className="italic" {...props}>{children}</em>
              ),
              img: ({ src, alt, ...props }: any) => {
                // 支持 base64 图片和外部 URL
                if (src && (src.startsWith('data:') || src.startsWith('http'))) {
                  return (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={src}
                      alt={alt || '图表'}
                      className="max-w-full h-auto rounded-lg my-2"
                      {...props}
                    />
                  )
                }
                // 无效的图片源，显示 alt 文本
                return <span className="text-muted-foreground">{alt || src}</span>
              },
            }}
          >
            {fixedPart}
          </ReactMarkdown>
        )
      })}
    </div>
  )
}