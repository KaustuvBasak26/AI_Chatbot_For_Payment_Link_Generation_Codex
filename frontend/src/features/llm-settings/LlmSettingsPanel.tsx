import { useState } from 'react'
import type { LlmSettings } from '../../types/payment'
import { clearRetainedKey, retainSettings } from './llmSettingsStore'

interface Props {
  settings: LlmSettings
  onChange: (settings: LlmSettings) => void
  onTest: () => Promise<void>
  connection: string
  serverKeyConfigured?: boolean
  allowUserProvidedKeys?: boolean
}

export function LlmSettingsPanel({ settings, onChange, onTest, connection, serverKeyConfigured = false, allowUserProvidedKeys = true }: Props) {
  const [showKey, setShowKey] = useState(false)
  const update = (patch: Partial<LlmSettings>) => { const next = {...settings, ...patch}; onChange(next); retainSettings(next) }
  const clear = () => { clearRetainedKey(); update({apiKey: '', rememberSession: false}); setShowKey(false) }
  return <details className="settings-card">
    <summary><span>AI Settings</span><span className={settings.useAi ? 'dot online' : 'dot'} /></summary>
    <div className="settings-content">
      <label className="toggle-row"><span><strong>OpenAI extraction</strong><small>Use structured AI extraction</small></span><input type="checkbox" checked={settings.useAi} onChange={e => update({useAi: e.target.checked})} /></label>
      <label>OpenAI model<input value={settings.model} placeholder="e.g. gpt-5-mini" onChange={e => update({model: e.target.value})} disabled={!settings.useAi} /></label>
      {serverKeyConfigured && <p className="connection" role="status">Server-managed OpenAI key is configured.</p>}
      {allowUserProvidedKeys && <>
        <label>Browser API key<div className="input-action"><input aria-label="OpenAI API key" type={showKey ? 'text' : 'password'} value={settings.apiKey} placeholder="sk-…" onChange={e => update({apiKey: e.target.value})} disabled={!settings.useAi} /><button type="button" className="ghost" onClick={() => setShowKey(v => !v)}>{showKey ? 'Hide' : 'Show'}</button></div></label>
        <label className="check"><input type="checkbox" checked={settings.rememberSession} onChange={e => update({rememberSession: e.target.checked})} /> Remember until this browser tab is closed</label>
      </>}
      <label className="check"><input type="checkbox" checked={settings.fallback} onChange={e => update({fallback: e.target.checked})} /> Use basic parser if OpenAI is temporarily unavailable</label>
      <div className="button-row"><button type="button" className="secondary" onClick={onTest} disabled={!settings.model || (!serverKeyConfigured && !settings.apiKey)}>Test connection</button>{allowUserProvidedKeys && <button type="button" className="ghost danger" onClick={clear}>Clear key</button>}</div>
      {connection && <p className="connection" role="status">{connection}</p>}
      <p className="security-note">{serverKeyConfigured && !allowUserProvidedKeys ? 'OpenAI credentials are managed by the server and are never sent to the browser.' : 'A browser-provided OpenAI key is sent only to backend extraction endpoints and is never stored in the application database.'}</p>
    </div>
  </details>
}
