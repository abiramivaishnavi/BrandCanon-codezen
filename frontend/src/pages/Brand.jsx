import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Button, Card, Empty, ErrorNote, Field, Pill, inputCls } from '../ui.jsx'

const CATEGORIES = ['tone', 'claim', 'messaging', 'visual', 'accessibility']

function Rules({ isAdmin }) {
  const [rules, setRules] = useState([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [form, setForm] = useState({ category: 'tone', text: '', severity: 'major' })
  const [editing, setEditing] = useState(null)
  const load = () => api('/brand/rules').then(setRules).catch(e => setError(e.message))
  useEffect(() => { load() }, [])

  async function upload(e) {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData(); fd.append('file', file)
    setError(''); setMsg('Reading document…')
    try { const r = await api('/brand/rules/upload', { method: 'POST', form: fd }); setMsg(`${r.rules_added} new rule(s) added from ${file.name}.`); load() }
    catch (err) { setError(err.message); setMsg('') }
    e.target.value = ''
  }
  async function add(e) {
    e.preventDefault(); setError('')
    try { await api('/brand/rules', { method: 'POST', body: form }); setForm({ ...form, text: '' }); load() } catch (err) { setError(err.message) }
  }
  async function save() {
    try { await api(`/brand/rules/${editing.id}`, { method: 'PUT', body: editing }); setEditing(null); load() } catch (err) { setError(err.message) }
  }

  return (
    <div className="space-y-4">
      {isAdmin && (
        <Card title="Add guidelines">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm text-slate-600">Upload a guideline document. Each bullet or sentence becomes one numbered, versioned rule.</p>
              <input type="file" accept=".pdf,.docx,.txt,.md" onChange={upload} className="text-sm" />
              {msg && <p className="mt-2 text-sm text-emerald-700">{msg}</p>}
            </div>
            <form onSubmit={add} className="space-y-2">
              <div className="flex gap-2">
                <select className={inputCls} value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
                <select className={inputCls} value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })}><option>major</option><option>minor</option></select>
              </div>
              <textarea className={inputCls} rows={2} placeholder="Or type one rule…" value={form.text} onChange={e => setForm({ ...form, text: e.target.value })} />
              <Button disabled={form.text.trim().length < 10}>Add rule</Button>
            </form>
          </div>
          <div className="mt-3"><ErrorNote error={error} /></div>
        </Card>
      )}
      <Card title={`Rules (${rules.length})`}>
        {rules.length === 0 ? <Empty>No rules yet.</Empty> : (
          <ul className="divide-y divide-slate-100">
            {rules.map(r => (
              <li key={r.id} className="flex items-start gap-3 py-2.5 text-sm">
                <span className="w-16 shrink-0 font-mono text-xs font-semibold text-brand">{r.code}<span className="block font-normal text-slate-400">v{r.version}</span></span>
                <span className="w-24 shrink-0 text-xs capitalize text-slate-500">{r.category}</span>
                {editing?.id === r.id ? (
                  <span className="flex-1 space-y-2">
                    <textarea className={inputCls} rows={2} value={editing.text} onChange={e => setEditing({ ...editing, text: e.target.value })} />
                    <span className="flex gap-2"><Button onClick={save}>Save (creates v{r.version + 1})</Button><Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button></span>
                  </span>
                ) : <span className="flex-1 text-slate-700">{r.text}</span>}
                {isAdmin && editing?.id !== r.id && (
                  <span className="flex shrink-0 gap-2 text-xs">
                    <button className="font-medium text-brand hover:underline" onClick={() => setEditing({ ...r })}>Edit</button>
                    <button className="font-medium text-red-600 hover:underline" onClick={async () => { await api(`/brand/rules/${r.id}`, { method: 'DELETE' }); load() }}>Retire</button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

function Facts({ isAdmin }) {
  const empty = { label: '', value: '', value_type: 'price', keywords: '', valid_until: '' }
  const [facts, setFacts] = useState([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const load = () => api('/brand/facts').then(setFacts).catch(e => setError(e.message))
  useEffect(() => { load() }, [])
  async function add(e) {
    e.preventDefault(); setError('')
    try { await api('/brand/facts', { method: 'POST', body: { ...form, valid_until: form.valid_until || null } }); setForm(empty); load() } catch (err) { setError(err.message) }
  }
  return (
    <div className="space-y-4">
      <Card title="Claims Ledger – approved facts">
        <p className="mb-3 text-sm text-slate-600">Numbers in content are compared with these facts by code (Verified lane). A fact applies when one of its keywords appears near the number. Facts past their “valid until” date are flagged as outdated.</p>
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="pb-2">ID</th><th className="pb-2">Fact</th><th className="pb-2">Approved value</th><th className="pb-2">Type</th><th className="pb-2">Keywords</th><th className="pb-2">Valid until</th><th /></tr></thead>
          <tbody>
            {facts.map(f => (
              <tr key={f.id} className="border-b border-slate-100 last:border-0">
                <td className="py-2 font-mono text-xs font-semibold text-brand">{f.code}</td>
                <td>{f.label}</td><td className="font-semibold">{f.value}</td><td className="text-slate-500">{f.value_type}</td>
                <td className="text-slate-500">{f.keywords}</td>
                <td>{f.valid_until ? <span className={f.expired ? 'font-semibold text-red-700' : ''}>{f.valid_until}{f.expired && ' (expired)'}</span> : <span className="text-slate-400">no end date</span>}</td>
                <td className="text-right">{isAdmin && <button className="text-xs font-medium text-red-600 hover:underline" onClick={async () => { await api(`/brand/facts/${f.id}`, { method: 'DELETE' }); load() }}>Delete</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {isAdmin && (
        <Card title="Add a fact">
          <form onSubmit={add} className="grid gap-3 md:grid-cols-5">
            <Field label="Fact"><input className={inputCls} value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} placeholder="Cold brew 500ml price" /></Field>
            <Field label="Approved value"><input className={inputCls} value={form.value} onChange={e => setForm({ ...form, value: e.target.value })} placeholder="349" /></Field>
            <Field label="Type"><select className={inputCls} value={form.value_type} onChange={e => setForm({ ...form, value_type: e.target.value })}>
              <option value="price">price</option><option value="percent">percent</option><option value="number">number</option><option value="claim">claim (supported phrase)</option></select></Field>
            <Field label="Keywords (comma separated)"><input className={inputCls} value={form.keywords} onChange={e => setForm({ ...form, keywords: e.target.value })} placeholder="cold brew" /></Field>
            <Field label="Valid until (optional)"><input type="date" className={inputCls} value={form.valid_until} onChange={e => setForm({ ...form, valid_until: e.target.value })} /></Field>
            <div className="md:col-span-5"><Button disabled={!form.label || !form.value || !form.keywords}>Add fact</Button></div>
          </form>
          <div className="mt-3"><ErrorNote error={error} /></div>
        </Card>
      )}
    </div>
  )
}

function Terms({ isAdmin }) {
  const [terms, setTerms] = useState([])
  const [form, setForm] = useState({ preferred: '', variants: '', note: '', severity: 'major' })
  const load = () => api('/brand/terms').then(setTerms).catch(() => {})
  useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <Card title="Terminology">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="pb-2">ID</th><th className="pb-2">Use this</th><th className="pb-2">Not these</th><th className="pb-2">Note</th><th className="pb-2">Severity</th><th /></tr></thead>
          <tbody>
            {terms.map(t => (
              <tr key={t.id} className="border-b border-slate-100 last:border-0">
                <td className="py-2 font-mono text-xs font-semibold text-brand">{t.code}</td>
                <td className="font-semibold text-emerald-800">{t.preferred || <span className="font-normal italic text-slate-500">(banned – remove)</span>}</td>
                <td className="text-red-700">{t.variants}</td><td className="text-slate-500">{t.note}</td><td><Pill kind={t.severity} /></td>
                <td className="text-right">{isAdmin && <button className="text-xs font-medium text-red-600 hover:underline" onClick={async () => { await api(`/brand/terms/${t.id}`, { method: 'DELETE' }); load() }}>Delete</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {isAdmin && (
        <Card title="Add a term">
          <form className="grid gap-3 md:grid-cols-4" onSubmit={async e => { e.preventDefault(); await api('/brand/terms', { method: 'POST', body: form }); setForm({ preferred: '', variants: '', note: '', severity: 'major' }); load() }}>
            <Field label="Approved term" hint="Leave empty to ban the words"><input className={inputCls} value={form.preferred} onChange={e => setForm({ ...form, preferred: e.target.value })} /></Field>
            <Field label="Wrong / banned forms (comma separated)"><input className={inputCls} value={form.variants} onChange={e => setForm({ ...form, variants: e.target.value })} /></Field>
            <Field label="Note"><input className={inputCls} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} /></Field>
            <Field label="Severity"><select className={inputCls} value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })}><option>major</option><option>minor</option><option>blocking</option></select></Field>
            <div className="md:col-span-4"><Button disabled={!form.variants.trim()}>Add term</Button></div>
          </form>
        </Card>
      )}
    </div>
  )
}

function Palette({ isAdmin }) {
  const [colors, setColors] = useState([])
  const [form, setForm] = useState({ name: '', hex: '#' })
  const [error, setError] = useState('')
  const load = () => api('/brand/palette').then(setColors).catch(() => {})
  useEffect(() => { load() }, [])
  return (
    <Card title="Approved colours">
      <p className="mb-3 text-sm text-slate-600">Dominant colours in uploaded images are measured and compared with this palette. Whites, greys and black are always allowed.</p>
      <div className="flex flex-wrap gap-3">
        {colors.map(c => (
          <div key={c.id} className="w-36 overflow-hidden rounded-lg border border-slate-200">
            <div className="h-16" style={{ background: c.hex }} />
            <div className="p-2 text-xs"><div className="font-semibold text-slate-800">{c.name}</div><div className="font-mono text-slate-500">{c.hex}</div>
              {isAdmin && <button className="mt-1 font-medium text-red-600 hover:underline" onClick={async () => { await api(`/brand/palette/${c.id}`, { method: 'DELETE' }); load() }}>Remove</button>}</div>
          </div>
        ))}
      </div>
      {isAdmin && (
        <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={async e => { e.preventDefault(); setError(''); try { await api('/brand/palette', { method: 'POST', body: form }); setForm({ name: '', hex: '#' }); load() } catch (err) { setError(err.message) } }}>
          <Field label="Name"><input className={inputCls} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Hex"><input className={inputCls} value={form.hex} onChange={e => setForm({ ...form, hex: e.target.value })} placeholder="#E2703A" /></Field>
          <Button disabled={!form.name}>Add colour</Button>
        </form>
      )}
      <div className="mt-3"><ErrorNote error={error} /></div>
    </Card>
  )
}

export default function Brand({ user }) {
  const [tab, setTab] = useState('rules')
  const isAdmin = user.role === 'admin'
  const tabs = [['rules', 'Guideline rules'], ['facts', 'Claims Ledger'], ['terms', 'Terminology'], ['palette', 'Colours']]
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Brand knowledge</h1>
        <p className="text-sm text-slate-500">The approved source of truth that all content is checked against. {isAdmin ? '' : 'Only the Brand Admin can change it.'}</p>
      </div>
      <div className="flex gap-1">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} className={`rounded-md px-3 py-1 text-sm ${tab === k ? 'bg-brand text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}>{label}</button>
        ))}
      </div>
      {tab === 'rules' && <Rules isAdmin={isAdmin} />}
      {tab === 'facts' && <Facts isAdmin={isAdmin} />}
      {tab === 'terms' && <Terms isAdmin={isAdmin} />}
      {tab === 'palette' && <Palette isAdmin={isAdmin} />}
    </div>
  )
}
