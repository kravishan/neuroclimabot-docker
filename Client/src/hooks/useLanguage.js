import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { DEFAULT_LANGUAGE } from '@/constants/languages'

export const useLanguage = () => {
  const [selectedLanguage, setSelectedLanguage] = useState(DEFAULT_LANGUAGE)
  const { i18n } = useTranslation()

  const changeLanguage = (language) => {
    setSelectedLanguage(language)
    i18n.changeLanguage(language)
  }

  return {
    selectedLanguage,
    changeLanguage,
  }
}