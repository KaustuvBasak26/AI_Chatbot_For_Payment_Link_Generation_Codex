import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { cancelPayment, getPayment } from '../api/client'
import { PaymentSummary } from '../components/PaymentSummary'
import { dateTime, money } from '../utils/format'

export function DetailPage() {
  const {id = ''} = useParams(), client = useQueryClient()
  const query = useQuery({queryKey: ['payment', id], queryFn: () => getPayment(id), enabled: Boolean(id)})
  const cancel = useMutation({mutationFn: () => cancelPayment(id), onSuccess: data => client.setQueryData(['payment', id], data)})
  if (query.isLoading) return <main className="page inner-page"><div className="empty">Loading payment…</div></main>
  if (!query.data) return <main className="page inner-page"><div className="empty error-text">Payment request not found.</div></main>
  const payment = query.data
  return <main className="page inner-page"><Link className="back-link" to="/history">← Payment history</Link><PaymentSummary payment={payment}/><div className="detail-grid"><section className="card"><h2>Line items</h2>{payment.items.map(item => <div className="detail-row" key={item.id}><span>{item.quantity} × {item.name}<small>{money(item.unit_price_minor, payment.currency)} each</small></span><strong>{money(item.line_total_minor, payment.currency)}</strong></div>)}<div className="breakdown"><span>Subtotal <strong>{money(payment.subtotal_minor, payment.currency)}</strong></span><span>Discount <strong>− {money(payment.discount_minor, payment.currency)}</strong></span><span>Tax <strong>+ {money(payment.tax_minor, payment.currency)}</strong></span><span>Total <strong>{money(payment.total_minor, payment.currency)}</strong></span></div></section><section className="card"><h2>Request details</h2><dl><dt>Customer</dt><dd>{payment.customer_name || 'Not specified'}</dd><dt>Email</dt><dd>{payment.customer_email || '—'}</dd><dt>Pay by</dt><dd>{dateTime(payment.pay_by)}</dd><dt>Expires</dt><dd>{dateTime(payment.expires_at)}</dd><dt>Description</dt><dd>{payment.description || '—'}</dd></dl>{payment.status === 'ACTIVE' && <button className="secondary danger wide" onClick={() => cancel.mutate()} disabled={cancel.isPending}>{cancel.isPending ? 'Cancelling…' : 'Cancel payment link'}</button>}</section></div></main>
}

