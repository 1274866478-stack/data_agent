import type { ChatSession } from '@/types/store/chat'
import { useChatStore } from '@/store/chatStore'

export const useChatSessions = (): { sessions: ChatSession[] } =>
  useChatStore((state) => ({
    sessions: state.sessions,
  }))
