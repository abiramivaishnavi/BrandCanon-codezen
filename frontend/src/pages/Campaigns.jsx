import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { Card, Empty, ErrorNote, Pill } from '../ui.jsx'

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [selected, setSelected] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/campaigns').then(list => { setCampaigns(list); if (list.length) setSelected(list[0].id) }).catch(e => setError(e.message))
  }, [])
  useEffect(() => {
    if (!selected) return
    setResult(null)
    api(`/campaigns/${selected}/check`).then(setResult).catch(e => setError(e.message))
  }, [selected])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Campaign Check</h1>
        <p className="text-sm text-slate-500">Compares prices, discounts and dates across every piece of content in a campaign, so the poster, caption and PDF all say the same thing.</p>
      </div>
      <ErrorNote error={error} />
      <div className="flex flex-wrap gap-2">
        {campaigns.map(c => (
          <button key={c.id} onClick={() => setSelected(c.id)}
            className={`rounded-md px-3 py-1.5 text-sm ${selected === c.id ? 'bg-brand text-white' : 'border border-slate-200 bg-white text-slate-600'}`}>{c.name} <span className="opacity-70">({c.items})</span></button>
        ))}
        {campaigns.length === 0 && <Empty>No campaigns yet. Choose a campaign when you upload content.</Empty>}
      </div>
      {result && (
        <>
          {result.items.length < 2 ? (
            <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">Add at least two pieces of content to this campaign to compare them.</div>
          ) : result.mismatches.length === 0 ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">Prices, discounts and dates agree across all {result.items.length} items.</div>
          ) : (
            <div className="space-y-3">
              {result.mismatches.map(m => (
                <div key={m.type} className="rounded-lg border border-red-200 bg-white">
                  <div className="flex items-center gap-2 border-b border-red-100 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800"><Pill kind="blocking">Mismatch</Pill>{m.message}</div>
                  <table className="w-full text-sm">
                    <tbody>
                      {m.items.map(i => (
                        <tr key={i.content_id} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-2"><Link className="font-medium text-brand hover:underline" to={`/content/${i.content_id}`}>{i.title}</Link> <span className="text-xs uppercase text-slate-400">{i.kind}</span></td>
                          <td className="px-4 py-2 font-semibold">{i.values.map(v => m.type === 'price' ? `Rs ${v}` : m.type === 'discount' ? `${v}%` : v).join(', ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
          <Card title="Values found in each item">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Content</th><th className="pb-2">Type</th><th className="pb-2">Prices</th><th className="pb-2">Discounts</th><th className="pb-2">Dates</th><th className="pb-2">Status</th></tr></thead>
              <tbody>
                {result.items.map(i => (
                  <tr key={i.content_id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2"><Link className="font-medium text-brand hover:underline" to={`/content/${i.content_id}`}>{i.title}</Link></td>
                    <td className="text-xs uppercase text-slate-500">{i.kind}</td>
                    <td>{i.values.price.map(v => `Rs ${v}`).join(', ') || '—'}</td>
                    <td>{i.values.discount.map(v => `${v}%`).join(', ') || '—'}</td>
                    <td>{i.values.date.join(', ') || '—'}</td>
                    <td><Pill kind={i.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  )
}
