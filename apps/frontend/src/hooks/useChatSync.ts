import { useChatStore } from '@/store/chatStore'

export const useChatSync = () => {
  return useChatStore((state) => ({
    isOnline: state.isOnline,
    isSyncing: state.isSyncing,
    syncPendingMessages: state.syncPendingMessages,
    stats: state.stats,
  }))
}
