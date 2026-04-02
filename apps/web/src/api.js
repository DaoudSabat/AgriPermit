const BASE = '/api/v1'

function getToken() {
  return localStorage.getItem('agripermit_token')
}

async function request(path, options = {}) {
  const token = getToken()
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      ...options,
    })
  } catch {
    throw new Error('Cannot reach API server — is it running on port 8000?')
  }

  const text = await res.text()

  if (!text) {
    throw new Error(`API returned empty response (HTTP ${res.status})`)
  }

  let data
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error(`API returned non-JSON (HTTP ${res.status}): ${text.slice(0, 120)}`)
  }

  if (!res.ok) {
    const msg = data?.detail ?? `HTTP ${res.status}`
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return data
}

export function fetchPermits({ parcelId, status, gisFlagged, skip = 0, limit = 20 } = {}) {
  const params = new URLSearchParams()
  if (parcelId) params.set('parcel_id', parcelId)
  if (status) params.set('status', status)
  if (gisFlagged !== undefined) params.set('gis_flagged', gisFlagged)
  params.set('skip', skip)
  params.set('limit', limit)
  return request(`/permits?${params}`)
}

export function createPermit(body) {
  return request('/permits', { method: 'POST', body: JSON.stringify(body) })
}

export function approvePermit(permitId, body) {
  return request(`/permits/${permitId}/approve`, { method: 'POST', body: JSON.stringify(body) })
}

export function fetchParcels() {
  return request('/parcels')
}

export function checkLand({ parcelId, gush, helka, zone } = {}) {
  const params = new URLSearchParams()
  if (parcelId)    params.set('parcel_id', parcelId)
  if (gush != null) params.set('gush', gush)
  if (helka != null) params.set('helka', helka)
  if (zone)        params.set('zone', zone)
  return request(`/gis/check?${params}`)
}

export function login(username, password) {
  return request('/users/login', { method: 'POST', body: JSON.stringify({ username, password }) })
}

export function register(body) {
  return request('/users/register', { method: 'POST', body: JSON.stringify(body) })
}

export function fetchMe() {
  return request('/users/me')
}

export function fetchStats() {
  return request('/stats')
}

export function uploadDesign(formData) {
  // formData is a FormData object — don't set Content-Type, browser sets multipart boundary
  const token = localStorage.getItem('agripermit_token')
  return fetch('/api/v1/designs/upload', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  }).then(async res => {
    const text = await res.text()
    if (!text) throw new Error(`Empty response (HTTP ${res.status})`)
    const data = JSON.parse(text)
    if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`)
    return data
  })
}

export function fetchDesigns({ permitId, parcelId } = {}) {
  const params = new URLSearchParams()
  if (permitId) params.set('permit_id', permitId)
  if (parcelId) params.set('parcel_id', parcelId)
  return request(`/designs?${params}`)
}

export function registerOrg(body) {
  return request('/orgs/register', { method: 'POST', body: JSON.stringify(body) })
}

export function fetchMyOrg() {
  return request('/orgs/me')
}
