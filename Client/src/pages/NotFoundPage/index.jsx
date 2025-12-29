import React from 'react'
import { useTranslation } from 'react-i18next'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import './NotFoundPage.css'

const NotFoundPage = () => {
  const { t } = useTranslation()

  useDocumentTitle('404 - Page Not Found')

  return (
    <div className="not-found-container">
      <h1 className="not-found-title">
        404 - {t('pageNotFound', 'Page Not Found')}
      </h1>
      <p className="not-found-description">
        {t('pageNotFoundDescription', 'Sorry, the page you are looking for does not exist.')}
      </p>
    </div>
  )
}

export default NotFoundPage