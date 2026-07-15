import type { LlmSettings } from '../../types/payment'

const SESSION_KEY = 'paylink-openai-session'
export const defaultSettings: LlmSettings = { apiKey: '', model: import.meta.env.VITE_DEFAULT_LLM_MODEL || '', useAi: false, fallback: true, rememberSession: false }

export function loadSettings(): LlmSettings {
  const stored = sessionStorage.getItem(SESSION_KEY)
  if (!stored) return defaultSettings
  try { return { ...defaultSettings, ...JSON.parse(stored), rememberSession: true } as LlmSettings } catch { return defaultSettings }
}
export function retainSettings(settings: LlmSettings) {
  if (settings.rememberSession) sessionStorage.setItem(SESSION_KEY, JSON.stringify(settings))
  else sessionStorage.removeItem(SESSION_KEY)
}
export function clearRetainedKey() { sessionStorage.removeItem(SESSION_KEY) }

