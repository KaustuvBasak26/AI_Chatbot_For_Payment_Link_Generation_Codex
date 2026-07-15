export function money(minor: number, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(minor / 100)
}
export function dateTime(value: string | null) {
  return value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}
export function localInput(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

