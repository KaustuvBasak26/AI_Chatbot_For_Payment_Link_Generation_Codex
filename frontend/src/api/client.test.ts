import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  post: vi.fn(), get: vi.fn(), patch: vi.fn()
}))
vi.mock('axios', () => ({default: {create: () => mocks, isAxiosError: (error: unknown) => Boolean((error as {isAxiosError?: boolean})?.isAxiosError)}}))

import { apiErrorMessage, confirmPayment, sendChat, testLlm } from './client'

const settings = {apiKey: 'sk-browser-secret', model: 'gpt-test', useAi: true, fallback: true, rememberSession: false}

describe('scoped LLM headers', () => {
  beforeEach(() => { vi.clearAllMocks(); mocks.post.mockResolvedValue({data: {}}) })

  it('attaches the key only to LLM operations', async () => {
    await sendChat('hello', null, settings)
    expect(mocks.post.mock.calls[0]?.[2]?.headers['X-LLM-API-Key']).toBe('sk-browser-secret')
    await testLlm(settings)
    expect(mocks.post.mock.calls[1]?.[2]?.headers['X-LLM-API-Key']).toBe('sk-browser-secret')
    await confirmPayment('request-id', 'idempotency-key')
    const paymentHeaders = mocks.post.mock.calls[2]?.[2]?.headers
    expect(paymentHeaders['X-LLM-API-Key']).toBeUndefined()
    expect(paymentHeaders['Idempotency-Key']).toBe('idempotency-key')
  })

  it('surfaces safe backend error messages', () => {
    const error = {isAxiosError: true, response: {data: {error: {message: 'The selected model is unavailable.'}}}}
    expect(apiErrorMessage(error, 'Fallback')).toBe('The selected model is unavailable.')
    expect(apiErrorMessage(new Error('unsafe'), 'Fallback')).toBe('Fallback')
  })
})
