'use client'

import { cn } from '@/lib/utils'
import { useMemo } from 'react'

interface PlainTextProps {
  content: string
  className?: string
}

/**
 * 移除Markdown格式符号，转换为纯文本
 * 保留段落结构，移除所有格式标记
 */
function stripMarkdownFormatting(content: string): string {
  let cleaned = content

  // 1. 移除标题符号 (###, ##, #)
  cleaned = cleaned.replace(/^#{1,6}\s+/gm, '')

  // 2. 移除无序列表符号 (-, *, +)
  cleaned = cleaned.replace(/^[\s]*[-*+]\s+/gm, '')

  // 3. 移除有序列表符号 (1., 2., etc.)
  cleaned = cleaned.replace(/^\d+\.\s+/gm, '')

  // 4. 移除加粗符号 (**, __)
  cleaned = cleaned.replace(/\*\*/g, '')
  cleaned = cleaned.replace(/__/g, '')

  // 5. 移除斜体符号 (*, _)
  cleaned = cleaned.replace(/(?<!\*)\*(?!\*)/g, '')
  cleaned = cleaned.replace(/(?<!_)_(?!_)/g, '')

  // 6. 移除代码块标记 (```)
  cleaned = cleaned.replace(/```[\s\S]*?```/g, (match) => {
    // 提取代码内容，移除 ``` 和语言标记
    return match.replace(/```\w*\n?/g, '').replace(/```/g, '')
  })

  // 7. 移除行内代码标记 (`)
  cleaned = cleaned.replace(/`([^`]+)`/g, '$1')

  // 8. 移除链接格式 [text](url)，保留文本
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')

  // 9. 移除图片格式 ![alt](url)
  cleaned = cleaned.replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')

  // 10. 移除引用符号 >
  cleaned = cleaned.replace(/^>\s+/gm, '')

  // 11. 移除水平线符号
  cleaned = cleaned.replace(/^[-*_]{3,}\s*$/gm, '')

  // 12. 移除删除线标记
  cleaned = cleaned.replace(/~~(.+?)~~/g, '$1')

  // 13. 清理多余空行，保留段落分隔（最多两个连续换行）
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')

  // 14. 移除行首行尾多余空格
  cleaned = cleaned.split('\n').map(line => line.trim()).join('\n')

  return cleaned.trim()
}

/**
 * PlainText 组件 - 将Markdown格式内容转换为纯文本显示
 * 移除所有Markdown格式符号，保留段落结构
 */
export function PlainText({ content, className }: PlainTextProps) {
  const plainContent = useMemo(() => stripMarkdownFormatting(content), [content])

  // 将内容按段落分割，为每个段落创建 <p> 标签
  const paragraphs = useMemo(() => {
    return plainContent
      .split(/\n\n+/)  // 按双换行分割段落
      .filter(p => p.trim())  // 过滤空段落
      .map((p, idx) => ({
        id: idx,
        content: p.trim(),
      }))
  }, [plainContent])

  return (
    <div className={cn('text-base leading-relaxed text-gray-700', className)}>
      {paragraphs.map((para) => (
        <p key={para.id} className="mb-3 last:mb-0">
          {para.content}
        </p>
      ))}
      {paragraphs.length === 0 && (
        <p className="text-gray-400 italic">暂无内容</p>
      )}
    </div>
  )
}
