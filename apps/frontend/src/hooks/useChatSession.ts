import { useChatStore } from '@/store/chatStore'

export const useChatSession = () => {
  return useChatStore((state) => ({
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
  }))
}
