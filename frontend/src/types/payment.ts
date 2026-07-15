export type Status = 'DRAFT' | 'AWAITING_CLARIFICATION' | 'AWAITING_CONFIRMATION' | 'CREATING' | 'ACTIVE' | 'PAID' | 'EXPIRED' | 'CANCELLED' | 'FAILED'

export interface Customer { name: string | null; email: string | null; phone: string | null }
export interface DraftItem { name: string | null; quantity: number | null; unit_price_minor: number | null }
export interface Draft {
  customer: Customer; items: DraftItem[]; currency: string | null; discount_minor: number | null; tax_minor: number | null;
  pay_by: string | null; expires_at: string | null; validity_days: number | null; description: string | null;
  missing_fields: string[]; ambiguities: string[]
}
export interface PaymentItem { id: string; name: string; quantity: number; unit_price_minor: number; line_total_minor: number }
export interface PaymentLink { provider: string; provider_link_id: string | null; public_token: string; payment_url: string; status: string; created_at: string; expires_at: string; paid_at: string | null }
export interface PaymentRequest {
  id: string; reference_id: string; customer_name: string | null; customer_email: string | null; customer_phone: string | null;
  currency: string; subtotal_minor: number; discount_minor: number; tax_minor: number; total_minor: number; description: string | null;
  pay_by: string | null; expires_at: string | null; status: Status; created_at: string; updated_at: string; items: PaymentItem[]; link: PaymentLink | null
}
export interface ChatResponse {
  conversation_id: string; payment_request_id: string; assistant_message: string; draft: Draft; missing_fields: string[]; ambiguities: string[];
  validation_errors: {field: string; message: string}[]; requires_clarification: boolean; requires_confirmation: boolean;
  extraction_method: 'llm' | 'deterministic'; llm_provider: string | null; llm_model: string | null; llm_fallback_used: boolean
}
export interface LlmSettings { apiKey: string; model: string; useAi: boolean; fallback: boolean; rememberSession: boolean }

