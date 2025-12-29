import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { EXTERNAL_URLS } from '@/constants/config'
import './Footer.css'

const Footer = () => {
  const { t } = useTranslation()

  return (
    <footer className="footer-container">
      <div className="footer-links">
        <Link to="/privacy-policy" className="footer-link">{t('privacyPolicy')}</Link>
        <Link to="/disclaimer" className="footer-link">{t('disclaimerLink')}</Link>
        <Link to="/terms-of-use" className="footer-link">{t('termsOfUse')}</Link>
      </div>

      <div className="footer-logos">
        <a href={EXTERNAL_URLS.UNIVERSITY_OULU} target="_blank" rel="noopener noreferrer" className="logo-link">
          <img src="/assets/images/UNIOULU_logo.png" alt={t('universityOfOulu')} className="footer-logo" />
        </a>
        <a href={EXTERNAL_URLS.UBICOMP} target="_blank" rel="noopener noreferrer" className="logo-link">
          <img src="/assets/images/UBICOMP_logo.png" alt={t('ubicomp')} className="footer-logo" />
        </a>
        <a href={EXTERNAL_URLS.FCG} target="_blank" rel="noopener noreferrer" className="logo-link">
          <img src="/assets/images/FCG_logo.png" alt={t('fcg')} className="footer-logo" />
        </a>
      </div>
      
      <div className="footer-copyright">&copy; {new Date().getFullYear()} {t('neuroClimaAllRightsReserved')}</div>
    </footer>
  )
}

export default Footer