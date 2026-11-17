// Small fetch wrapper: adds the login token and turns API errors into readable messages.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function getSession() {
  try { return JSON.parse(localStorage.getItem('bc_session')) } catch { return null }
}
export function setSession(s) {
  if (s) localStorage.setItem('bc_session', JSON.stringify(s))
  else localStorage.removeItem('bc_session')
}

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const session = getSession()
  if (session?.token) headers.Authorization = `Bearer ${session.token}`
  let payload
  if (form) payload = form                       // FormData (file uploads)
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res
  try {
    res = await fetch(API_URL + path, { method, headers, body: payload })
  } catch {
    throw new Error('Cannot reach the server. It may be waking up (free hosting sleeps) — try again in 30 seconds.')
  }
  if (res.status === 401 && path !== '/auth/login') {
    setSession(null)
    window.location.href = '/login'
    throw new Error('Please log in again')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map(x => x.msg).join(', ') : 'Something went wrong')
  }
  return data
}

// Files need the auth header, so we fetch them as blobs instead of using <img src>.
export async function fileUrl(path) {
  const session = getSession()
  const res = await fetch(API_URL + path, { headers: { Authorization: `Bearer ${session?.token}` } })
  if (!res.ok) return null
  return URL.createObjectURL(await res.blob())
}
