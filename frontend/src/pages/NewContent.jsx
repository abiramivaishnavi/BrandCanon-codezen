import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { Button, Card, ErrorNote, Field, inputCls } from '../ui.jsx'

export default function NewContent() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('text')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [altText, setAltText] = useState('')
  const [imageText, setImageText] = useState('')
  const [campaigns, setCampaigns] = useState([])
  const [campaignId, setCampaignId] = useState('')
  const [newCampaign, setNewCampaign] = useState('')
  const [aiOn, setAiOn] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/campaigns').then(setCampaigns).catch(() => {})
    api('/health').then(h => setAiOn(h.ai_enabled)).catch(() => {})
  }, [])

  const isImage = file && /\.(png|jpe?g|webp)$/i.test(file.name)

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setError('')
    const form = new FormData()
    form.append('title', title || (file ? file.name : 'Untitled'))
    if (mode === 'text') form.append('text', text)
    if (mode === 'file' && file) form.append('file', file)
    if (campaignId === 'new') form.append('campaign_name', newCampaign)
    else if (campaignId) form.append('campaign_id', campaignId)
    form.append('alt_text', altText)
    form.append('image_text', imageText)
    try {
      const res = await api('/contents', { method: 'POST', form })
      navigate(`/content/${res.id}`)
    } catch (err) { setError(err.message); setBusy(false) }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-bold text-slate-900">Check new content</h1>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Title"><input className={inputCls} value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Winter offer – Instagram caption" /></Field>
          <div className="flex gap-2">
            {[['text', 'Paste text'], ['file', 'Upload a file']].map(([m, label]) => (
              <button type="button" key={m} onClick={() => setMode(m)}
                className={`rounded-md border px-3 py-1.5 text-sm font-medium ${mode === m ? 'border-brand bg-brand text-white' : 'border-slate-300 bg-white text-slate-600'}`}>{label}</button>
            ))}
          </div>
          {mode === 'text' ? (
            <Field label="Content"><textarea className={inputCls} rows={8} value={text} onChange={e => setText(e.target.value)} placeholder="Paste a caption, email, job post or any draft…" /></Field>
          ) : (
            <>
              <Field label="File" hint="PDF, DOCX, TXT, PNG or JPG">
                <input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files[0] || null)} className="block w-full text-sm" />
              </Field>
              {isImage && (
                <>
                  <Field label="Alt text for this image" hint="A one-line description for people using screen readers.">
                    <input className={inputCls} value={altText} onChange={e => setAltText(e.target.value)} />
                  </Field>
                  <Field label={aiOn ? 'Text on the image (optional)' : 'Text on the image'}
                    hint={aiOn ? 'Leave empty and the vision model will read the text from the image.' : 'AI is not configured on this server, so type the words that appear on the poster.'}>
                    <textarea className={inputCls} rows={3} value={imageText} onChange={e => setImageText(e.target.value)} />
                  </Field>
                </>
              )}
            </>
          )}
          <Field label="Campaign (optional)" hint="Group a poster, caption and PDF in one campaign to compare them with Campaign Check.">
            <select className={inputCls} value={campaignId} onChange={e => setCampaignId(e.target.value)}>
              <option value="">No campaign</option>
              {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              <option value="new">+ New campaign…</option>
            </select>
          </Field>
          {campaignId === 'new' && <Field label="New campaign name"><input className={inputCls} value={newCampaign} onChange={e => setNewCampaign(e.target.value)} /></Field>}
          <ErrorNote error={error} />
          <div className="flex items-center gap-3">
            <Button disabled={busy}>{busy ? 'Checking…' : 'Run brand check'}</Button>
            {busy && <span className="text-sm text-slate-500">Extracting, running verified checks{aiOn ? ' and AI review' : ''}…</span>}
          </div>
        </form>
      </Card>
    </div>
  )
}
