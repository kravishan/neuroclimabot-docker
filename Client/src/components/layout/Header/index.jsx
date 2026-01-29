import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { FileText, BookOpen, Settings as SettingsIcon, CheckCircle, Coffee, BarChart3, Shield } from 'lucide-react'
import { SUPPORTED_LANGUAGES, DIFFICULTY_LEVELS } from '@/constants/languages'
import { EXTERNAL_URLS } from '@/constants/config'
import { ROUTES } from '@/constants/routes'
import './Header.css'

const Header = ({
  selectedLanguage,
  changeLanguage,
  difficultyLevel,
  setDifficultyLevel,
  onPrivacySettingsOpen,
  sessionStatus,
  countdownDisplay
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isLevelDropdownOpen, setIsLevelDropdownOpen] = useState(false)
  const { t, i18n } = useTranslation()
  
  const navigate = useNavigate()
  const location = useLocation()

  const isIndexPage = location.pathname === '/'
  const isResponsePage = location.pathname.includes('/response/')
  const isDashboardPage = location.pathname === '/dashboard'

  const dropdownRef = useRef(null)
  const levelDropdownRef = useRef(null)

  const toggleDropdown = () => setIsDropdownOpen(!isDropdownOpen)
  const toggleLevelDropdown = () => setIsLevelDropdownOpen(!isLevelDropdownOpen)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false)
      }
      if (levelDropdownRef.current && !levelDropdownRef.current.contains(event.target)) {
        setIsLevelDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLanguageChange = (language) => {
    changeLanguage(language)
    i18n.changeLanguage(language)
    setIsDropdownOpen(false)
  }

  const handleTitleClick = () => {
    navigate('/')
  }

  const handleOpenForm = () => {
    navigate(ROUTES.QUESTIONNAIRE)
  }

  const handleDashboardClick = () => {
    window.open(EXTERNAL_URLS.DASHBOARD, '_blank')
  }

  const handleAdminClick = () => {
    navigate('/admin')
  }

  const handleDifficultyChange = (level) => {
    setDifficultyLevel(level)
    setIsLevelDropdownOpen(false)
  }

  const formatCountdown = () => {
    if (!countdownDisplay) return ''
    const { minutes, seconds } = countdownDisplay
    if (minutes > 0) {
      return `${minutes} min${minutes !== 1 ? 's' : ''}`
    } else {
      return `${seconds}s`
    }
  }

  // Session Status Component for Header - Only show on response pages (WebSocket-based)
  const SessionStatusInHeader = () => {
    // Only show session badge on response pages
    if (!isResponsePage) {
      return null
    }

    // Show session badge when session is active and we're on response page
    if (!sessionStatus?.isSessionActive || !sessionStatus?.sessionId) {
      return null
    }

    const { isWarning, isCritical, showCountdown, minutes, seconds } = countdownDisplay || {}

    return (
      <div className="session-status-header">
        <div className="session-info-header">
          <span className="session-label-header">
            <CheckCircle size={14} />
            {t('sessionActive')}
          </span>
          <span className={`session-timeout-header ${isWarning ? 'warning' : ''} ${isCritical ? 'critical' : ''}`}>
            <Coffee size={12} />
            {showCountdown && minutes !== undefined && seconds !== undefined
              ? `${minutes}:${seconds.toString().padStart(2, '0')}`
              : '...'
            }
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="header-container">
      <div className="title" onClick={handleTitleClick}>
        <img src="/assets/images/logo.svg" alt="NeuroClima Bot Logo" className="header-logo" />
      </div>
      
      <div className="header-controls">
        {/* Session Status - only shows on response pages */}
        <SessionStatusInHeader />

        {/* Privacy Settings - always visible */}
        <button
          className="privacy-settings-button"
          onClick={onPrivacySettingsOpen}
          aria-label="Privacy Settings"
          title={t('consent.settings.title')}
        >
          <Shield size={18} />
          <span className="button-text">Privacy</span>
        </button>

        {/* Show Admin button when on dashboard page, otherwise show Dashboard button */}
        {isDashboardPage ? (
          <button className="dashboard-button" onClick={handleAdminClick}>
            <BarChart3 size={18} />
            <span className="button-text">Admin</span>
          </button>
        ) : (
          <button className="dashboard-button" onClick={handleDashboardClick}>
            <BarChart3 size={18} />
            <span className="button-text">{t('dashboard')}</span>
          </button>
        )}
        
        <button className="form-button" onClick={handleOpenForm}>
          <FileText size={18} />
          <span className="button-text">{t('participateResearch')}</span>
        </button>
        
        {isIndexPage && (
          <div className="difficulty-selector">
            <button className="difficulty-button" onClick={toggleLevelDropdown}>
              <BookOpen size={18} />
              <span className="button-text">
                {difficultyLevel === 'low' ? t('easyReading') : t('advancedReading')}
              </span>
              <span className="arrow-down">▼</span>
            </button>
            
            {isLevelDropdownOpen && (
              <div className="difficulty-dropdown" ref={levelDropdownRef}>
                {DIFFICULTY_LEVELS.map(level => (
                  <div 
                    key={level.value}
                    className={`difficulty-option ${difficultyLevel === level.value ? 'selected' : ''}`} 
                    onClick={() => handleDifficultyChange(level.value)}
                  >
                    {t(level.label)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {isIndexPage && (
          <div className="language-selector">
            <button className="language-button" onClick={toggleDropdown}>
              {selectedLanguage.toUpperCase()}
              <span className="arrow-down">▼</span>
            </button>
            
            {isDropdownOpen && (
              <div className="language-dropdown" ref={dropdownRef}>
                {SUPPORTED_LANGUAGES.map(lang => (
                  <div 
                    key={lang.code}
                    className={`language-option ${selectedLanguage === lang.code ? 'selected' : ''}`} 
                    onClick={() => handleLanguageChange(lang.code)}
                  >
                    {lang.nativeName}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default Header