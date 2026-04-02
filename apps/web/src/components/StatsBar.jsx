import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchStats } from '../api'

export default function StatsBar() {
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {})
  }, [])

  if (!stats) return null

  const tiles = [
    { label: t('stats.total'),    value: stats.total,       cls: '',                     icon: '📁' },
    { label: t('stats.pending'),  value: stats.pending,     cls: 'stats-tile--pending',  icon: '⏳' },
    { label: t('stats.approved'), value: stats.approved,    cls: 'stats-tile--approved', icon: '✅' },
    { label: t('stats.rejected'), value: stats.rejected,    cls: 'stats-tile--rejected', icon: '❌' },
    { label: t('stats.blocked'),  value: stats.gis_blocked, cls: 'stats-tile--blocked',  icon: '🚫' },
  ]

  return (
    <div className="stats-bar">
      {tiles.map(({ label, value, cls, icon }) => (
        <div key={label} className={`stats-tile ${cls}`}>
          <span className="stats-tile__icon">{icon}</span>
          <span className="stats-tile__value">{value}</span>
          <span className="stats-tile__label">{label}</span>
        </div>
      ))}
    </div>
  )
}
