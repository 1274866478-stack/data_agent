import { useChatStore } from '@/store/chatStore'
import { useShallow } from 'zustand/shallow'

export const useChatSync = () => {
  return useChatStore(useShallow((state) => ({
    isOnline: state.isOnline,
    isSyncing: state.isSyncing,
    syncPendingMessages: state.syncPendingMessages,
    stats: state.stats,
  })))
}
