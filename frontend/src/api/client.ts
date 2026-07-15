import axios from 'axios'
import type { ChatResponse, LlmSettings, PaymentRequest, Status } from '../types/payment'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1', timeout: 20_000 })

function llmHeaders(settings: LlmSettings) {
  if (!settings.useAi) return {}
  return { 'X-LLM-Provider': 'openai', 'X-LLM-Model': settings.model, 'X-LLM-API-Key': settings.apiKey }
}

export async function sendChat(message: string, conversationId: string | null, settings: LlmSettings) {
  const { data } = await api.post<ChatResponse>('/chat/messages', { conversation_id: conversationId, message, use_llm_extraction: settings.useAi, allow_deterministic_fallback: settings.fallback }, { headers: llmHeaders(settings) })
  return data
}
export async function testLlm(settings: LlmSettings) {
  const { data } = await api.post<{connected: boolean; message: string}>('/llm/test', {}, { headers: llmHeaders({...settings, useAi: true}) })
  return data
}
export async function getPayment(id: string) { return (await api.get<PaymentRequest>(`/payment-requests/${id}`)).data }
export async function updatePayment(id: string, payload: unknown) { return (await api.patch<PaymentRequest>(`/payment-requests/${id}`, payload)).data }
export async function confirmPayment(id: string, key: string) { return (await api.post<PaymentRequest>(`/payment-requests/${id}/confirm`, {}, { headers: {'Idempotency-Key': key} })).data }
export async function cancelPayment(id: string) { return (await api.post<PaymentRequest>(`/payment-requests/${id}/cancel`)).data }
export async function listPayments(page = 1, status = '', search = '') { return (await api.get<{items: PaymentRequest[]; total: number; page: number; page_size: number}>('/payment-requests', {params: {page, status: status || undefined, search: search || undefined}})).data }
export async function getMockPayment(token: string) { return (await api.get<PaymentRequest>(`/mock/payment-links/${token}`)).data }
export async function completeMockPayment(token: string) { return (await api.post<PaymentRequest>(`/mock/payment-links/${token}/complete`)).data }
export function apiErrorMessage(error: unknown, fallback: string) {
  if (!axios.isAxiosError(error)) return fallback
  const payload = error.response?.data as {error?: {message?: string}} | undefined
  return payload?.error?.message || fallback
}
export type { Status }
