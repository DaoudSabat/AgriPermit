import React, { createContext, useContext, useState, useEffect } from 'react'
import { fetchMe, fetchMyOrg } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [org, setOrg] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('agripermit_token')
    if (!token) { setReady(true); return }
    fetchMe()
      .then(u => {
        setUser(u)
        return fetchMyOrg().then(o => setOrg(o)).catch(() => {})
      })
      .catch(() => localStorage.removeItem('agripermit_token'))
      .finally(() => setReady(true))
  }, [])

  function signIn(tokenData) {
    localStorage.setItem('agripermit_token', tokenData.access_token)
    setUser({
      username: tokenData.username,
      full_name: tokenData.full_name,
      role: tokenData.role,
    })
    fetchMyOrg().then(o => setOrg(o)).catch(() => {})
  }

  function signOut() {
    localStorage.removeItem('agripermit_token')
    setUser(null)
    setOrg(null)
  }

  return (
    <AuthContext.Provider value={{ user, org, ready, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
