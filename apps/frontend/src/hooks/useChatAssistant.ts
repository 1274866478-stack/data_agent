import { useChatStore } from '@/store/chatStore'
import { useShallow } from 'zustand/shallow'

export const useChatAssistant = () => {
  return useChatStore(useShallow((state) => ({
    sendMessage: state.sendMessage,
    currentSession: state.currentSession,
    createSession: state.createSession,
    isLoading: state.isLoading,
    sessions: state.sessions,
    switchSession: state.switchSession,
    deleteSession: state.deleteSession,
    deleteSessions: state.deleteSessions,
    searchSessions: state.searchSessions,
    startNewConversation: state.startNewConversation,
    stopStreaming: state.stopStreaming,
    streamingStatus: state.streamingStatus,
    outputFormat: state.outputFormat,
    setOutputFormat: state.setOutputFormat,
  })))
}
