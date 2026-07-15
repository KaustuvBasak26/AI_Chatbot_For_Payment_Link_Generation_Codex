import { zodResolver } from '@hookform/resolvers/zod'
import { useFieldArray, useForm } from 'react-hook-form'
import { z } from 'zod'
import type { Draft, PaymentRequest } from '../../types/payment'
import { localInput, money } from '../../utils/format'

const itemSchema = z.object({name: z.string().min(1), quantity: z.number().int().positive(), unitPrice: z.number().positive()})
const schema = z.object({
  customerName: z.string(), customerEmail: z.string().email().or(z.literal('')), customerPhone: z.string(), currency: z.string().length(3),
  items: z.array(itemSchema).min(1), discount: z.number().min(0), tax: z.number().min(0), payBy: z.string(), expiresAt: z.string().min(1), description: z.string().max(1000)
})
type FormValues = z.infer<typeof schema>

function defaults(draft: Draft, payment?: PaymentRequest): FormValues {
  return { customerName: payment?.customer_name || draft.customer.name || '', customerEmail: payment?.customer_email || draft.customer.email || '', customerPhone: payment?.customer_phone || draft.customer.phone || '', currency: payment?.currency || draft.currency || 'INR',
    items: (payment?.items || draft.items).map(item => ({name: item.name || '', quantity: item.quantity || 1, unitPrice: (item.unit_price_minor || 0) / 100})),
    discount: (payment?.discount_minor ?? draft.discount_minor ?? 0) / 100, tax: (payment?.tax_minor ?? draft.tax_minor ?? 0) / 100,
    payBy: localInput(payment?.pay_by || draft.pay_by), expiresAt: localInput(payment?.expires_at || draft.expires_at), description: payment?.description || draft.description || '' }
}

export function DraftForm({draft, payment, onSave, saving}: {draft: Draft; payment?: PaymentRequest; onSave: (payload: unknown) => Promise<void>; saving: boolean}) {
  const {register, control, handleSubmit, watch, formState: {errors}} = useForm<FormValues>({resolver: zodResolver(schema), defaultValues: defaults(draft, payment)})
  const {fields, append, remove} = useFieldArray({control, name: 'items'})
  const values = watch()
  const subtotal = values.items.reduce((sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unitPrice) || 0), 0)
  const total = subtotal - (Number(values.discount) || 0) + (Number(values.tax) || 0)
  return <form className="card draft-form" onSubmit={handleSubmit(async data => onSave({
    customer: {name: data.customerName || null, email: data.customerEmail || null, phone: data.customerPhone || null}, currency: data.currency.toUpperCase(),
    items: data.items.map(item => ({name: item.name, quantity: Number(item.quantity), unit_price_minor: Math.round(Number(item.unitPrice) * 100)})),
    discount_minor: Math.round(Number(data.discount) * 100), tax_minor: Math.round(Number(data.tax) * 100), pay_by: data.payBy ? new Date(data.payBy).toISOString() : null,
    expires_at: new Date(data.expiresAt).toISOString(), description: data.description || null
  }))}>
    <div className="section-heading"><div><p className="eyebrow">Review draft</p><h2>Payment details</h2></div><span className="method-badge">Backend-calculated</span></div>
    <div className="form-grid three"><label>Customer name<input {...register('customerName')} /></label><label>Email<input type="email" {...register('customerEmail')} /></label><label>Phone<input {...register('customerPhone')} /></label></div>
    <div className="items-header"><h3>Line items</h3><button type="button" className="ghost" onClick={() => append({name: '', quantity: 1, unitPrice: 0})}>+ Add item</button></div>
    <div className="item-list">{fields.map((field, index) => <div className="item-row" key={field.id}><label>Item<input {...register(`items.${index}.name`)} /></label><label>Qty<input type="number" min="1" {...register(`items.${index}.quantity`, {valueAsNumber: true})} /></label><label>Unit price (₹)<input type="number" min="0.01" step="0.01" {...register(`items.${index}.unitPrice`, {valueAsNumber: true})} /></label><strong>{money((Number(values.items[index]?.quantity) || 0) * (Number(values.items[index]?.unitPrice) || 0) * 100)}</strong><button type="button" className="icon-button" aria-label="Remove item" onClick={() => remove(index)} disabled={fields.length === 1}>×</button></div>)}</div>
    <div className="form-grid three"><label>Currency<input {...register('currency')} /></label><label>Discount<input type="number" min="0" step="0.01" {...register('discount', {valueAsNumber: true})} /></label><label>Tax<input type="number" min="0" step="0.01" {...register('tax', {valueAsNumber: true})} /></label><label>Payment deadline<input type="datetime-local" {...register('payBy')} /></label><label>Link expiration<input type="datetime-local" {...register('expiresAt')} /></label><label>Description<input {...register('description')} /></label></div>
    {Object.keys(errors).length > 0 && <p className="error-text">Please correct the highlighted payment details.</p>}
    <div className="totals"><span>Subtotal <strong>{money(Math.round(subtotal * 100))}</strong></span><span>Discount <strong>− {money(Math.round((Number(values.discount) || 0) * 100))}</strong></span><span>Tax <strong>+ {money(Math.round((Number(values.tax) || 0) * 100))}</strong></span><span className="grand-total">Estimated total <strong>{money(Math.round(total * 100))}</strong></span><small>The backend recalculates and validates every amount.</small></div>
    <button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Save and review totals'}</button>
  </form>
}
