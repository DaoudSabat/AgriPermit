import React, { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchPermits, approvePermit } from '../api'
import { useAuth } from '../AuthContext'

const PAGE_SIZE = 20

function StatusBadge({ status }) {
  const { t } = useTranslation()
  return <span className={`badge badge--${status}`}>{t(`permits.status.${status}`, status)}</span>
}

function GisBadge({ flagged, blocked }) {
  const { t } = useTranslation()
  if (!flagged) return <span className="gis-badge gis-badge--ok"    title={t('gis.okTitle')}   >{t('gis.ok')}</span>
  if (blocked)  return <span className="gis-badge gis-badge--block" title={t('gis.blockTitle')}>{t('gis.block')}</span>
  return              <span className="gis-badge gis-badge--warn"   title={t('gis.warnTitle')} >{t('gis.warn')}</span>
}

function ViolationsList({ violations }) {
  const { t } = useTranslation()
  if (!violations?.length) return null
  return (
    <ul className="violations-list">
      {violations.map((v, i) => (
        <li key={i} className={`violation violation--${v.severity}`}>
          <span className="violation__icon">{v.severity === 'block' ? '⛔' : '⚠'}</span>
          <span className="violation__rule">[{t(`gis.severity${v.severity.charAt(0).toUpperCase() + v.severity.slice(1)}`, v.severity)}]</span>
          {v.message}
        </li>
      ))}
    </ul>
  )
}

