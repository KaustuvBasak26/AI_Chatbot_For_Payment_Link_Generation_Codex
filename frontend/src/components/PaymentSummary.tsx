import { useState } from 'react'
import type { PaymentRequest } from '../types/payment'
import { money, dateTime } from '../utils/format'
import { StatusBadge } from './StatusBadge'

export function PaymentSummary({payment}: {payment: PaymentRequest}) {
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
  const paymentUrl = payment.link ? new URL(payment.link.payment_url, window.location.origin).href : ''

  async function copyPaymentUrl() {
    try {
      await navigator.clipboard.writeText(paymentUrl)
      setCopyStatus('copied')
    } catch {
      setCopyStatus('failed')
    }
  }

  return <section className="card summary-card">
    <div className="section-heading"><div><p className="eyebrow">{payment.reference_id}</p><h2>{money(payment.total_minor, payment.currency)}</h2></div><StatusBadge status={payment.status} /></div>
    <div className="summary-grid"><div><small>Customer</small><strong>{payment.customer_name || 'Not specified'}</strong><span>{payment.customer_email}</span></div><div><small>Expires</small><strong>{dateTime(payment.expires_at)}</strong></div><div><small>Provider</small><strong>{payment.link?.provider || 'Not created'}</strong></div></div>
    {payment.link && <div className="link-result"><input aria-label="Payment link" readOnly value={paymentUrl} /><button onClick={() => void copyPaymentUrl()}>{copyStatus === 'copied' ? 'Copied' : copyStatus === 'failed' ? 'Copy failed' : 'Copy'}</button><a className="button secondary" href={paymentUrl} target="_blank" rel="noreferrer">Open link</a></div>}
  </section>
}
