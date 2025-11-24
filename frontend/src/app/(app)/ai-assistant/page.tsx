'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Send, Bot, User, Sparkles } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'

export default function AIAssistantPage() {
  const [input, setInput] = useState('')
  const { sendMessage, currentSession, createSession, isLoading } = useChatStore()

  // 获取当前会话的消息，如果没有会话则为空数组
  const messages = currentSession?.messages || []

  const handleSend = async () => {
    // 如果没有会话，先创建一个
    if (!currentSession) {
      await createSession('新对话')
    }

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
    <div className="h-full flex flex-col bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="flex-1 max-w-6xl mx-auto w-full p-6 flex flex-col">
        {/* Header */}
        <Card className="mb-6 border-2 border-blue-200 shadow-lg">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-3 text-2xl">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              AI 智能助手
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              基于智谱 GLM-4 的智能数据分析助手，支持多轮对话和上下文理解
            </p>
          </CardHeader>
        </Card>

        {/* Chat Area */}
        <Card className="flex-1 flex flex-col shadow-lg">
          <CardContent className="flex-1 flex flex-col p-6">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <div className="p-4 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full mb-4">
                    <Bot className="w-16 h-16 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">欢迎使用 AI 智能助手</h3>
                  <p className="text-gray-600 mb-6 max-w-md">
                    我可以帮助您分析数据、回答问题、生成报告。请输入您的问题开始对话。
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
                    {[
                      '介绍一下你的功能',
                      '分析我的数据源',
                      '生成数据报告',
                      '查看数据洞察'
                    ].map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        onClick={() => setInput(question)}
                        className="text-left justify-start"
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        {question}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.role === 'user' ? 'flex-row-reverse' : ''
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.role === 'user'
                          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                          : 'bg-gradient-to-br from-gray-100 to-gray-200'
                      }`}>
                        {message.role === 'user' ? (
                          <User className="w-5 h-5" />
                        ) : (
                          <Bot className="w-5 h-5 text-gray-700" />
                        )}
                      </div>
                      <div className={`flex-1 max-w-[75%] ${
                        message.role === 'user' ? 'text-right' : ''
                      }`}>
                        <div className={`inline-block p-4 rounded-2xl ${
                          message.role === 'user'
                            ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                            : 'bg-white border border-gray-200 shadow-sm'
                        }`}>
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                        <div className={`text-xs text-gray-500 mt-1 px-2 ${
                          message.role === 'user' ? 'text-right' : ''
                        }`}>
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                        <Bot className="w-5 h-5 text-gray-700" />
                      </div>
                      <div className="flex-1">
                        <div className="inline-block p-4 rounded-2xl bg-white border border-gray-200 shadow-sm">
                          <div className="flex items-center gap-2">
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
                            </div>
                            <span className="text-sm text-gray-600">AI 正在思考...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t pt-4">
              <div className="flex gap-3">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="输入您的问题... (按 Enter 发送，Shift+Enter 换行)"
                  disabled={isLoading}
                  className="flex-1 h-12 text-base"
                />
                <Button 
                  onClick={handleSend} 
                  disabled={isLoading || !input.trim()}
                  size="lg"
                  className="bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

