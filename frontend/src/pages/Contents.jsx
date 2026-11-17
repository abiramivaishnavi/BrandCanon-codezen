import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { Button, Card, Empty, ErrorNote, Pill, timeAgo } from '../ui.jsx'

export default function Contents({ user }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState(user.role === 'reviewer' ? 'in_review' : 'all')

  useEffect(() => { api('/contents').then(setItems).catch(e => setError(e.message)) }, [])

  const shown = (items || []).filter(i => filter === 'all' || i.status === filter)
  const tabs = [['all', 'All'], ['draft', 'Draft'], ['in_review', 'In review'], ['changes_requested', 'Changes requested'], ['approved', 'Approved']]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{user.role === 'reviewer' ? 'Review queue' : 'Content'}</h1>
          <p className="text-sm text-slate-500">
            {user.role === 'reviewer' ? 'Content waiting for your decision.' : 'Everything is checked against the approved brand knowledge before it can be approved.'}
          </p>
        </div>
        {user.role !== 'reviewer' && <Link to="/new"><Button>+ Check new content</Button></Link>}
      </div>
      <div className="flex gap-1">
        {tabs.map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)}
            className={`rounded-md px-3 py-1 text-sm ${filter === key ? 'bg-brand text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}>
            {label}{items && <span className="ml-1 opacity-70">{items.filter(i => key === 'all' || i.status === key).length}</span>}
          </button>
        ))}
      </div>
      <ErrorNote error={error} />
      <Card>
        {!items ? <Empty>Loading…</Empty> : shown.length === 0 ? <Empty>Nothing here yet.</Empty> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2 font-semibold">Title</th><th className="pb-2 font-semibold">Type</th><th className="pb-2 font-semibold">Campaign</th>
                <th className="pb-2 font-semibold">Creator</th><th className="pb-2 font-semibold">Open issues</th><th className="pb-2 font-semibold">Status</th><th className="pb-2 font-semibold">Updated</th>
              </tr>
            </thead>
            <tbody>
              {shown.map(i => (
                <tr key={i.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="py-2.5"><Link to={`/content/${i.id}`} className="font-medium text-brand hover:underline">{i.title}</Link> <span className="text-xs text-slate-400">v{i.version}</span></td>
                  <td className="uppercase text-xs text-slate-500">{i.kind}</td>
                  <td className="text-slate-600">{i.campaign || '—'}</td>
                  <td className="text-slate-600">{i.creator}</td>
                  <td>
                    {i.open_findings === 0 ? <span className="text-emerald-700">None</span> : (
                      <span>{i.open_findings}{i.blocking_open > 0 && <span className="ml-2"><Pill kind="blocking">{i.blocking_open} blocking</Pill></span>}</span>
                    )}
                  </td>
                  <td><Pill kind={i.status} /></td>
                  <td className="text-slate-500">{timeAgo(i.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
