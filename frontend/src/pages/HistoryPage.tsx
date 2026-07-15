import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listPayments } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { dateTime, money } from '../utils/format'

export function HistoryPage() {
  const [page, setPage] = useState(1), [status, setStatus] = useState(''), [search, setSearch] = useState('')
  const query = useQuery({queryKey: ['payments', page, status, search], queryFn: () => listPayments(page, status, search)})
  return <main className="page inner-page"><div className="page-title"><div><p className="eyebrow">Payment ledger</p><h1>History</h1><p>Every request, link, and payment status in one place.</p></div></div>
    <section className="card table-card"><div className="filters"><input placeholder="Search reference or customer…" value={search} onChange={e => {setSearch(e.target.value);setPage(1)}}/><select value={status} onChange={e => {setStatus(e.target.value);setPage(1)}}><option value="">All statuses</option>{['ACTIVE','PAID','CANCELLED','EXPIRED','AWAITING_CONFIRMATION'].map(value => <option key={value}>{value}</option>)}</select></div>
      {query.isLoading ? <div className="empty">Loading payments…</div> : query.isError ? <div className="empty error-text">Could not load payment history.</div> : !query.data?.items.length ? <div className="empty"><strong>No payments yet</strong><span>Create your first request from the assistant.</span></div> : <div className="table-wrap"><table><thead><tr><th>Reference</th><th>Customer</th><th>Amount</th><th>Status</th><th>Created</th><th></th></tr></thead><tbody>{query.data.items.map(payment => <tr key={payment.id}><td><strong>{payment.reference_id}</strong><small>{payment.link?.provider || 'Draft'}</small></td><td>{payment.customer_name || '—'}<small>{payment.customer_email}</small></td><td><strong>{money(payment.total_minor, payment.currency)}</strong></td><td><StatusBadge status={payment.status}/></td><td>{dateTime(payment.created_at)}</td><td><Link to={`/payments/${payment.id}`}>View →</Link></td></tr>)}</tbody></table></div>}
      <div className="pagination"><button className="ghost" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Previous</button><span>Page {page}</span><button className="ghost" disabled={!query.data || page * query.data.page_size >= query.data.total} onClick={() => setPage(p => p + 1)}>Next →</button></div>
    </section></main>
}

