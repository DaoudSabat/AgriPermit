import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './en.json'
import he from './he.json'
import ar from './ar.json'

export const LANGUAGES = [
  { code: 'he', label: 'עברית', dir: 'rtl' },
  { code: 'ar', label: 'العربية', dir: 'rtl' },
  { code: 'en', label: 'English', dir: 'ltr' },
]

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    he: { translation: he },
    ar: { translation: ar },
  },
  lng: 'he',
  fallbackLng: 'he',
  interpolation: { escapeValue: false },
})

export default i18n
