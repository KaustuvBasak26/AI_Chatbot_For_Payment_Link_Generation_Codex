import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { PaymentRequest } from '../types/payment'
import { PaymentSummary } from './PaymentSummary'

const payment: PaymentRequest = {
  id: 'payment-1',
  reference_id: 'PAY-TEST',
  customer_name: 'Rahul Sharma',
  customer_email: 'rahul@example.com',
  customer_phone: null,
  currency: 'INR',
  subtotal_minor: 3500000,
  discount_minor: 0,
  tax_minor: 0,
  total_minor: 3500000,
  description: null,
  pay_by: null,
  expires_at: '2026-07-25T00:00:00Z',
  status: 'ACTIVE',
  created_at: '2026-07-15T00:00:00Z',
  updated_at: '2026-07-15T00:00:00Z',
  items: [],
  link: {
    provider: 'mock',
    provider_link_id: null,
    public_token: 'token',
    payment_url: '/pay/mock/token',
    status: 'ACTIVE',
    created_at: '2026-07-15T00:00:00Z',
    expires_at: '2026-07-25T00:00:00Z',
    paid_at: null,
  },
}

describe('PaymentSummary', () => {
  it('opens and copies relative payment links as absolute URLs', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText}})
    const expectedUrl = `${window.location.origin}/pay/mock/token`

    render(<PaymentSummary payment={payment} />)

    expect(screen.getByLabelText('Payment link')).toHaveValue(expectedUrl)
    expect(screen.getByRole('link', {name: 'Open link'})).toHaveAttribute('href', expectedUrl)
    await userEvent.click(screen.getByRole('button', {name: 'Copy'}))
    expect(writeText).toHaveBeenCalledWith(expectedUrl)
    expect(screen.getByRole('button', {name: 'Copied'})).toBeInTheDocument()
  })
})
