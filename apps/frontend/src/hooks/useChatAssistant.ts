import { useChatStore } from '@/store/chatStore'

export const useChatAssistant = () => {
  return useChatStore((state) => ({
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
  }))
}
