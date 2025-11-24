'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Send, Bot, User } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'

export default function SimpleChatPage() {
  const [input, setInput] = useState('')
  const { sendMessage, currentSession, createSession, messages, isLoading } = useChatStore()

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const content = input.trim()
    setInput('')
    await sendMessage(content)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              Data Agent V4 - AI聊天助手
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              多租户SaaS数据智能平台 - 让数据工作更智能
            </p>
          </CardHeader>
        </Card>

        <Card className="mb-4">
          <CardContent className="p-4">
            <div className="space-y-4 mb-4 h-96 overflow-y-auto border rounded-lg p-4 bg-white">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <Bot className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p>开始您的对话</p>
                  <p className="text-sm">我是您的AI助手，可以帮助您分析数据和回答问题</p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 mb-4 ${
                      message.role === 'user' ? 'flex-row-reverse' : ''
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200'
                    }`}>
                      {message.role === 'user' ? (
                        <User className="w-4 h-4" />
                      ) : (
                        <Bot className="w-4 h-4" />
                      )}
                    </div>
                    <div className={`max-w-[70%] ${
                      message.role === 'user' ? 'text-right' : ''
                    }`}>
                      <div className={`p-3 rounded-lg ${
                        message.role === 'user'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100'
                      }`}>
                        <p className="text-sm">{message.content}</p>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="max-w-[70%]">
                    <div className="p-3 rounded-lg bg-gray-100">
                      <div className="flex items-center gap-2">
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse"></div>
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse delay-75"></div>
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse delay-150"></div>
                        <span className="text-sm text-gray-600">AI正在思考...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题..."
                disabled={isLoading}
                className="flex-1"
              />
              <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
                <Send className="w-4 h-4" />
              </Button>
            </div>

            <div className="mt-2 text-xs text-gray-500">
              按 Enter 发送消息，Shift+Enter 换行
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold mb-2">功能特性</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ 实时AI对话</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ 多租户隔离</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ Markdown渲染</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ 响应式设计</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ 键盘快捷键</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>✅ 本地存储</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="mt-4">
          <CardContent className="p-4">
            <h3 className="font-semibold mb-2">测试建议问题</h3>
            <div className="flex flex-wrap gap-2">
              {[
                '你好，介绍一下你自己',
                '我的数据有哪些来源？',
                '分析最近的销售趋势',
                '查看客户数据洞察',
                '生成业务报告'
              ].map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => setInput(question)}
                  disabled={isLoading}
                >
                  {question}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}