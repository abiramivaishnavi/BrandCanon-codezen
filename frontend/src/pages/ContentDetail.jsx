import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fileUrl } from '../api.js'
import { Button, Card, Empty, ErrorNote, Pill, inputCls, timeAgo } from '../ui.jsx'

/* ---------- content with highlighted findings ---------- */
function highlightClass(f) {
  if (f.status === 'accepted') return 'bg-emerald-50 text-slate-400 line-through decoration-emerald-600'
  if (f.severity === 'blocking') return 'bg-red-100 border-b-2 border-red-500'
  if (f.lane === 'advisory') return 'bg-amber-100 border-b-2 border-amber-500'
  return 'bg-emerald-100 border-b-2 border-emerald-600'
}

function HighlightedText({ text, findings, activeId, onPick }) {
  const parts = useMemo(() => {
    const spans = findings
      .filter(f => f.start !== null && f.status !== 'dismissed' && f.status !== 'overridden')
      .sort((a, b) => a.start - b.start)
    const out = []
    let pos = 0
    for (const f of spans) {
      if (f.start < pos) continue            // skip overlapping spans
      if (f.start > pos) out.push({ text: text.slice(pos, f.start) })
      out.push({ text: text.slice(f.start, f.end), finding: f })
      pos = f.end
    }
    if (pos < text.length) out.push({ text: text.slice(pos) })
    return out
  }, [text, findings])

  if (!text) return <Empty>No text could be read from this content.</Empty>
  return (
    <div className="whitespace-pre-wrap text-[15px] leading-7 text-slate-800">
      {parts.map((p, i) => p.finding ? (
        <mark key={i} onClick={() => onPick(p.finding.id)} title={p.finding.reason}
          className={`cursor-pointer rounded-sm px-0.5 ${highlightClass(p.finding)} ${activeId === p.finding.id ? 'ring-2 ring-brand' : ''}`}>
          {p.text}
        </mark>
      ) : <span key={i}>{p.text}</span>)}
    </div>
  )
}

