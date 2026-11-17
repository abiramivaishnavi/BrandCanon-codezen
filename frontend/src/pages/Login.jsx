import React, { useState } from 'react'
import { api } from '../api.js'
import { Button, ErrorNote, Field, inputCls } from '../ui.jsx'

// Demo accounts are created automatically by the backend (see backend/app/seed.py).
const DEMO = [
  { label: 'Brand Admin', email: 'admin@aurorabrew.demo', password: 'admin123', note: 'Sets up guidelines, facts, terms, colours' },
  { label: 'Creator', email: 'creator@aurorabrew.demo', password: 'creator123', note: 'Uploads content and fixes issues' },
  { label: 'Reviewer', email: 'reviewer@aurorabrew.demo', password: 'reviewer123', note: 'Approves or requests changes' },
]

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e, creds) {
    e?.preventDefault()
    setBusy(true); setError('')
    try {
      onLogin(await api('/auth/login', { method: 'POST', body: creds || { email, password } }))
    } catch (err) { setError(err.message) }
    setBusy(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-brand">BrandCanon</h1>
        <p className="mt-1 text-sm text-slate-600">Every flag comes with a reason, a source and a fix.</p>
        <form onSubmit={submit} className="mt-6 space-y-3 rounded-lg border border-slate-200 bg-white p-5">
          <Field label="Email"><input className={inputCls} value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" /></Field>
          <Field label="Password"><input type="password" className={inputCls} value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></Field>
          <ErrorNote error={error} />
          <Button disabled={busy} className="w-full">{busy ? 'Signing in…' : 'Sign in'}</Button>
        </form>
        <div className="mt-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Demo accounts (fictional brand: AuroraBrew)</p>
          <div className="space-y-2">
            {DEMO.map(d => (
              <button key={d.email} disabled={busy} onClick={() => submit(null, { email: d.email, password: d.password })}
                className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:border-brand">
                <span><span className="text-sm font-semibold text-slate-800">{d.label}</span><span className="block text-xs text-slate-500">{d.note}</span></span>
                <span className="text-xs font-medium text-brand">Sign in →</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
