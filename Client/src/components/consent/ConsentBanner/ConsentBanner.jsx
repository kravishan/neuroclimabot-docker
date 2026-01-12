import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Shield, X, Settings } from 'lucide-react'
import { consentService } from '@/services/consent/consentService'
import { CONSENT_TYPES } from '@/constants/consent'
import './ConsentBanner.css'

const ConsentBanner = ({ onOpenSettings }) => {
  const { t } = useTranslation()
  const [isVisible, setIsVisible] = useState(false)
  const [showCustomize, setShowCustomize] = useState(false)
  const [analyticsConsent, setAnalyticsConsent] = useState(true) // Default: ON

  useEffect(() => {
    // Check if consent has been set
    const hasConsent = consentService.hasConsentBeenSet()
    setIsVisible(!hasConsent)
  }, [])

  const handleAcceptAll = () => {
    consentService.acceptAll()
    setIsVisible(false)
  }

  const handleRejectOptional = () => {
    consentService.rejectOptional()
    setIsVisible(false)
  }

  const handleSaveCustom = () => {
    consentService.setConsent({
      [CONSENT_TYPES.ESSENTIAL]: true,
      [CONSENT_TYPES.ANALYTICS]: analyticsConsent
    })
    setIsVisible(false)
    setShowCustomize(false)
  }

  const handleClose = () => {
    // User dismissed without action - save default (all on)
    consentService.acceptAll()
    setIsVisible(false)
  }

  if (!isVisible) {
    return null
  }

  return (
    <div className="consent-banner">
      <div className="consent-banner-content">
        <div className="consent-banner-header">
          <Shield size={24} className="consent-banner-icon" />
          <h3 className="consent-banner-title">{t('consent.banner.title')}</h3>
          <button
            className="consent-banner-close"
            onClick={handleClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {!showCustomize ? (
          <>
            <p className="consent-banner-text">
              {t('consent.banner.description')}
            </p>
            <p className="consent-banner-anonymized">
              {t('consent.banner.anonymized')}
            </p>

            <div className="consent-banner-actions">
              <button
                className="consent-btn consent-btn-primary"
                onClick={handleAcceptAll}
              >
                {t('consent.banner.acceptAll')}
              </button>
              <button
                className="consent-btn consent-btn-secondary"
                onClick={handleRejectOptional}
              >
                {t('consent.banner.rejectOptional')}
              </button>
              <button
                className="consent-btn consent-btn-text"
                onClick={() => setShowCustomize(true)}
              >
                <Settings size={16} />
                {t('consent.banner.customize')}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="consent-customize-section">
              <div className="consent-option">
                <div className="consent-option-header">
                  <input
                    type="checkbox"
                    id="consent-essential"
                    checked={true}
                    disabled={true}
                  />
                  <label htmlFor="consent-essential" className="consent-option-label">
                    <strong>{t('consent.essential.name')}</strong>
                    <span className="consent-required">{t('consent.required')}</span>
                  </label>
                </div>
                <p className="consent-option-description">
                  {t('consent.essential.description')}
                </p>
              </div>

              <div className="consent-option">
                <div className="consent-option-header">
                  <input
                    type="checkbox"
                    id="consent-analytics"
                    checked={analyticsConsent}
                    onChange={(e) => setAnalyticsConsent(e.target.checked)}
                  />
                  <label htmlFor="consent-analytics" className="consent-option-label">
                    <strong>{t('consent.analytics.name')}</strong>
                    <span className="consent-optional">{t('consent.optional')}</span>
                  </label>
                </div>
                <p className="consent-option-description">
                  {t('consent.analytics.description')}
                </p>
              </div>
            </div>

            <div className="consent-banner-actions">
              <button
                className="consent-btn consent-btn-primary"
                onClick={handleSaveCustom}
              >
                {t('consent.banner.savePreferences')}
              </button>
              <button
                className="consent-btn consent-btn-text"
                onClick={() => setShowCustomize(false)}
              >
                {t('consent.banner.back')}
              </button>
            </div>
          </>
        )}

        <div className="consent-banner-footer">
          <a href="/privacy-policy" className="consent-link">
            {t('privacyPolicy')}
          </a>
          <span className="consent-separator">•</span>
          <a href="/disclaimer" className="consent-link">
            {t('disclaimerLink')}
          </a>
        </div>
      </div>
    </div>
  )
}

export default ConsentBanner
