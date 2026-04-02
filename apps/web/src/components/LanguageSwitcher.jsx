import React from 'react'
import { useTranslation } from 'react-i18next'
import { LANGUAGES } from '../i18n'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()

  function switchTo(lang) {
    const { dir } = LANGUAGES.find(l => l.code === lang)
    i18n.changeLanguage(lang)
    document.documentElement.lang = lang
    document.documentElement.dir  = dir
  }

  return (
    <div className="lang-switcher" role="group" aria-label="Language / שפה / اللغة">
      {LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          className={`lang-btn${i18n.language === code ? ' lang-btn--active' : ''}`}
          onClick={() => switchTo(code)}
          aria-pressed={i18n.language === code}
          lang={code}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