/* ---------- one Evidence Card ---------- */
function EvidenceCard({ f, active, canAct, canFix, onChange, cardRef }) {
  const [mode, setMode] = useState(null)        // null | 'dismiss' | 'edit'
  const [note, setNote] = useState('')
  const [replacement, setReplacement] = useState(f.replacement || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function patch(body) {
    setBusy(true); setError('')
    try { await api(`/findings/${f.id}`, { method: 'PATCH', body }); setMode(null); onChange() }
    catch (e) { setError(e.message) }
    setBusy(false)
  }

  const resolved = f.status !== 'open'
  return (
    <div ref={cardRef} className={`rounded-lg border bg-white p-3 ${active ? 'border-brand ring-1 ring-brand' : 'border-slate-200'} ${resolved ? 'opacity-70' : ''}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        <Pill kind={f.lane}>{f.lane === 'verified' ? 'Verified' : 'Advisory · AI'}</Pill>
        <Pill kind={f.severity} />
        <span className="text-xs capitalize text-slate-500">{f.category}</span>
        {resolved && <span className="ml-auto"><Pill kind={f.status} /></span>}
      </div>
      {f.quote && <p className="mt-2 text-sm font-medium text-slate-900">“{f.quote}”</p>}
      <dl className="mt-2 space-y-1.5 text-[13px]">
        <div className="flex gap-2"><dt className="w-14 shrink-0 font-semibold text-slate-500">Source</dt>
          <dd className="text-slate-700"><span className="font-mono text-xs font-semibold text-brand">{f.rule_code} v{f.rule_version}</span> — {f.rule_text}</dd></div>
        <div className="flex gap-2"><dt className="w-14 shrink-0 font-semibold text-slate-500">Why</dt><dd className="text-slate-700">{f.reason}</dd></div>
        <div className="flex gap-2"><dt className="w-14 shrink-0 font-semibold text-slate-500">Fix</dt>
          <dd className="text-slate-700">
            {f.replacement !== null && f.quote ? (
              <span><span className="text-red-700 line-through">{f.quote}</span> → <span className="font-semibold text-emerald-800">{f.replacement || '(remove)'}</span></span>
            ) : f.suggestion}
          </dd></div>
        {f.resolution_note && <div className="flex gap-2"><dt className="w-14 shrink-0 font-semibold text-slate-500">Note</dt><dd className="italic text-slate-600">{f.resolution_note}</dd></div>}
      </dl>

      {canAct && !resolved && mode === null && (
        <div className="mt-3 flex flex-wrap gap-2">
          {canFix && f.replacement !== null && f.start !== null && <Button disabled={busy} onClick={() => patch({ status: 'accepted' })}>Accept fix</Button>}
          {canFix && f.start !== null && <Button variant="secondary" onClick={() => setMode('edit')}>{f.replacement !== null ? 'Edit fix' : 'Write a fix'}</Button>}
          {f.severity !== 'blocking' && <Button variant="ghost" onClick={() => setMode('dismiss')}>Dismiss</Button>}
        </div>
      )}
      {canAct && resolved && f.status !== 'overridden' && (
        <div className="mt-2"><button className="text-xs font-medium text-brand hover:underline" onClick={() => patch({ status: 'open' })}>Undo</button></div>
      )}
      {mode === 'edit' && (
        <div className="mt-3 space-y-2">
          <input className={inputCls} value={replacement} onChange={e => setReplacement(e.target.value)} placeholder={`Replace “${f.quote}” with…`} />
          <div className="flex gap-2">
            <Button disabled={busy || !replacement.trim()} onClick={() => patch({ status: 'accepted', replacement })}>Accept my fix</Button>
            <Button variant="ghost" onClick={() => setMode(null)}>Cancel</Button>
          </div>
        </div>
      )}
      {mode === 'dismiss' && (
        <div className="mt-3 space-y-2">
          <input className={inputCls} value={note} onChange={e => setNote(e.target.value)} placeholder="Why is this not a problem? (helps improve the guidelines)" />
          <div className="flex gap-2">
            <Button variant="secondary" disabled={busy} onClick={() => patch({ status: 'dismissed', note })}>Dismiss with reason</Button>
            <Button variant="ghost" onClick={() => setMode(null)}>Cancel</Button>
          </div>
        </div>
      )}
      <div className="mt-2"><ErrorNote error={error} /></div>
    </div>
  )
}

/* ---------- the page ---------- */
export default function ContentDetail({ user }) {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [viewVersion, setViewVersion] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [activeId, setActiveId] = useState(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [imgUrl, setImgUrl] = useState(null)
  const [comment, setComment] = useState('')
  const [reviewComment, setReviewComment] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [newFile, setNewFile] = useState(null)
  const cardRefs = useRef({})

  async function load(version = viewVersion) {
    try {
      const d = await api(`/contents/${id}${version ? `?version=${version}` : ''}`)
      setData(d)
      if (d.kind === 'image' && d.has_file) setImgUrl(await fileUrl(`/contents/${id}/file?version=${d.viewing_version}`))
    } catch (e) { setError(e.message) }
  }
  useEffect(() => { load(viewVersion) }, [id, viewVersion])   // eslint-disable-line

  async function act(label, fn) {
    setBusy(label); setError('')
    try { await fn(); setViewVersion(null); await load(null) } catch (e) { setError(e.message) }
    setBusy('')
  }

  function pick(fid) {
    setActiveId(fid)
    cardRefs.current[fid]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  if (!data) return <div className="space-y-3"><ErrorNote error={error} /><Empty>Loading…</Empty></div>

  const latest = data.viewing_version === data.version
  const isOwner = user.role !== 'reviewer' && (user.role === 'admin' || data.creator_id === user.id)
  const canEdit = isOwner && latest && ['draft', 'changes_requested'].includes(data.status)
  const canReview = (user.role === 'reviewer' || user.role === 'admin') && latest && data.status === 'in_review'
  const open = data.findings.filter(f => f.status === 'open')
  const blockingOpen = open.filter(f => f.severity === 'blocking')
  const acceptedToApply = data.findings.filter(f => f.status === 'accepted' && f.replacement !== null && f.start !== null)
  const check = data.meta?.check || {}
  const order = { blocking: 0, major: 1, minor: 2 }
  const cards = [...data.findings].sort((a, b) => (a.status !== 'open') - (b.status !== 'open') || order[a.severity] - order[b.severity])

  async function saveDraft() {
    const form = new FormData()
    form.append('text', draft)
    form.append('note', 'Edited by creator')
    await api(`/contents/${id}/versions`, { method: 'POST', form })
    setEditing(false)
  }
  async function uploadNew() {
    const form = new FormData()
    form.append('file', newFile)
    form.append('note', 'New file uploaded')
    form.append('alt_text', data.meta?.alt_text || '')
    await api(`/contents/${id}/versions`, { method: 'POST', form })
    setNewFile(null)
  }

  return (
    <div className="space-y-4">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/" className="text-xs font-medium text-brand hover:underline">← Back</Link>
          <h1 className="mt-1 text-xl font-bold text-slate-900">{data.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <Pill kind={data.status} />
            <span className="uppercase text-xs">{data.kind}</span>
            <span>· by {data.creator}</span>
            {data.campaign && <span>· Campaign: <Link className="text-brand hover:underline" to="/campaigns">{data.campaign}</Link></span>}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-500">Version</span>
          <select className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm" value={data.viewing_version}
            onChange={e => setViewVersion(Number(e.target.value) === data.version ? null : Number(e.target.value))}>
            {data.versions.map(v => <option key={v.number} value={v.number}>v{v.number}{v.number === data.version ? ' (latest)' : ''} – {v.note}</option>)}
          </select>
        </div>
      </div>

      {!latest && <div className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-600">You are viewing an older version (read-only).</div>}
      <ErrorNote error={error} />

      {/* check summary */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm">
        <span><b>{open.length}</b> open issue{open.length === 1 ? '' : 's'}</span>
        <span className={blockingOpen.length ? 'font-semibold text-red-700' : 'text-slate-500'}>{blockingOpen.length} blocking</span>
        <span className="text-slate-500">Verified checks: {check.verified ?? '–'}</span>
        <span className="text-slate-500">
          AI review: {check.ai_used ? `${check.advisory} finding(s), ${check.rules_retrieved} rules retrieved, ${check.ai_rejected} rejected by validator`
            : data.ai_enabled ? 'no findings returned' : 'off (no API key set) – verified lane only'}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        {/* left: the content */}
        <div className="space-y-4 lg:col-span-3">
          <Card title="Content" action={canEdit && data.kind !== 'image' && !editing &&
            <Button variant="secondary" onClick={() => { setDraft(data.text); setEditing(true) }}>Edit text</Button>}>
            {data.kind === 'image' && imgUrl && <img src={imgUrl} alt={data.meta?.alt_text || 'Uploaded creative'} className="mb-3 max-h-96 rounded border border-slate-200" />}
            {data.kind === 'image' && (
              <div className="mb-3 space-y-2 text-xs text-slate-500">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">Dominant colours:</span>
                  {(data.colors || []).map(c => (
                    <span key={c.hex} className="inline-flex items-center gap-1"><span className="inline-block h-4 w-4 rounded border border-slate-300" style={{ background: c.hex }} />{c.hex} {Math.round(c.share * 100)}%</span>
                  ))}
                </div>
                <div><span className="font-semibold">Alt text:</span> {data.meta?.alt_text || <i>none provided</i>} · <span className="font-semibold">Text read by:</span> {data.meta?.text_source}</div>
              </div>
            )}
            {editing ? (
              <div className="space-y-2">
                <textarea className={inputCls} rows={12} value={draft} onChange={e => setDraft(e.target.value)} />
                <div className="flex gap-2">
                  <Button disabled={!!busy} onClick={() => act('save', saveDraft)}>{busy === 'save' ? 'Saving & re-checking…' : 'Save as new version & re-check'}</Button>
                  <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <HighlightedText text={data.text} findings={data.findings} activeId={activeId} onPick={pick} />
            )}
            <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
              <span><span className="mr-1 inline-block h-2.5 w-4 rounded-sm border-b-2 border-red-500 bg-red-100 align-middle" />Blocking</span>
              <span><span className="mr-1 inline-block h-2.5 w-4 rounded-sm border-b-2 border-emerald-600 bg-emerald-100 align-middle" />Verified by code</span>
              <span><span className="mr-1 inline-block h-2.5 w-4 rounded-sm border-b-2 border-amber-500 bg-amber-100 align-middle" />Advisory (AI suggestion)</span>
            </div>
          </Card>

          {/* creator actions */}
          {canEdit && (
            <Card title="Next step">
              <div className="flex flex-wrap items-center gap-2">
                {data.kind !== 'image' && (
                  <Button disabled={!!busy || acceptedToApply.length === 0} onClick={() => act('apply', () => api(`/contents/${id}/apply-fixes`, { method: 'POST' }))}>
                    {busy === 'apply' ? 'Applying…' : `Apply ${acceptedToApply.length} accepted fix${acceptedToApply.length === 1 ? '' : 'es'}`}
                  </Button>
                )}
                <Button variant="secondary" disabled={!!busy} onClick={() => act('check', () => api(`/contents/${id}/check`, { method: 'POST' }))}>{busy === 'check' ? 'Checking…' : 'Re-run check'}</Button>
                <Button variant="secondary" disabled={!!busy} onClick={() => act('submit', () => api(`/contents/${id}/submit`, { method: 'POST' }))}>Submit for review</Button>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-sm">
                <span className="text-slate-500">Upload a corrected file:</span>
                <input type="file" className="text-sm" onChange={e => setNewFile(e.target.files[0] || null)} />
                {newFile && <Button variant="secondary" disabled={!!busy} onClick={() => act('upload', uploadNew)}>{busy === 'upload' ? 'Uploading…' : 'Save as new version'}</Button>}
              </div>
              {data.kind === 'image' && <p className="mt-2 text-xs text-slate-500">Images cannot be edited here. Correct the design in your design tool and upload the new file.</p>}
              {blockingOpen.length > 0 && <p className="mt-2 text-xs text-red-700">{blockingOpen.length} blocking issue(s) are open. A reviewer cannot approve until they are fixed or overridden with a reason.</p>}
            </Card>
          )}
          {isOwner && latest && data.status === 'in_review' && <p className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">Submitted. Waiting for a reviewer.</p>}
          {isOwner && latest && data.status === 'approved' && <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">Approved and ready to publish. BrandCanon never publishes automatically; a person publishes this content.</p>}

          {/* reviewer actions */}
          {canReview && (
            <Card title="Review decision">
              <textarea className={inputCls} rows={2} value={reviewComment} onChange={e => setReviewComment(e.target.value)} placeholder="Comment for the creator (required when requesting changes)" />
              {blockingOpen.length > 0 && (
                <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-3">
                  <p className="text-sm font-medium text-red-800">{blockingOpen.length} blocking issue(s) are still open.</p>
                  <p className="mt-0.5 text-xs text-red-700">To approve anyway you must write a reason. The override is saved in the audit log.</p>
                  <input className={`${inputCls} mt-2`} value={overrideReason} onChange={e => setOverrideReason(e.target.value)} placeholder="Override reason (e.g. offer extended, confirmed by brand head on 17 Nov)" />
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <Button disabled={!!busy} onClick={() => act('approve', () => api(`/contents/${id}/review`, { method: 'POST', body: { decision: 'approve', comment: reviewComment, override_reason: overrideReason } }))}>
                  {blockingOpen.length > 0 ? 'Approve with override' : 'Approve'}
                </Button>
                <Button variant="danger" disabled={!!busy} onClick={() => act('changes', () => api(`/contents/${id}/review`, { method: 'POST', body: { decision: 'request_changes', comment: reviewComment } }))}>Request changes</Button>
              </div>
            </Card>
          )}

          {/* comments */}
          <Card title={`Comments (${data.comments.length})`}>
            {data.comments.length === 0 && <p className="text-sm text-slate-500">No comments yet.</p>}
            <ul className="space-y-3">
              {data.comments.map(c => (
                <li key={c.id} className="text-sm">
                  <span className="font-semibold text-slate-800">{c.user}</span> <span className="text-xs capitalize text-slate-400">{c.role} · {timeAgo(c.created_at)}</span>
                  <p className="text-slate-700">{c.text}</p>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex gap-2">
              <input className={inputCls} value={comment} onChange={e => setComment(e.target.value)} placeholder="Add a comment…" />
              <Button variant="secondary" disabled={!comment.trim() || !!busy}
                onClick={() => act('comment', async () => { await api(`/contents/${id}/comments`, { method: 'POST', body: { text: comment } }); setComment('') })}>Post</Button>
            </div>
          </Card>
        </div>

        {/* right: evidence cards */}
        <div className="space-y-3 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-900">Evidence Cards ({data.findings.length})</h2>
          {data.findings.length === 0 && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">No issues found against the current brand knowledge.</div>
          )}
          {cards.map(f => (
            <EvidenceCard key={f.id} f={f} active={activeId === f.id} canAct={canEdit} canFix={data.kind !== 'image'}
              onChange={() => load(null)} cardRef={el => (cardRefs.current[f.id] = el)} />
          ))}
        </div>
      </div>
    </div>
  )
}
