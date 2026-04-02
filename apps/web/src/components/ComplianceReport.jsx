import React from 'react'
import { useTranslation } from 'react-i18next'

function Badge({ ok }) {
  return (
    <span className={`compliance-badge compliance-badge--${ok ? 'pass' : 'fail'}`}>
      {ok ? '✓ PASS' : '✗ FAIL'}
    </span>
  )
}

function ViolationRow({ v }) {
  return (
    <div className={`violation-row violation-row--${v.severity}`}>
      <span className={`violation-severity violation-severity--${v.severity}`}>
        {v.severity === 'block' ? '🚫' : '⚠️'} {v.severity.toUpperCase()}
      </span>
      <span className="violation-rule">[{v.rule}]</span>
      <span className="violation-msg">{v.message}</span>
    </div>
  )
}

export default function ComplianceReport({ submission }) {
  const { t } = useTranslation()
  const c = submission.compliance
  const warnings = submission.parse_warnings || []

  return (
    <div className="compliance-report">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="compliance-header">
        <div className="compliance-header__left">
          <h3>{t('report.title')}</h3>
          <p className="compliance-file">📄 {submission.filename}</p>
          <p className="compliance-time">
            {t('report.checked')}: {new Date(submission.uploaded_at).toLocaleString()}
          </p>
        </div>
        {c && (
          <div className="compliance-header__badge">
            <Badge ok={c.compliant} />
          </div>
        )}
      </div>

      {/* ── Extracted parameters ───────────────────────── */}
      <section className="report-section">
        <h4>{t('report.parsedParams')}</h4>
        <div className="report-grid">
          <div className="report-kv">
            <span>{t('report.floors')}</span>
            <strong>{submission.parsed_floors ?? t('report.notDetected')}</strong>
          </div>
          <div className="report-kv">
            <span>{t('report.coverage')}</span>
            <strong>{submission.parsed_coverage_pct != null ? `${submission.parsed_coverage_pct}%` : t('report.notDetected')}</strong>
          </div>
          <div className="report-kv">
            <span>{t('report.area')}</span>
            <strong>{submission.parsed_area_sqm != null ? `${submission.parsed_area_sqm} m²` : t('report.notDetected')}</strong>
          </div>
          {submission.engineer_name && (
            <div className="report-kv">
              <span>{t('report.engineer')}</span>
              <strong>{submission.engineer_name}</strong>
            </div>
          )}
          {submission.engineer_license && (
            <div className="report-kv">
              <span>{t('report.license')}</span>
              <strong>{submission.engineer_license}</strong>
            </div>
          )}
        </div>

        {warnings.length > 0 && (
          <div className="parse-warnings">
            {warnings.map((w, i) => (
              <p key={i} className="parse-warning">⚠️ {w}</p>
            ))}
          </div>
        )}
      </section>

      {/* ── GIS zone data ──────────────────────────────── */}
      {c && (
        <section className="report-section">
          <h4>
            {t('report.gisData')}
            <span className="gis-source">
              {t('report.source')}: {c.gis_source} &nbsp;·&nbsp;
              {t('report.version')}: {c.gis_data_version || 'N/A'}
            </span>
          </h4>
          <div className="report-grid">
            <div className="report-kv">
              <span>{t('report.zone')}</span>
              <strong>{c.gis_zone}</strong>
            </div>
            <div className="report-kv">
              <span>{t('report.planId')}</span>
              <strong>{c.gis_plan_id}</strong>
            </div>
            <div className="report-kv">
              <span>{t('report.maxFloors')}</span>
              <strong>{c.gis_max_floors}</strong>
            </div>
            <div className="report-kv">
              <span>{t('report.maxCoverage')}</span>
              <strong>{c.gis_max_cov}%</strong>
            </div>
            <div className="report-kv">
              <span>{t('report.protected')}</span>
              <strong>{c.gis_protected ? t('common.yes') : t('common.no')}</strong>
            </div>
            <div className="report-kv">
              <span>{t('report.agFreeze')}</span>
              <strong>{c.gis_ag_freeze ? t('common.yes') : t('common.no')}</strong>
            </div>
          </div>
        </section>
      )}

      {/* ── Violations ─────────────────────────────────── */}
      {c && (
        <section className="report-section">
          <h4>{t('report.violations')}</h4>
          {c.violations.length === 0 ? (
            <p className="no-violations">✅ {t('report.noViolations')}</p>
          ) : (
            <div className="violations-list">
              {c.violations.map((v, i) => <ViolationRow key={i} v={v} />)}
            </div>
          )}
        </section>
      )}

      {!c && (
        <section className="report-section">
          <p className="no-gis-msg">ℹ️ {t('report.noGis')}</p>
        </section>
      )}

      {/* ── Print / audit note ─────────────────────────── */}
      <div className="report-footer">
        <small>
          {t('report.auditNote')} · ID: {submission.id}
        </small>
      </div>
    </div>
  )
}
