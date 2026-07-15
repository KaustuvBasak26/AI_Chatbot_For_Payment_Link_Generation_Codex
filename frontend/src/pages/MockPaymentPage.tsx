import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { completeMockPayment, getMockPayment } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { dateTime, money } from '../utils/format'

export function MockPaymentPage() {
  const {publicToken = ''} = useParams(), client = useQueryClient()
  const query = useQuery({queryKey: ['mock', publicToken], queryFn: () => getMockPayment(publicToken), retry: false})
  const complete = useMutation({mutationFn: () => completeMockPayment(publicToken), onSuccess: data => client.setQueryData(['mock', publicToken], data)})
  if (query.isLoading) return <main className="checkout"><div className="checkout-card">Loading secure checkout…</div></main>
  if (!query.data) return <main className="checkout"><div className="checkout-card"><div className="checkout-brand">PayLink</div><h1>Link unavailable</h1><p>This payment link is invalid or no longer available.</p></div></main>
  const payment = query.data
  return <main className="checkout"><div className="checkout-card"><div className="checkout-brand">PayLink <span>Mock checkout</span></div><div className="checkout-status"><StatusBadge status={payment.status}/><small>{payment.reference_id}</small></div><p className="eyebrow">Amount due</p><h1>{money(payment.total_minor, payment.currency)}</h1><p>{payment.customer_name ? `Payment for ${payment.customer_name}` : 'Secure payment request'}</p><div className="checkout-items">{payment.items.map(item => <div key={item.id}><span>{item.quantity} × {item.name}</span><strong>{money(item.line_total_minor, payment.currency)}</strong></div>)}</div><div className="checkout-expiry">Link expires {dateTime(payment.expires_at)}</div>{payment.status === 'ACTIVE' && <button className="primary wide pay-button" onClick={() => complete.mutate()} disabled={complete.isPending}>{complete.isPending ? 'Processing…' : `Simulate payment of ${money(payment.total_minor, payment.currency)}`}</button>}{payment.status === 'PAID' && <div className="success-panel"><span>✓</span><strong>Payment successful</strong><p>This mock payment has been recorded.</p></div>}{['CANCELLED','EXPIRED'].includes(payment.status) && <div className="warning">This link is {payment.status.toLowerCase()} and cannot accept payment.</div>}<small className="mock-note">Demo only — no real money will be charged.</small></div></main>
}

