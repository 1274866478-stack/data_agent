'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'

export default function ChatPage() {
  return (
    <div className="h-screen flex flex-col">
      <ChatInterface className="flex-1" />
    </div>
  )
}