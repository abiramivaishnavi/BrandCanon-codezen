// Shared small UI pieces so every page looks the same.
import React from 'react'

export function Button({ variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-brand text-white hover:bg-brand-dark',
    secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50',
    danger: 'bg-white text-red-700 border border-red-300 hover:bg-red-50',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  return <button {...props} className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${styles[variant]} ${className}`} />
}

export function Card({ title, action, children, className = '' }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

const PILL = {
  verified: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  advisory: 'bg-amber-50 text-amber-800 border-amber-200',
  blocking: 'bg-red-50 text-red-700 border-red-200',
  major: 'bg-orange-50 text-orange-700 border-orange-200',
  minor: 'bg-slate-100 text-slate-600 border-slate-200',
  draft: 'bg-slate-100 text-slate-600 border-slate-200',
  in_review: 'bg-blue-50 text-blue-700 border-blue-200',
  changes_requested: 'bg-orange-50 text-orange-700 border-orange-200',
  approved: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  accepted: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  dismissed: 'bg-slate-100 text-slate-500 border-slate-200',
  overridden: 'bg-purple-50 text-purple-700 border-purple-200',
  open: 'bg-white text-slate-600 border-slate-300',
}
const LABEL = { in_review: 'In review', changes_requested: 'Changes requested', approved: 'Approved – ready to publish' }

export function Pill({ kind, children }) {
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${PILL[kind] || PILL.minor}`}>
      {children || LABEL[kind] || kind}
    </span>
  )
}

export function ErrorNote({ error }) {
  if (!error) return null
  return <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
}

export function Empty({ children }) {
  return <p className="py-6 text-center text-sm text-slate-500">{children}</p>
}

export const inputCls = 'w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand'

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export function timeAgo(iso) {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  const mins = Math.round((Date.now() - d.getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`
  return d.toLocaleDateString()
}
