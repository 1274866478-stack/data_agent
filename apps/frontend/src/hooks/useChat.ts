import { useChatStore } from '@/store/chatStore'
import { useShallow } from 'zustand/shallow'

export const useChat = () => {
  return useChatStore(useShallow((state) => ({
    sessions: state.sessions,
    currentSession: state.currentSession,
    isLoading: state.isLoading,
    isTyping: state.isTyping,
    error: state.error,
    sendMessage: state.sendMessage,
    createSession: state.createSession,
    switchSession: state.switchSession,
  })))
}
