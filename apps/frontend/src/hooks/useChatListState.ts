import { useChatStore } from '@/store/chatStore'

export const useChatListState = () => {
  return useChatStore((state) => ({
    streamingStatus: state.streamingStatus,
    streamingMessageId: state.streamingMessageId,
    selectedCharts: state.selectedCharts,
    isMergingCharts: state.isMergingCharts,
    toggleChartSelection: state.toggleChartSelection,
    clearChartSelection: state.clearChartSelection,
    mergeCharts: state.mergeCharts,
    stopStreaming: state.stopStreaming,
  }))
}
