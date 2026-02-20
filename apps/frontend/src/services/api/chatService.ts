import { api } from '@/lib/api-client'
import type { ChatQueryRequest, ChatQueryResponse, V2StreamCallbacks } from '@/types/api/chat'

export const chatService = {
  query: (request: ChatQueryRequest): Promise<ChatQueryResponse> => api.v2.query(request),
  stream: (
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    signal?: AbortSignal
  ): Promise<AbortController> => api.v2.stream(request, callbacks, signal),
  completion: (request: { messages: ChatQueryRequest['history'] }) => api.chat.completion(request as any),
  createSession: (title?: string) => api.chat?.createSession?.(title),
  deleteSession: (sessionId: string) => api.chat?.deleteSession?.(sessionId),
}

export default chatService