function ActionPanel({ permit, onDone, onCancel }) {
  const { t } = useTranslation()
  const [approvedBy, setApprovedBy]           = useState('')
  const [rejectionReason, setRejectionReason] = useState('')
  const [action, setAction]                   = useState(null)
  const [submitting, setSubmitting]           = useState(false)
  const [error, setError]                     = useState(null)

  const hasViolations = permit.gis_violations?.length > 0

  async function submit() {
    if (!approvedBy.trim()) { setError(t('action.errApprovedBy')); return }
    if (action === 'reject' && !rejectionReason.trim()) { setError(t('action.errReason')); return }
    setSubmitting(true)
    setError(null)
    try {
      await approvePermit(permit.id, {
        action,
        approved_by: approvedBy.trim(),
        rejection_reason: rejectionReason.trim() || undefined,
      })
      onDone()
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="action-panel">
      {hasViolations && (
        <div className="action-panel__gis">
          <strong className="action-panel__gis-title">
            {permit.gis_blocked ? t('gis.headingBlock') : t('gis.headingWarn')}
          </strong>
          <ViolationsList violations={permit.gis_violations} />
        </div>
      )}

      {error && <span className="action-panel__error">{error}</span>}

      {!action ? (
        <div className="action-panel__row">
          <span className="action-panel__label">
            {permit.gis_blocked
              ? t('action.chooseBlocked')
              : t('action.choose', { number: permit.permit_number })}
          </span>
          <button className="btn btn--approve"   onClick={() => setAction('approve')}>{t('action.approve')}</button>
          <button className="btn btn--reject"    onClick={() => setAction('reject')} >{t('action.reject')}</button>
          <button className="btn btn--secondary" onClick={onCancel}                  >{t('action.cancel')}</button>
        </div>
      ) : (
        <div className="action-panel__row">
          <strong>
            {action === 'approve'
              ? t('action.confirmApprove')
              : t('action.confirmReject')}
            {' '}{permit.permit_number}
          </strong>

          <label className="action-panel__field">
            <span>{t('action.approvedByLabel')}</span>
            <input
              type="text"
              value={approvedBy}
              onChange={e => setApprovedBy(e.target.value)}
              placeholder={t('action.approvedByPh')}
              disabled={submitting}
            />
          </label>

          {action === 'reject' && (
            <label className="action-panel__field">
              <span>{t('action.reasonLabel')}</span>
              <input
                type="text"
                value={rejectionReason}
                onChange={e => setRejectionReason(e.target.value)}
                placeholder={t('action.reasonPh')}
                disabled={submitting}
              />
            </label>
          )}

          <div className="action-panel__btns">
            <button
              className={`btn ${action === 'approve' ? 'btn--approve' : 'btn--reject'}`}
              onClick={submit}
              disabled={submitting}
            >
              {submitting ? t('action.submitting') : action === 'approve' ? t('action.confirmApprove') : t('action.confirmReject')}
            </button>
            <button className="btn btn--secondary" onClick={() => setAction(null)} disabled={submitting}>
              {t('action.back')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function PermitList({ refreshKey }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const canAct = user?.role === 'admin' || user?.role === 'reviewer'
  const [permits, setPermits]               = useState([])
  const [total, setTotal]                   = useState(0)
  const [page, setPage]                     = useState(0)
  const [filterStatus, setFilterStatus]     = useState('')
  const [filterGis, setFilterGis]           = useState('')
  const [loading, setLoading]               = useState(false)
  const [error, setError]                   = useState(null)
  const [activePermitId, setActivePermitId] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const gisFlagged = filterGis === 'flagged' ? true : filterGis === 'ok' ? false : undefined
    fetchPermits({ status: filterStatus || undefined, gisFlagged, skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      .then(data => { setPermits(data.items); setTotal(data.total) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [filterStatus, filterGis, page])

  useEffect(() => { load() }, [load, refreshKey])
  useEffect(() => { setPage(0) }, [filterStatus, filterGis])

  function handleActionDone() { setActivePermitId(null); load() }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="card">
      <div className="list-toolbar">
        <h2 className="section-title">{t('permits.title')}</h2>
        <div className="filter-row">
          <label htmlFor="status-filter">{t('permits.filter.statusLabel')}</label>
          <select id="status-filter" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">{t('permits.filter.all')}</option>
            <option value="pending">{t('permits.status.pending')}</option>
            <option value="approved">{t('permits.status.approved')}</option>
            <option value="rejected">{t('permits.status.rejected')}</option>
          </select>

          <label htmlFor="gis-filter">{t('permits.filter.gisLabel')}</label>
          <select id="gis-filter" value={filterGis} onChange={e => setFilterGis(e.target.value)}>
            <option value="">{t('permits.filter.all')}</option>
            <option value="flagged">{t('permits.filter.flagged')}</option>
            <option value="ok">{t('permits.filter.ok')}</option>
          </select>

          <button className="btn btn--secondary" onClick={load} disabled={loading}>
            {loading ? t('permits.filter.refreshing') : t('permits.filter.refresh')}
          </button>
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {!loading && !error && permits.length === 0 && <p className="empty-msg">{t('permits.empty')}</p>}

      {permits.length > 0 && (
        <>
          <div className="table-wrapper">
            <table className="permits-table">
              <thead>
                <tr>
                  <th>{t('permits.columns.number')}</th>
                  <th>{t('permits.columns.parcel')}</th>
                  <th>{t('permits.columns.applicant')}</th>
                  <th>{t('permits.columns.type')}</th>
                  <th>{t('permits.columns.status')}</th>
                  <th>{t('permits.columns.gis')}</th>
                  <th>{t('permits.columns.date')}</th>
                  {canAct && <th>{t('permits.columns.actions')}</th>}
                </tr>
              </thead>
              <tbody>
                {permits.map(p => (
                  <React.Fragment key={p.id}>
                    <tr className={activePermitId === p.id ? 'row--active' : ''}>
                      <td className="permit-number">{p.permit_number}</td>
                      <td>{p.parcel_id}</td>
                      <td>{p.applicant_name}</td>
                      <td>{t(`permits.type.${p.permit_type}`, p.permit_type)}</td>
                      <td><StatusBadge status={p.status} /></td>
                      <td><GisBadge flagged={p.gis_flagged} blocked={p.gis_blocked} /></td>
                      <td>{new Date(p.created_at).toLocaleDateString()}</td>
                      {canAct && (
                        <td>
                          {p.status === 'pending' ? (
                            <button
                              className={`btn btn--sm ${activePermitId === p.id ? 'btn--ghost' : 'btn--secondary'}`}
                              onClick={() => setActivePermitId(id => id === p.id ? null : p.id)}
                            >
                              {activePermitId === p.id ? '✕ ' + t('action.close') : '▾ ' + t('action.handle')}
                            </button>
                          ) : (
                            <span className="no-action">—</span>
                          )}
                        </td>
                      )}
                    </tr>

                    {activePermitId === p.id && canAct && (
                      <tr className="action-row">
                        <td colSpan={canAct ? 8 : 7} style={{ padding: 0 }}>
                          <ActionPanel
                            permit={p}
                            onDone={handleActionDone}
                            onCancel={() => setActivePermitId(null)}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button className="btn btn--secondary" onClick={() => setPage(p => p - 1)} disabled={page === 0}>
              {t('permits.pagination.prev')}
            </button>
            <span>{t('permits.pagination.info', { current: page + 1, total: totalPages, count: total })}</span>
            <button className="btn btn--secondary" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>
              {t('permits.pagination.next')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
