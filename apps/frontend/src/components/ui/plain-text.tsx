'use client'

import { cn } from '@/lib/utils'
import { useMemo } from 'react'

interface PlainTextProps {
  content: string
  className?: string
  isLoading?: boolean  // 鏂板锛氬姞杞界姸鎬?
}

/**
 * 绉婚櫎Markdown鏍煎紡绗﹀彿锛岃浆鎹负绾枃鏈?
 * 淇濈暀娈佃惤缁撴瀯锛岀Щ闄ゆ墍鏈夋牸寮忔爣璁?
 */
function stripMarkdownFormatting(content: string): string {
  let cleaned = content

  // 1. 绉婚櫎鏍囬绗﹀彿 (###, ##, #)
  cleaned = cleaned.replace(/^#{1,6}\s+/gm, '')

  // 2. 绉婚櫎鏃犲簭鍒楄〃绗﹀彿 (-, *, +)
  cleaned = cleaned.replace(/^[\s]*[-*+]\s+/gm, '')

  // 3. 绉婚櫎鏈夊簭鍒楄〃绗﹀彿 (1., 2., etc.)
  cleaned = cleaned.replace(/^\d+\.\s+/gm, '')

  // 4. 绉婚櫎鍔犵矖绗﹀彿 (**, __)
  cleaned = cleaned.replace(/\*\*/g, '')
  cleaned = cleaned.replace(/__/g, '')

  // 5. 绉婚櫎鏂滀綋绗﹀彿 (*, _)
  cleaned = cleaned.replace(/(?<!\*)\*(?!\*)/g, '')
  cleaned = cleaned.replace(/(?<!_)_(?!_)/g, '')

  // 6. 绉婚櫎浠ｇ爜鍧楁爣璁?(```)
  cleaned = cleaned.replace(/```[\s\S]*?```/g, (match) => {
    // 鎻愬彇浠ｇ爜鍐呭锛岀Щ闄?``` 鍜岃瑷€鏍囪
    return match.replace(/```\w*\n?/g, '').replace(/```/g, '')
  })

  // 7. 绉婚櫎琛屽唴浠ｇ爜鏍囪 (`)
  cleaned = cleaned.replace(/`([^`]+)`/g, '$1')

  // 8. 绉婚櫎閾炬帴鏍煎紡 [text](url)锛屼繚鐣欐枃鏈?
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')

  // 9. 绉婚櫎鍥剧墖鏍煎紡 ![alt](url)
  cleaned = cleaned.replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')

  // 10. 绉婚櫎寮曠敤绗﹀彿 >
  cleaned = cleaned.replace(/^>\s+/gm, '')

  // 11. 绉婚櫎姘村钩绾跨鍙?
  cleaned = cleaned.replace(/^[-*_]{3,}\s*$/gm, '')

  // 12. 绉婚櫎鍒犻櫎绾挎爣璁?
  cleaned = cleaned.replace(/~~(.+?)~~/g, '$1')

  // 13. 娓呯悊澶氫綑绌鸿锛屼繚鐣欐钀藉垎闅旓紙鏈€澶氫袱涓繛缁崲琛岋級
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')

  // 14. 绉婚櫎琛岄琛屽熬澶氫綑绌烘牸
  cleaned = cleaned.split('\n').map(line => line.trim()).join('\n')

  return cleaned.trim()
}

/**
 * PlainText 缁勪欢 - 灏哅arkdown鏍煎紡鍐呭杞崲涓虹函鏂囨湰鏄剧ず
 * 绉婚櫎鎵€鏈塎arkdown鏍煎紡绗﹀彿锛屼繚鐣欐钀界粨鏋?
 */
export function PlainText({ content, className, isLoading = false }: PlainTextProps) {
  const plainContent = useMemo(() => stripMarkdownFormatting(content), [content])

  // 灏嗗唴瀹规寜娈佃惤鍒嗗壊锛屼负姣忎釜娈佃惤鍒涘缓 <p> 鏍囩
  const paragraphs = useMemo(() => {
    return plainContent
      .split(/\n\n+/)  // 鎸夊弻鎹㈣鍒嗗壊娈佃惤
      .filter(p => p.trim())  // 杩囨护绌烘钀?
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
        <p className={cn(
          "italic",
          isLoading
            ? "text-gray-400 animate-pulse"
            : "text-gray-500"
        )}>
          {isLoading
            ? "AI 正在思考..."
            : (content && content.trim())
              ? "暂无内容"
              : ""}
        </p>
      )}
    </div>
  )
}



