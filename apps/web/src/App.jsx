import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import './index.css'
import { useAuth } from './AuthContext'
import PermitList from './components/PermitList'
import NewPermitForm from './components/NewPermitForm'
import LanguageSwitcher from './components/LanguageSwitcher'
import LandCheck from './components/LandCheck'
import LoginPage from './components/LoginPage'
import StatsBar from './components/StatsBar'
import DesignUpload from './components/DesignUpload'

export default function App() {
  const { t } = useTranslation()
  const { user, org, ready, signOut } = useAuth()
  const [activeTab, setActiveTab] = useState('list')
  const [refreshKey, setRefreshKey] = useState(0)

  if (!ready) {
    return <div className="app-loading"><span className="spinner" />{t('app.loading')}</div>
  }

  if (!user) return <LoginPage />

  function handlePermitSubmitted() {
    setRefreshKey(k => k + 1)
    setActiveTab('list')
  }

  const TABS = [
    { id: 'list',   label: t('tabs.list'),   icon: '📋' },
    { id: 'new',    label: t('tabs.new'),    icon: '➕' },
    { id: 'design', label: t('tabs.design'), icon: '📐' },
    { id: 'check',  label: t('tabs.check'),  icon: '🗺️' },
  ]

  return (
    <>
      <header className="app-header">
        <div className="app-header__text">
          <h1>{t('app.title')}</h1>
          <p className="subtitle">{t('app.subtitle')}</p>
        </div>
        <div className="app-header__right">
          <div className="user-info">
            {org && <span className="user-info__org">{org.name}</span>}
            <span className="user-info__name">{user.full_name ?? user.username}</span>
            <span className={`role-badge role-badge--${user.role}`}>{user.role}</span>
            <button className="btn-signout" onClick={signOut}>{t('app.signOut')}</button>
          </div>
          <LanguageSwitcher />
        </div>
      </header>

      <StatsBar />

      <nav className="app-tabs" role="tablist">
        {TABS.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn${activeTab === tab.id ? ' tab-btn--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="app-body">
        {activeTab === 'list'   && <PermitList refreshKey={refreshKey} />}
        {activeTab === 'check'  && <LandCheck />}
        {activeTab === 'new'    && <NewPermitForm onSubmitted={handlePermitSubmitted} />}
        {activeTab === 'design' && <DesignUpload />}
      </main>
    </>
  )
}
