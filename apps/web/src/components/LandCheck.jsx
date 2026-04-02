import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { checkLand, fetchParcels } from '../api'

const USE_REQUIREMENTS = {
  agricultural: 'agricultural',
  construction: 'residential',
  water:        'agricultural',
}

function eligibility(uses, t) {
  return ['agricultural', 'construction', 'water', 'other'].map(type => {
    const required = USE_REQUIREMENTS[type]
    const allowed  = !required || uses.includes(required)
    return { type, allowed }
  })
}

function ResultCard({ data }) {
  const { t } = useTranslation()
  const uses = data.permitted_uses ?? []

  return (
    <div className="gis-result">
      <div className="gis-result__header">
        <h3 className="gis-result__title">{t('check.resultsTitle')}</h3>
        <span className="gis-result__id">
          {data.parcel_id
            ? data.parcel_id
            : `${t('check.gushLabel')} ${data.gush} / ${t('check.helkaLabel')} ${data.helka}`}
        </span>
      </div>

      <div className="gis-result__meta">
        <span className="gis-meta-item">
          <span className="gis-meta-label">{t('check.plan')}</span>
          <span className="gis-meta-value">{data.zone_plan_id}</span>
        </span>
        <span className="gis-meta-item">
          <span className="gis-meta-label">{t('check.source')}</span>
          <span className="gis-meta-value gis-meta-value--mono">{data.source}</span>
        </span>
      </div>

      <div className="gis-metrics">
        {/* Max floors */}
        <div className="gis-metric">
          <div className="gis-metric__value">{data.max_floors}</div>
          <div className="gis-metric__label">{t('check.maxFloors')}</div>
        </div>

        {/* Max coverage */}
        <div className="gis-metric">
          <div className="gis-metric__value">{data.max_coverage_pct}%</div>
          <div className="gis-metric__label">{t('check.maxCoverage')}</div>
        </div>

        {/* Protected zone */}
        <div className={`gis-metric ${data.is_protected_zone ? 'gis-metric--danger' : 'gis-metric--ok'}`}>
          <div className="gis-metric__value">{data.is_protected_zone ? '⛔' : '✓'}</div>
          <div className="gis-metric__label">{t('check.protectedZone')}</div>
          <div className="gis-metric__sub">
            {data.is_protected_zone ? t('check.yes') : t('check.no')}
          </div>
        </div>

        {/* Agricultural freeze */}
        <div className={`gis-metric ${data.is_agricultural_freeze ? 'gis-metric--warn' : 'gis-metric--ok'}`}>
          <div className="gis-metric__value">{data.is_agricultural_freeze ? '⚠' : '✓'}</div>
          <div className="gis-metric__label">{t('check.agFreeze')}</div>
          <div className="gis-metric__sub">
            {data.is_agricultural_freeze ? t('check.yes') : t('check.no')}
          </div>
        </div>
      </div>

      {/* Permitted uses */}
      <div className="gis-section">
        <h4 className="gis-section__label">{t('check.permittedUses')}</h4>
        <div className="gis-uses">
          {uses.map(u => (
            <span key={u} className="gis-use-tag">{u}</span>
          ))}
        </div>
      </div>

      {/* Per permit-type eligibility */}
      <div className="gis-section">
        <h4 className="gis-section__label">{t('check.permitTypes')}</h4>
        <div className="gis-eligibility">
          {eligibility(uses, t).map(({ type, allowed }) => (
            <div key={type} className={`gis-elig-row ${allowed ? 'gis-elig-row--ok' : 'gis-elig-row--block'}`}>
              <span className="gis-elig-icon">{allowed ? '✓' : '⛔'}</span>
              <span className="gis-elig-type">{t(`permits.type.${type}`, type)}</span>
              <span className="gis-elig-verdict">{allowed ? t('check.allowed') : t('check.blocked')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function LandCheck() {
  const { t } = useTranslation()
  const [mode, setMode]           = useState('manual')   // 'known' | 'manual'
  const [parcelId, setParcelId]   = useState('')
  const [gush, setGush]           = useState('')
  const [helka, setHelka]         = useState('')
  const [zone, setZone]           = useState('')
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [parcels, setParcels]     = useState([])

  useEffect(() => {
    fetchParcels().then(setParcels).catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setResult(null)

    if (mode === 'manual' && (!gush.trim() || !helka.trim())) {
      setError(t('check.errGushHelka'))
      return
    }

    setLoading(true)
    try {
      const data = await checkLand(
        mode === 'known'
          ? { parcelId }
          : { gush: parseInt(gush, 10), helka: parseInt(helka, 10), zone: zone.trim() || undefined }
      )
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2 className="section-title">{t('check.title')}</h2>
      <p className="check-subtitle">{t('check.subtitle')}</p>

      {/* Mode toggle */}
      <div className="check-mode-toggle">
        <button
          type="button"
          className={`mode-btn${mode === 'manual' ? ' mode-btn--active' : ''}`}
          onClick={() => { setMode('manual'); setResult(null); setError(null) }}
        >
          {t('check.modeManual')}
        </button>
        <button
          type="button"
          className={`mode-btn${mode === 'known' ? ' mode-btn--active' : ''}`}
          onClick={() => { setMode('known'); setResult(null); setError(null) }}
        >
          {t('check.modeKnown')}
        </button>
      </div>

      <form className="check-form" onSubmit={handleSubmit}>
        {mode === 'manual' ? (
          <div className="check-fields">
            <div className="form-group">
              <label htmlFor="gush">{t('check.gushLabel')}</label>
              <input
                id="gush"
                type="number"
                min="1"
                placeholder={t('check.gushPh')}
                value={gush}
                onChange={e => { setGush(e.target.value); setResult(null) }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="helka">{t('check.helkaLabel')}</label>
              <input
                id="helka"
                type="number"
                min="1"
                placeholder={t('check.helkaPh')}
                value={helka}
                onChange={e => { setHelka(e.target.value); setResult(null) }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="zone">{t('check.zoneLabel')}</label>
              <input
                id="zone"
                type="text"
                placeholder={t('check.zonePh')}
                value={zone}
                onChange={e => { setZone(e.target.value); setResult(null) }}
              />
            </div>
          </div>
        ) : (
          <div className="check-fields">
            <div className="form-group">
              <label htmlFor="known-parcel">{t('check.parcelLabel')}</label>
              <select
                id="known-parcel"
                value={parcelId}
                onChange={e => { setParcelId(e.target.value); setResult(null) }}
              >
                <option value="">{t('check.parcelPh')}</option>
                {parcels.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.id} — {p.address}
                    {p.gush ? ` (גוש ${p.gush} / חלקה ${p.helka})` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {error && <p className="error-msg">{error}</p>}

        <button
          type="submit"
          className="btn btn--primary check-submit"
          disabled={loading || (mode === 'known' && !parcelId)}
        >
          {loading ? t('check.checking') : t('check.submit')}
        </button>
      </form>

      {result && <ResultCard data={result} />}
    </div>
  )
}
