import { useState } from 'react'
import type { LlmSettings } from '../../types/payment'
import { clearRetainedKey, retainSettings } from './llmSettingsStore'

interface Props { settings: LlmSettings; onChange: (settings: LlmSettings) => void; onTest: () => Promise<void>; connection: string }

export function LlmSettingsPanel({ settings, onChange, onTest, connection }: Props) {
  const [showKey, setShowKey] = useState(false)
  const update = (patch: Partial<LlmSettings>) => { const next = {...settings, ...patch}; onChange(next); retainSettings(next) }
  const clear = () => { clearRetainedKey(); update({apiKey: '', rememberSession: false}); setShowKey(false) }
  return <details className="settings-card">
    <summary><span>AI Settings</span><span className={settings.useAi ? 'dot online' : 'dot'} /></summary>
    <div className="settings-content">
      <label className="toggle-row"><span><strong>OpenAI extraction</strong><small>Use structured AI extraction</small></span><input type="checkbox" checked={settings.useAi} onChange={e => update({useAi: e.target.checked})} /></label>
      <label>OpenAI model<input value={settings.model} placeholder="e.g. gpt-5-mini" onChange={e => update({model: e.target.value})} disabled={!settings.useAi} /></label>
      <label>API key<div className="input-action"><input aria-label="OpenAI API key" type={showKey ? 'text' : 'password'} value={settings.apiKey} placeholder="sk-…" onChange={e => update({apiKey: e.target.value})} disabled={!settings.useAi} /><button type="button" className="ghost" onClick={() => setShowKey(v => !v)}>{showKey ? 'Hide' : 'Show'}</button></div></label>
      <label className="check"><input type="checkbox" checked={settings.rememberSession} onChange={e => update({rememberSession: e.target.checked})} /> Remember until this browser tab is closed</label>
      <label className="check"><input type="checkbox" checked={settings.fallback} onChange={e => update({fallback: e.target.checked})} /> Use basic parser if OpenAI is temporarily unavailable</label>
      <div className="button-row"><button type="button" className="secondary" onClick={onTest} disabled={!settings.apiKey || !settings.model}>Test connection</button><button type="button" className="ghost danger" onClick={clear}>Clear key</button></div>
      {connection && <p className="connection" role="status">{connection}</p>}
      <p className="security-note">Your OpenAI API key is sent to the backend only for AI extraction. It is not stored in the application database.</p>
    </div>
  </details>
}

