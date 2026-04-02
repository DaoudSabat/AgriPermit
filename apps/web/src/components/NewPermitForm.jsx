import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { createPermit, fetchParcels } from '../api'

const EMPTY = {
  parcel_id: '',
  applicant_name: '',
  applicant_email: '',
  permit_type: 'agricultural',
  description: '',
  requested_floors: '',
  requested_coverage_pct: '',
}

function validate(fields, t) {
  const errors = {}
  if (!fields.parcel_id)              errors.parcel_id        = t('form.errParcel')
  if (!fields.applicant_name.trim())  errors.applicant_name   = t('form.errName')
  if (!fields.applicant_email.trim()) {
    errors.applicant_email = t('form.errEmail')
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.applicant_email)) {
    errors.applicant_email = t('form.errEmailInvalid')
  }
  return errors
}

export default function NewPermitForm({ onSubmitted }) {
  const { t } = useTranslation()
  const [fields, setFields]           = useState(EMPTY)
  const [errors, setErrors]           = useState({})
  const [submitting, setSubmitting]   = useState(false)
  const [serverError, setServerError] = useState(null)
  const [success, setSuccess]         = useState(null)
  const [parcels, setParcels]         = useState([])
  const [parcelsLoading, setParcelsLoading] = useState(true)

  useEffect(() => {
    fetchParcels()
      .then(setParcels)
      .catch(() => setParcels([]))
      .finally(() => setParcelsLoading(false))
  }, [])

  function handleChange(e) {
    const { name, value } = e.target
    setFields(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: undefined }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = validate(fields, t)
    if (Object.keys(errs).length) { setErrors(errs); return }

    setSubmitting(true)
    setServerError(null)
    try {
      const permit = await createPermit({
        parcel_id:              fields.parcel_id,
        applicant_name:         fields.applicant_name.trim(),
        applicant_email:        fields.applicant_email.trim(),
        permit_type:            fields.permit_type,
        description:            fields.description.trim() || undefined,
        requested_floors:       fields.requested_floors ? parseInt(fields.requested_floors, 10) : undefined,
        requested_coverage_pct: fields.requested_coverage_pct ? parseFloat(fields.requested_coverage_pct) : undefined,
      })
      setSuccess(t('form.success', { number: permit.permit_number }))
      setFields(EMPTY)
      onSubmitted?.()
    } catch (err) {
      setServerError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  function handleClear() { setFields(EMPTY); setErrors({}); setServerError(null) }

  return (
    <div className="card">
      <h2 className="section-title">{t('form.title')}</h2>

      {success && (
        <div className="success-banner" role="status">
          {success}
          <button className="dismiss-btn" onClick={() => setSuccess(null)}>✕</button>
        </div>
      )}
      {serverError && <p className="error-msg">{serverError}</p>}

      <form className="permit-form" onSubmit={handleSubmit} noValidate>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="parcel_id">{t('form.parcelLabel')}</label>
            <select
              id="parcel_id"
              name="parcel_id"
              value={fields.parcel_id}
              onChange={handleChange}
              disabled={parcelsLoading}
              aria-invalid={!!errors.parcel_id}
            >
              <option value="">{parcelsLoading ? t('form.parcelLoading') : t('form.parcelPh')}</option>
              {parcels.map(p => (
                <option key={p.id} value={p.id}>
                  {p.id} — {p.address} ({p.area_sqm.toLocaleString()} m², {p.zone})
                </option>
              ))}
            </select>
            {errors.parcel_id && <span className="field-error">{errors.parcel_id}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="permit_type">{t('form.typeLabel')}</label>
            <select id="permit_type" name="permit_type" value={fields.permit_type} onChange={handleChange}>
              <option value="agricultural">{t('permits.type.agricultural')}</option>
              <option value="construction">{t('permits.type.construction')}</option>
              <option value="water">{t('permits.type.water')}</option>
              <option value="other">{t('permits.type.other')}</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="applicant_name">{t('form.nameLabel')}</label>
            <input
              id="applicant_name"
              name="applicant_name"
              type="text"
              placeholder={t('form.namePh')}
              value={fields.applicant_name}
              onChange={handleChange}
              aria-invalid={!!errors.applicant_name}
            />
            {errors.applicant_name && <span className="field-error">{errors.applicant_name}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="applicant_email">{t('form.emailLabel')}</label>
            <input
              id="applicant_email"
              name="applicant_email"
              type="email"
              placeholder={t('form.emailPh')}
              value={fields.applicant_email}
              onChange={handleChange}
              aria-invalid={!!errors.applicant_email}
              dir="ltr"
            />
            {errors.applicant_email && <span className="field-error">{errors.applicant_email}</span>}
          </div>
        </div>

        {fields.permit_type === 'construction' && (
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="requested_floors">{t('form.floorsLabel')}</label>
              <input
                id="requested_floors"
                name="requested_floors"
                type="number"
                min="1"
                placeholder={t('form.floorsPh')}
                value={fields.requested_floors}
                onChange={handleChange}
              />
              <span className="field-hint">{t('form.floorsHint')}</span>
            </div>

            <div className="form-group">
              <label htmlFor="requested_coverage_pct">{t('form.coverageLabel')}</label>
              <input
                id="requested_coverage_pct"
                name="requested_coverage_pct"
                type="number"
                min="1"
                max="100"
                step="0.1"
                placeholder={t('form.coveragePh')}
                value={fields.requested_coverage_pct}
                onChange={handleChange}
              />
              <span className="field-hint">{t('form.coverageHint')}</span>
            </div>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="description">{t('form.descLabel')}</label>
          <textarea
            id="description"
            name="description"
            rows={4}
            placeholder={t('form.descPh')}
            value={fields.description}
            onChange={handleChange}
          />
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn--primary" disabled={submitting || parcelsLoading}>
            {submitting ? t('form.submitting') : t('form.submit')}
          </button>
          <button type="button" className="btn btn--secondary" onClick={handleClear} disabled={submitting}>
            {t('form.clear')}
          </button>
        </div>
      </form>
    </div>
  )
}
