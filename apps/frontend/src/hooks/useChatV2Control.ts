import { useChatStore } from '@/store/chatStore'

export const useChatV2Control = () => {
  return useChatStore((state) => ({
    v2Session: state.v2Session,
    pauseV2Session: state.pauseV2Session,
    resumeV2Session: state.resumeV2Session,
    cancelV2Session: state.cancelV2Session,
  }))
}
