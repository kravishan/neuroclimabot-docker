import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Shield, Info, Save, RotateCcw } from 'lucide-react'
import { consentService } from '@/services/consent/consentService'
import { CONSENT_TYPES } from '@/constants/consent'
import './PrivacySettingsModal.css'

const PrivacySettingsModal = ({ isOpen, onClose }) => {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('preferences') // 'preferences' or 'info'
  const [analyticsConsent, setAnalyticsConsent] = useState(true)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    if (isOpen) {
      // Load current consent preferences
      const currentConsent = consentService.getConsent()
      if (currentConsent) {
        setAnalyticsConsent(currentConsent.preferences[CONSENT_TYPES.ANALYTICS])
      }
    }
  }, [isOpen])

  const handleSave = () => {
    consentService.setConsent({
      [CONSENT_TYPES.ESSENTIAL]: true,
      [CONSENT_TYPES.ANALYTICS]: analyticsConsent
    })
    setSaveMessage(t('consent.settings.saved'))
    setTimeout(() => {
      setSaveMessage('')
      onClose()
    }, 1500)
  }

  const handleReset = () => {
    if (window.confirm(t('consent.settings.resetConfirm'))) {
      consentService.resetConsent()
      setSaveMessage(t('consent.settings.resetSuccess'))
      setTimeout(() => {
        setSaveMessage('')
        window.location.reload()
      }, 1500)
    }
  }

  if (!isOpen) return null

  return (
    <div className="privacy-modal-overlay" onClick={onClose}>
      <div className="privacy-modal" onClick={(e) => e.stopPropagation()}>
        <div className="privacy-modal-header">
          <div className="privacy-modal-title">
            <Shield size={24} />
            <h2>{t('consent.settings.title')}</h2>
          </div>
          <button className="privacy-modal-close" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="privacy-modal-tabs">
          <button
            className={`privacy-tab ${activeTab === 'preferences' ? 'active' : ''}`}
            onClick={() => setActiveTab('preferences')}
          >
            <Shield size={16} />
            {t('consent.settings.preferencesTab')}
          </button>
          <button
            className={`privacy-tab ${activeTab === 'info' ? 'active' : ''}`}
            onClick={() => setActiveTab('info')}
          >
            <Info size={16} />
            {t('consent.settings.infoTab')}
          </button>
        </div>

        <div className="privacy-modal-content">
          {activeTab === 'preferences' ? (
            <>
              <div className="privacy-info-box">
                <Shield size={18} />
                <p>{t('consent.settings.description')}</p>
              </div>

              <div className="consent-preferences-list">
                {/* Essential Consent */}
                <div className="consent-preference-item">
                  <div className="consent-preference-header">
                    <div className="consent-preference-toggle">
                      <input
                        type="checkbox"
                        id="modal-consent-essential"
                        checked={true}
                        disabled={true}
                      />
                      <label htmlFor="modal-consent-essential">
                        <strong>{t('consent.essential.name')}</strong>
                        <span className="consent-badge consent-badge-required">
                          {t('consent.required')}
                        </span>
                      </label>
                    </div>
                  </div>
                  <p className="consent-preference-description">
                    {t('consent.essential.description')}
                  </p>
                  <p className="consent-preference-details">
                    {t('consent.essential.details')}
                  </p>
                </div>

                {/* Analytics Consent */}
                <div className="consent-preference-item">
                  <div className="consent-preference-header">
                    <div className="consent-preference-toggle">
                      <input
                        type="checkbox"
                        id="modal-consent-analytics"
                        checked={analyticsConsent}
                        onChange={(e) => setAnalyticsConsent(e.target.checked)}
                      />
                      <label htmlFor="modal-consent-analytics">
                        <strong>{t('consent.analytics.name')}</strong>
                        <span className="consent-badge consent-badge-optional">
                          {t('consent.optional')}
                        </span>
                      </label>
                    </div>
                  </div>
                  <p className="consent-preference-description">
                    {t('consent.analytics.description')}
                  </p>
                  <p className="consent-preference-details">
                    {t('consent.analytics.details')}
                  </p>
                </div>
              </div>

              {saveMessage && (
                <div className="privacy-save-message">
                  {saveMessage}
                </div>
              )}

              <div className="privacy-modal-actions">
                <button className="privacy-btn privacy-btn-primary" onClick={handleSave}>
                  <Save size={16} />
                  {t('consent.settings.save')}
                </button>
                <button className="privacy-btn privacy-btn-secondary" onClick={onClose}>
                  {t('consent.settings.cancel')}
                </button>
                <button className="privacy-btn privacy-btn-danger" onClick={handleReset}>
                  <RotateCcw size={16} />
                  {t('consent.settings.reset')}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="privacy-info-section">
                <h3>{t('consent.info.anonymizationTitle')}</h3>
                <p>{t('consent.info.anonymizationDescription')}</p>

                <h3>{t('consent.info.platformIndependenceTitle')}</h3>
                <p>{t('consent.info.platformIndependenceDescription')}</p>

                <h3>{t('consent.info.dataCollectionTitle')}</h3>
                <ul>
                  <li>{t('consent.info.dataItem1')}</li>
                  <li>{t('consent.info.dataItem2')}</li>
                  <li>{t('consent.info.dataItem3')}</li>
                  <li>{t('consent.info.dataItem4')}</li>
                </ul>

                <h3>{t('consent.info.dataUsageTitle')}</h3>
                <ul>
                  <li>{t('consent.info.usageItem1')}</li>
                  <li>{t('consent.info.usageItem2')}</li>
                  <li>{t('consent.info.usageItem3')}</li>
                </ul>

                <h3>{t('consent.info.yourRightsTitle')}</h3>
                <p>{t('consent.info.yourRightsDescription')}</p>
              </div>

              <div className="privacy-info-links">
                <a href="/privacy-policy" target="_blank" rel="noopener noreferrer">
                  {t('privacyPolicy')} →
                </a>
                <a href="/disclaimer" target="_blank" rel="noopener noreferrer">
                  {t('disclaimerLink')} →
                </a>
                <a href="/terms-of-use" target="_blank" rel="noopener noreferrer">
                  {t('termsOfUse')} →
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default PrivacySettingsModal
