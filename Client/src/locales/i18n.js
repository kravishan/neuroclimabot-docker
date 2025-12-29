import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { DEFAULT_LANGUAGE } from '@/constants/languages'

// Import language resources
import en from './en/translation.json'
import it from './it/translation.json'
import pt from './pt/translation.json'
import el from './el/translation.json'

const resources = {
  en: { translation: en },
  it: { translation: it },
  pt: { translation: pt },
  el: { translation: el }
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
  })

export default i18n