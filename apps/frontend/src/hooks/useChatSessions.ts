import type { ChatSession } from '@/types/store/chat'
import { useChatStore } from '@/store/chatStore'
import { useShallow } from 'zustand/shallow'

export const useChatSessions = (): { sessions: ChatSession[] } =>
  useChatStore(useShallow((state) => ({
    sessions: state.sessions,
  })))
