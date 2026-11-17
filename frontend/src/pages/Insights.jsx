import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Card, Empty, ErrorNote, Pill, timeAgo } from '../ui.jsx'

const GAP_LABEL = { vague_or_strict: 'Possibly vague or too strict', unclear: 'Possibly unclear or not well known', missing_rule: 'Possible missing rule' }

function Stat({ label, value }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-4"><div className="text-2xl font-bold text-slate-900">{value}</div><div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div></div>
}

export default function Insights() {
  const [data, setData] = useState(null)
  const [audit, setAudit] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    api('/insights').then(setData).catch(e => setError(e.message))
    api('/audit').then(setAudit).catch(() => {})
  }, [])
  if (!data) return <div><ErrorNote error={error} /><Empty>Loading…</Empty></div>
  const t = data.totals
  const max = Math.max(1, ...data.top_rules.map(r => r.count))
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Guideline Clarity Insights</h1>
        <p className="text-sm text-slate-500">Which mistakes keep repeating, and where the guidelines themselves may need work. Early version: based on the content checked so far.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Content items" value={t.contents} />
        <Stat label="Issues found" value={t.findings} />
        <Stat label="Verified" value={t.by_lane.verified || 0} />
        <Stat label="Advisory (AI)" value={t.by_lane.advisory || 0} />
        <Stat label="Approved" value={t.by_status.approved || 0} />
      </div>

      <Card title="Guideline Gap signals">
        {data.gap_signals.length === 0 ? <Empty>No gap signals yet. They appear when a rule is dismissed repeatedly, broken across several pieces of content, or when the AI spots an issue no rule covers.</Empty> : (
          <ul className="space-y-3">
            {data.gap_signals.map((g, i) => (
              <li key={i} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2"><Pill kind="advisory">{GAP_LABEL[g.type] || g.type}</Pill><span className="font-semibold text-slate-900">{g.title}</span></div>
                {g.rule_text && <p className="mt-1 text-slate-700"><span className="font-mono text-xs font-semibold text-brand">{g.rule_code}</span> — {g.rule_text}</p>}
                <p className="mt-1 text-slate-700"><b>Evidence:</b> {g.evidence}</p>
                <p className="mt-1 text-slate-700"><b>Suggestion for the admin:</b> {g.suggestion}</p>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-slate-500">The system only suggests. The Brand Admin decides whether to change a guideline. Detecting conflicting rules is planned for Round 3.</p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Most frequent issues (by rule)" className="lg:col-span-2">
          {data.top_rules.length === 0 ? <Empty>No findings yet.</Empty> : (
            <ul className="space-y-2.5">
              {data.top_rules.map(r => (
                <li key={r.rule_code} className="text-sm">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate"><span className="font-mono text-xs font-semibold text-brand">{r.rule_code}</span> <span className="text-slate-700">{r.rule_text}</span></span>
                    <span className="shrink-0 text-xs text-slate-500">{r.count}× in {r.contents} item(s){r.dismissed > 0 && ` · ${r.dismissed} dismissed`}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded bg-slate-100"><div className="h-1.5 rounded bg-brand" style={{ width: `${(r.count / max) * 100}%` }} /></div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Issues by category">
          {Object.keys(t.by_category).length === 0 ? <Empty>No findings yet.</Empty> : (
            <ul className="space-y-1.5 text-sm">
              {Object.entries(t.by_category).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                <li key={k} className="flex justify-between"><span className="capitalize text-slate-700">{k}</span><span className="font-semibold">{v}</span></li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Audit log (latest 100 actions)">
        {audit.length === 0 ? <Empty>No activity yet.</Empty> : (
          <table className="w-full text-sm">
            <tbody>
              {audit.map(a => (
                <tr key={a.id} className="border-b border-slate-100 last:border-0">
                  <td className="w-28 py-1.5 text-xs text-slate-500">{timeAgo(a.created_at)}</td>
                  <td className="w-44 text-slate-700">{a.user}</td>
                  <td className="w-48 font-mono text-xs text-brand">{a.action}</td>
                  <td className="text-slate-600">{a.target} {a.detail && <span className="text-slate-400">— {a.detail}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
