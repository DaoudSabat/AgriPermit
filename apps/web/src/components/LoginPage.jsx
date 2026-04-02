import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { login, registerOrg } from '../api'
import { useAuth } from '../AuthContext'
import LanguageSwitcher from './LanguageSwitcher'

function slugify(s) {
  return s.toLowerCase().trim().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')
}

export default function LoginPage() {
  const { t } = useTranslation()
  const { signIn } = useAuth()
  const [mode, setMode] = useState('login')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const [orgName, setOrgName] = useState('')
  const [orgSlug, setOrgSlug] = useState('')
  const [adminUsername, setAdminUsername] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminName, setAdminName] = useState('')
  const [regPassword, setRegPassword] = useState('')

  const [error, setError]     = useState(null)
  const [loading, setLoading] = useState(false)

  function handleOrgNameChange(e) {
    const val = e.target.value
    setOrgName(val)
    setOrgSlug(slugify(val))
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await login(username.trim(), password)
      signIn(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await registerOrg({
        org_name: orgName,
        org_slug: orgSlug,
        admin_username: adminUsername,
        admin_email: adminEmail,
        admin_full_name: adminName,
        password: regPassword,
      })
      signIn(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-header-bar">
        <LanguageSwitcher />
      </div>
      <div className="login-card">
        <div className="login-logo">🌾</div>
        <h1 className="login-title">AgriPermit</h1>
        <p className="login-subtitle">{t('app.subtitle')}</p>

        {error && <p className="error-msg">{error}</p>}

        {mode === 'login' ? (
          <>
            <form className="login-form" onSubmit={handleLogin}>
              <div className="form-group">
                <label htmlFor="login-username">{t('login.username')}</label>
                <input
                  id="login-username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder={t('login.usernamePh')}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="login-password">{t('login.password')}</label>
                <input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>
              <button type="submit" className="btn btn--primary login-btn" disabled={loading}>
                {loading ? t('login.loggingIn') : t('login.submit')}
              </button>
            </form>
            <p className="login-hint">{t('login.hint')}</p>
            <button className="btn-link" onClick={() => { setMode('create'); setError(null) }}>
              {t('org.switchToCreate')}
            </button>
          </>
        ) : (
          <>
            <h2 className="login-subtitle">{t('org.createTitle')}</h2>
            <form className="login-form" onSubmit={handleRegister}>
              <div className="form-group">
                <label>{t('org.orgName')}</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={handleOrgNameChange}
                  placeholder={t('org.orgNamePh')}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('org.orgSlug')}</label>
                <input
                  type="text"
                  value={orgSlug}
                  onChange={e => setOrgSlug(e.target.value)}
                  placeholder="my-org"
                  required
                />
                <small>{t('org.slugHint')}</small>
              </div>
              <div className="form-group">
                <label>{t('org.adminUsername')}</label>
                <input
                  type="text"
                  autoComplete="username"
                  value={adminUsername}
                  onChange={e => setAdminUsername(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('org.adminEmail')}</label>
                <input
                  type="email"
                  autoComplete="email"
                  value={adminEmail}
                  onChange={e => setAdminEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('org.adminName')}</label>
                <input
                  type="text"
                  autoComplete="name"
                  value={adminName}
                  onChange={e => setAdminName(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t('org.password')}</label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={regPassword}
                  onChange={e => setRegPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>
              <button type="submit" className="btn btn--primary login-btn" disabled={loading}>
                {loading ? t('org.submitting') : t('org.submit')}
              </button>
            </form>
            <button className="btn-link" onClick={() => { setMode('login'); setError(null) }}>
              {t('org.switchToLogin')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
