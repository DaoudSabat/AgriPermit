import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { uploadDesign } from '../api'
import ComplianceReport from './ComplianceReport'

export default function DesignUpload() {
  const { t, i18n } = useTranslation()
  const isRtl = i18n.language !== 'en'

  const fileRef        = useRef(null)
  const [file, setFile]               = useState(null)
  const [dragging, setDragging]       = useState(false)
  const [parcelId, setParcelId]       = useState('')
  const [floorsOverride, setFloors]   = useState('')
  const [coverageOverride, setCov]    = useState('')
  const [loading, setLoading]         = useState(false)
  const [result, setResult]           = useState(null)
  const [error, setError]             = useState(null)

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  function onFileChange(e) {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) { setError(t('design.noFile')); return }

    setError(null)
    setResult(null)
    setLoading(true)

    const fd = new FormData()
    fd.append('file', file)
    if (parcelId.trim()) fd.append('parcel_id', parcelId.trim())
    if (floorsOverride)  fd.append('floors_override', floorsOverride)
    if (coverageOverride) fd.append('coverage_override', coverageOverride)

    try {
      const data = await uploadDesign(fd)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setFile(null)
    setResult(null)
    setError(null)
    setParcelId('')
    setFloors('')
    setCov('')
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="design-upload" dir={isRtl ? 'rtl' : 'ltr'}>
      <h2 className="section-title">{t('design.title')}</h2>
      <p className="section-subtitle">{t('design.subtitle')}</p>

      {!result && (
        <form className="design-form" onSubmit={handleSubmit}>
          {/* ── Drop zone ───────────────────────────────── */}
          <div
            className={`drop-zone${dragging ? ' drop-zone--over' : ''}${file ? ' drop-zone--has-file' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.dxf,.dwg"
              onChange={onFileChange}
              style={{ display: 'none' }}
            />
            {file ? (
              <div className="drop-zone__file">
                <span className="drop-zone__icon">📄</span>
                <span className="drop-zone__name">{file.name}</span>
                <span className="drop-zone__size">({(file.size / 1024).toFixed(0)} KB)</span>
              </div>
            ) : (
              <div className="drop-zone__prompt">
                <span className="drop-zone__icon">📂</span>
                <p>{t('design.dropPrompt')}</p>
                <small>{t('design.dropFormats')}</small>
              </div>
            )}
          </div>

          {/* ── Parcel + optional overrides ─────────────── */}
          <div className="design-form__fields">
            <div className="form-group">
              <label>{t('design.parcelId')}</label>
              <input
                type="text"
                value={parcelId}
                onChange={e => setParcelId(e.target.value)}
                placeholder={t('design.parcelIdPh')}
              />
              <small className="form-hint">{t('design.parcelIdHint')}</small>
            </div>

            <div className="design-form__row">
              <div className="form-group">
                <label>{t('design.floorsOverride')}</label>
                <input
                  type="number" min="0" max="100"
                  value={floorsOverride}
                  onChange={e => setFloors(e.target.value)}
                  placeholder={t('design.autoDetected')}
                />
              </div>
              <div className="form-group">
                <label>{t('design.coverageOverride')}</label>
                <input
                  type="number" min="0" max="100" step="0.1"
                  value={coverageOverride}
                  onChange={e => setCov(e.target.value)}
                  placeholder={t('design.autoDetected')}
                />
              </div>
            </div>
          </div>

          {error && <p className="error-msg">{error}</p>}

          <button
            type="submit"
            className="btn btn--primary"
            disabled={loading || !file}
          >
            {loading ? t('design.validating') : t('design.submit')}
          </button>
        </form>
      )}

      {result && (
        <div className="design-result">
          <ComplianceReport submission={result} />
          <button className="btn btn--secondary" onClick={reset} style={{ marginTop: '1.5rem' }}>
            {t('design.uploadAnother')}
          </button>
        </div>
      )}
    </div>
  )
}
