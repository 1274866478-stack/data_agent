'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send } from 'lucide-react'

export default function TestInputPage() {
  const [input, setInput] = useState('')

  console.log('渲染 TestInputPage, input:', input)

  const handleSend = () => {
    console.log('发送消息:', input)
    alert(`发送消息: ${input}`)
    setInput('')
  }

  const isSendDisabled = !input.trim()

  return (
    <div className="container mx-auto p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">输入测试页面</h1>
      
      <div className="space-y-6">
        {/* 调试信息 */}
        <div className="bg-gray-100 p-4 rounded-lg space-y-2 text-sm font-mono">
          <div>
            <strong>输入内容:</strong> &quot;{input}&quot;
          </div>
          <div>
            <strong>输入长度:</strong> {input.length}
          </div>
          <div>
            <strong>Trim后内容:</strong> &quot;{input.trim()}&quot;
          </div>
          <div>
            <strong>Trim后长度:</strong> {input.trim().length}
          </div>
          <div>
            <strong>按钮禁用:</strong> {isSendDisabled ? '是 ❌' : '否 ✅'}
          </div>
        </div>

        {/* 输入区域 */}
        <div className="border-2 border-blue-500 rounded-lg p-4">
          <div className="flex gap-3">
            <Textarea
              value={input}
              onChange={(e) => {
                const newValue = e.target.value
                console.log('onChange 触发, 新值:', newValue)
                setInput(newValue)
              }}
              onInput={(e) => {
                console.log('onInput 触发:', (e.target as HTMLTextAreaElement).value)
              }}
              placeholder="在这里输入文字..."
              maxLength={2000}
              className="min-h-[40px] max-h-[120px] resize-none"
              rows={1}
            />
            
            <Button
              size="sm"
              onClick={() => {
                console.log('按钮被点击')
                handleSend()
              }}
              disabled={isSendDisabled}
              className="h-10 px-3"
              title={isSendDisabled ? '输入为空，按钮禁用' : '点击发送'}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="mt-2 text-xs text-gray-500">
            {input.length}/2000
          </div>
        </div>

        {/* 测试按钮 */}
        <div className="space-y-2">
          <Button 
            onClick={() => {
              console.log('设置测试消息')
              setInput('这是一条测试消息')
            }}
            className="w-full"
          >
            设置测试消息
          </Button>
          
          <Button 
            onClick={() => {
              console.log('清空输入')
              setInput('')
            }}
            variant="outline"
            className="w-full"
          >
            清空输入
          </Button>
        </div>

        {/* 原生 HTML 测试 */}
        <div className="border-2 border-green-500 rounded-lg p-4">
          <h3 className="font-bold mb-2">原生 HTML 测试</h3>
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => {
                console.log('原生 textarea onChange:', e.target.value)
                setInput(e.target.value)
              }}
              placeholder="原生 textarea..."
              className="flex-1 border rounded p-2"
              rows={2}
            />
            <button
              onClick={handleSend}
              disabled={isSendDisabled}
              className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

