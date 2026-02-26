import { useChatStore } from '@/store/chatStore'
import { useShallow } from 'zustand/shallow'

export const useChatSession = () => {
  return useChatStore(useShallow((state) => ({
    sessions: state.sessions,
    currentSession: state.currentSession,
    createSession: state.createSession,
    switchSession: state.switchSession,
    deleteSession: state.deleteSession,
    updateSessionTitle: state.updateSessionTitle,
    clearHistory: state.clearHistory,
    error: state.error,
    setError: state.setError,
    v2Session: state.v2Session,
    streamingStatus: state.streamingStatus,
  })))
}
