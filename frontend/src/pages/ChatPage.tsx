import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiErrorMessage, confirmPayment, getLlmConfig, getPayment, sendChat, testLlm, updatePayment } from '../api/client'
import { PaymentSummary } from '../components/PaymentSummary'
import { DraftForm } from '../features/payment-request/DraftForm'
import { LlmSettingsPanel } from '../features/llm-settings/LlmSettingsPanel'
import { clearRetainedKey, loadSettings } from '../features/llm-settings/llmSettingsStore'
import type { ChatResponse, LlmConfig, LlmSettings, PaymentRequest } from '../types/payment'

const examples = [
  'Create a payment link for 3 keyboards at ₹2,000 each. Payment is due by 18 July 2026 and the link should remain valid for 7 days.',
  'Charge Rahul Sharma for two office chairs at INR 4,500 each and one desk at INR 8,000. His email is rahul@example.com. Payment is due on 20 July 2026 and the link expires on 22 July 2026.',
  'Create a link for Priya for 5 software licences costing ₹1,200 each.'
]

export function ChatPage() {
  const [settings, setSettings] = useState<LlmSettings>(loadSettings)
  const [connection, setConnection] = useState('')
  const [prompt, setPrompt] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<{role: 'user' | 'assistant'; content: string}[]>([])
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null)
  const [payment, setPayment] = useState<PaymentRequest | null>(null)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null)

  useEffect(() => {
    void getLlmConfig().then(config => {
      setLlmConfig(config)
      if (!config.allow_user_provided_keys) clearRetainedKey()
      setSettings(current => ({
        ...current,
        apiKey: config.allow_user_provided_keys ? current.apiKey : '',
        rememberSession: config.allow_user_provided_keys ? current.rememberSession : false,
        model: current.model || config.default_model,
        useAi: current.useAi || (config.server_key_configured && config.default_provider === 'openai'),
      }))
    }).catch(() => setLlmConfig(null))
  }, [])

  const chatMutation = useMutation({ mutationFn: (message: string) => sendChat(message, conversationId, settings), onSuccess: async result => {
    setConversationId(result.conversation_id); setChatResult(result); setMessages(current => [...current, {role: 'assistant', content: result.assistant_message}]); setPayment(await getPayment(result.payment_request_id)); setPrompt(''); setError('')
  }, onError: error => setError(apiErrorMessage(error, 'The request could not be extracted. Check your settings and try again.')) })
  const saveMutation = useMutation({mutationFn: (payload: unknown) => updatePayment(chatResult!.payment_request_id, payload), onSuccess: result => {setPayment(result); setEditing(false); setError('')}})
  const confirmMutation = useMutation({mutationFn: () => confirmPayment(chatResult!.payment_request_id, crypto.randomUUID()), onSuccess: result => {setPayment(result); setEditing(false)}, onError: () => setError('The payment link could not be created. Please review the draft and retry.')})

  async function submit() {
    const message = prompt.trim(); if (!message) return
    setMessages(current => [...current, {role: 'user', content: message}]); chatMutation.mutate(message)
  }
  async function testConnection() {
    setConnection('Testing…')
    try { const result = await testLlm(settings); setConnection(result.message) } catch (error) { setConnection(apiErrorMessage(error, 'Connection failed. Check the key and model.')) }
  }

  return <main className="page chat-page">
    <header className="hero"><div><p className="eyebrow">Conversational invoicing</p><h1>Turn a sentence into a<br/><em>payment link.</em></h1><p>Describe what you’re charging for. PayLink extracts the details, you review them, and the backend handles the money.</p></div><div className="hero-mark">₹<span>→</span></div></header>
    <div className="workspace-grid">
      <section className="chat-column">
        <div className="card conversation">
          <div className="conversation-head"><div><span className="live-dot"/> New payment request</div>{chatResult && <span className="method-badge">{chatResult.extraction_method === 'llm' ? '✦ Extracted using OpenAI' : 'Extracted using basic parser'}</span>}</div>
          <div className="messages" aria-live="polite">
            {messages.length === 0 && <div className="welcome-message"><span>✦</span><div><strong>What would you like to collect?</strong><p>Include items, prices, a deadline, and how long the link should stay active.</p></div></div>}
            {messages.map((message, index) => <div key={index} className={`message ${message.role}`}>{message.content}</div>)}
            {chatMutation.isPending && <div className="message assistant typing">Extracting securely…</div>}
          </div>
          {chatResult?.llm_fallback_used && <div className="warning">OpenAI was unavailable. This draft was created using the basic parser. Review the details carefully.</div>}
          {error && <div className="error-text">{error}</div>}
          <div className="composer"><textarea value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => {if (e.key === 'Enter' && !e.shiftKey) {e.preventDefault(); void submit()}}} placeholder="e.g. Charge Rahul for 2 chairs at ₹4,500 each…" maxLength={5000}/><button className="send-button" onClick={() => void submit()} disabled={!prompt.trim() || chatMutation.isPending}>↑</button></div>
        </div>
        <div className="examples"><span>Try an example</span>{examples.map((example, index) => <button key={example} onClick={() => setPrompt(example)}>0{index + 1} · {index === 0 ? 'Simple order' : index === 1 ? 'Multi-item request' : 'Needs clarification'}</button>)}</div>
      </section>
      <aside><LlmSettingsPanel settings={settings} onChange={setSettings} onTest={testConnection} connection={connection} serverKeyConfigured={llmConfig?.server_key_configured} allowUserProvidedKeys={llmConfig?.allow_user_provided_keys ?? true}/><div className="trust-card"><span>✓</span><div><strong>Financially safe by design</strong><p>AI extracts fields. Your backend validates every date and calculates every paise.</p></div></div></aside>
    </div>
    {chatResult && payment && payment.status !== 'ACTIVE' && payment.status !== 'PAID' && payment.status !== 'CANCELLED' && <section className="review-section">
      {chatResult.requires_clarification && !payment.items.length ? <div className="card clarification"><p className="eyebrow">One more detail</p><h2>{chatResult.assistant_message}</h2><p>Reply in the chat above and I’ll merge it into this draft.</p></div> : editing ? <DraftForm draft={chatResult.draft} payment={payment} onSave={async payload => {await saveMutation.mutateAsync(payload)}} saving={saveMutation.isPending}/> : <div className="card review-preview"><div className="section-heading"><div><p className="eyebrow">Ready for review</p><h2>{payment.items.length} item{payment.items.length === 1 ? '' : 's'} · {payment.currency}</h2></div><button className="secondary" onClick={() => setEditing(true)}>Edit details</button></div><div className="preview-items">{payment.items.map(item => <div key={item.id}><span>{item.quantity} × {item.name}</span><strong>₹{(item.line_total_minor / 100).toLocaleString('en-IN')}</strong></div>)}</div><div className="confirm-total"><span>Total</span><strong>₹{(payment.total_minor / 100).toLocaleString('en-IN')}</strong></div><button className="primary wide" onClick={() => confirmMutation.mutate()} disabled={confirmMutation.isPending || !payment.expires_at}>{confirmMutation.isPending ? 'Creating one secure link…' : 'Confirm and create payment link'}</button><small className="centered">This action creates exactly one idempotent payment link.</small></div>}
    </section>}
    {payment && ['ACTIVE','PAID','CANCELLED','EXPIRED'].includes(payment.status) && <section className="review-section"><PaymentSummary payment={payment}/></section>}
  </main>
}
