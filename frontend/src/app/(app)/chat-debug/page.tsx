'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send } from 'lucide-react'

export default function ChatDebugPage() {
  const [input, setInput] = useState('')

  const handleSend = () => {
    console.log('发送消息:', input)
    alert(`发送消息: ${input}`)
  }

  const isSendDisabled = !input.trim()

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">聊天输入调试页面</h1>
      
      <div className="space-y-4">
        <div>
          <p className="text-sm text-muted-foreground mb-2">
            输入内容: "{input}" (长度: {input.length})
          </p>
          <p className="text-sm text-muted-foreground mb-2">
            Trim后内容: "{input.trim()}" (长度: {input.trim().length})
          </p>
          <p className="text-sm text-muted-foreground mb-2">
            按钮是否禁用: {isSendDisabled ? '是' : '否'}
          </p>
        </div>

        <div className="flex gap-3 border p-4 rounded-lg">
          <Textarea
            value={input}
            onChange={(e) => {
              console.log('输入变化:', e.target.value)
              setInput(e.target.value)
            }}
            placeholder="输入您的问题..."
            maxLength={2000}
            className="min-h-[40px] max-h-[120px] resize-none"
            rows={1}
          />
          
          <Button
            size="sm"
            onClick={handleSend}
            disabled={isSendDisabled}
            className="h-10 px-3"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-2">
          <Button onClick={() => setInput('测试消息')}>
            设置测试消息
          </Button>
          <Button onClick={() => setInput('')} variant="outline">
            清空输入
          </Button>
        </div>
      </div>
    </div>
  )
}

