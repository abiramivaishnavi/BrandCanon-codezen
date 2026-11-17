import React, { useState } from 'react'
import { Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom'
import { getSession, setSession } from './api.js'
import Login from './pages/Login.jsx'
import Contents from './pages/Contents.jsx'
import NewContent from './pages/NewContent.jsx'
import ContentDetail from './pages/ContentDetail.jsx'
import Brand from './pages/Brand.jsx'
import Campaigns from './pages/Campaigns.jsx'
import Insights from './pages/Insights.jsx'

function Layout({ user, onLogout, children }) {
  const link = ({ isActive }) =>
    `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-white/15 text-white' : 'text-slate-200 hover:bg-white/10'}`
  return (
    <div className="min-h-screen">
      <header className="bg-brand">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
          <div className="text-lg font-bold tracking-tight text-white">BrandCanon</div>
          <nav className="flex flex-1 gap-1">
            <NavLink to="/" end className={link}>{user.role === 'reviewer' ? 'Review queue' : 'Content'}</NavLink>
            <NavLink to="/campaigns" className={link}>Campaign Check</NavLink>
            <NavLink to="/brand" className={link}>Brand knowledge</NavLink>
            {user.role !== 'creator' && <NavLink to="/insights" className={link}>Insights</NavLink>}
          </nav>
          <div className="text-right text-xs text-slate-200">
            <div className="font-semibold text-white">{user.name}</div>
            <div className="capitalize">{user.role}</div>
          </div>
          <button onClick={onLogout} className="rounded-md border border-white/30 px-3 py-1 text-xs font-medium text-white hover:bg-white/10">Log out</button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  )
}

export default function App() {
  const [session, setSess] = useState(getSession())
  const navigate = useNavigate()
  const login = (s) => { setSession(s); setSess(s); navigate('/') }
  const logout = () => { setSession(null); setSess(null); navigate('/login') }

  if (!session) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={login} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }
  const user = session.user
  return (
    <Layout user={user} onLogout={logout}>
      <Routes>
        <Route path="/" element={<Contents user={user} />} />
        <Route path="/new" element={<NewContent />} />
        <Route path="/content/:id" element={<ContentDetail user={user} />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/brand" element={<Brand user={user} />} />
        <Route path="/insights" element={user.role === 'creator' ? <Navigate to="/" replace /> : <Insights />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
