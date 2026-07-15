import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { LlmSettings } from '../../types/payment'
import { LlmSettingsPanel } from './LlmSettingsPanel'
import { defaultSettings, loadSettings } from './llmSettingsStore'

function Harness() {
  const [settings, setSettings] = useState<LlmSettings>({...defaultSettings, useAi: true})
  return <LlmSettingsPanel settings={settings} onChange={setSettings} onTest={vi.fn()} connection="" />
}

describe('LLM settings security', () => {
  beforeEach(() => sessionStorage.clear())

  it('masks, reveals, and clears the key', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByText('AI Settings'))
    const key = screen.getByLabelText('OpenAI API key')
    await user.type(key, 'sk-test-secret')
    expect(key).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', {name: 'Show'}))
    expect(key).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', {name: 'Clear key'}))
    expect(key).toHaveValue('')
    expect(sessionStorage.length).toBe(0)
  })

  it('defaults to memory-only and supports tab session retention', () => {
    expect(loadSettings().apiKey).toBe('')
    expect(sessionStorage.length).toBe(0)
    sessionStorage.setItem('paylink-openai-session', JSON.stringify({...defaultSettings, apiKey: 'sk-session', rememberSession: true}))
    expect(loadSettings().apiKey).toBe('sk-session')
  })

  it('shows server-managed mode without a browser key field', async () => {
    render(<LlmSettingsPanel settings={{...defaultSettings, model: 'gpt-test', useAi: true}} onChange={vi.fn()} onTest={vi.fn()} connection="" serverKeyConfigured allowUserProvidedKeys={false} />)
    await userEvent.click(screen.getByText('AI Settings'))
    expect(screen.getByText('Server-managed OpenAI key is configured.')).toBeInTheDocument()
    expect(screen.queryByLabelText('OpenAI API key')).not.toBeInTheDocument()
    expect(screen.getByRole('button', {name: 'Test connection'})).toBeEnabled()
  })
})
