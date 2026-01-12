import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, useLocation } from 'react-router-dom'
import { useLanguage } from '@/hooks/useLanguage'
import { useSession } from '@/hooks/useSession'
import AuthGuard from '@/components/auth/AuthGuard'
import Header from '@/components/layout/Header'
import Footer from '@/components/layout/Footer'
import AppRoutes from '@/routes/AppRoutes'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import ConsentBanner from '@/components/consent/ConsentBanner/ConsentBanner'
import PrivacySettingsModal from '@/components/consent/PrivacySettingsModal/PrivacySettingsModal'

function AppContent() {
  const { selectedLanguage, changeLanguage } = useLanguage()
  const [difficultyLevel, setDifficultyLevel] = useState('low')
  const [isVoiceSettingsOpen, setIsVoiceSettingsOpen] = useState(false)
  const [isPrivacySettingsOpen, setIsPrivacySettingsOpen] = useState(false)
  const [countdownDisplay, setCountdownDisplay] = useState({
    minutes: 0,
    seconds: 0,
    isWarning: false,
    isCritical: false,
    showCountdown: false
  })
  
  const location = useLocation()
  const isHomePage = location.pathname === '/' || location.pathname === '/index'
  const isResponsePage = location.pathname.includes('/response/')
  const isAdminPage = location.pathname === '/admin'
  
  // Get session status
  const { sessionStatus, isSessionActive, updateSessionStatus } = useSession()
  
  // Force session status update when location changes to response page
  useEffect(() => {
    if (isResponsePage) {
      console.log('App.jsx: Response page detected, forcing session status update')
      updateSessionStatus()
    }
  }, [isResponsePage, updateSessionStatus])
  
  // Debug logging for session status
  useEffect(() => {
    console.log('App.jsx Session Debug:', {
      sessionStatus,
      isSessionActive,
      isResponsePage,
      pathname: location.pathname
    })
  }, [sessionStatus, isSessionActive, isResponsePage, location.pathname])
  
  // Set up countdown display for session status
  useEffect(() => {
    let intervalId
    
    if (isSessionActive) {
      // Update countdown display every second, but only for visual display
      intervalId = setInterval(() => {
        const status = sessionStatus
        
        if (!status || !status.hasActiveSession) {
          setCountdownDisplay(prev => ({
            ...prev,
            showCountdown: false
          }))
          return
        }

        const remainingMs = status.remainingMs || 0
        
        if (remainingMs <= 0) {
          setCountdownDisplay({
            minutes: 0,
            seconds: 0,
            isWarning: false,
            isCritical: true,
            showCountdown: false
          })
          
          if (intervalId) {
            clearInterval(intervalId)
          }
          return
        }

        const totalSeconds = Math.floor(remainingMs / 1000)
        const minutes = Math.floor(totalSeconds / 60)
        const seconds = totalSeconds % 60
        
        // Use environment variables for thresholds
        const warningMinutes = parseInt(import.meta.env.VITE_INACTIVITY_WARNING_MINUTES) || 1
        const isWarning = minutes < warningMinutes && minutes >= 0
        const isCritical = minutes < 1 && seconds <= 30

        // Only update if values actually changed to prevent unnecessary re-renders
        setCountdownDisplay(prev => {
          if (prev.minutes !== minutes || prev.seconds !== seconds || 
              prev.isWarning !== isWarning || prev.isCritical !== isCritical ||
              prev.showCountdown !== (status.showCountdown || false)) {
            return {
              minutes,
              seconds,
              isWarning,
              isCritical,
              showCountdown: status.showCountdown || false
            }
          }
          return prev
        })
      }, 1000)
    } else {
      setCountdownDisplay(prev => ({
        ...prev,
        showCountdown: false
      }))
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [isSessionActive, sessionStatus.hasActiveSession, sessionStatus.isInactive])
  
  useEffect(() => {
    if (isHomePage) {
      document.body.classList.add('index-page')
    } else {
      document.body.classList.remove('index-page')
    }
    
    return () => {
      document.body.classList.remove('index-page')
    }
  }, [isHomePage])
  
  const handleVoiceSettingsOpen = () => {
    setIsVoiceSettingsOpen(true)
  }

  const updateVoiceSettingsOpen = (isOpen) => {
    setIsVoiceSettingsOpen(isOpen)
  }

  const handlePrivacySettingsOpen = () => {
    setIsPrivacySettingsOpen(true)
  }

  const handlePrivacySettingsClose = () => {
    setIsPrivacySettingsOpen(false)
  }
  
  // Render admin page without header/footer
  if (isAdminPage) {
    return (
      <div className="app-container">
        <main className="main-content">
          <AppRoutes 
            selectedLanguage={selectedLanguage}
            difficultyLevel={difficultyLevel}
            isVoiceSettingsOpen={isVoiceSettingsOpen}
            updateVoiceSettingsOpen={updateVoiceSettingsOpen}
          />
        </main>
      </div>
    )
  }
  
  return (
    <div className={`app-container ${isHomePage ? 'blurred-bg' : ''}`}>
      <Header
        selectedLanguage={selectedLanguage}
        changeLanguage={changeLanguage}
        difficultyLevel={difficultyLevel}
        setDifficultyLevel={setDifficultyLevel}
        onVoiceSettingsOpen={handleVoiceSettingsOpen}
        onPrivacySettingsOpen={handlePrivacySettingsOpen}
        sessionStatus={sessionStatus}
        countdownDisplay={countdownDisplay}
      />

      <main className="main-content">
        <AppRoutes
          selectedLanguage={selectedLanguage}
          difficultyLevel={difficultyLevel}
          isVoiceSettingsOpen={isVoiceSettingsOpen}
          updateVoiceSettingsOpen={updateVoiceSettingsOpen}
        />
      </main>

      <Footer />

      {/* Consent Management */}
      <ConsentBanner onOpenSettings={handlePrivacySettingsOpen} />
      <PrivacySettingsModal
        isOpen={isPrivacySettingsOpen}
        onClose={handlePrivacySettingsClose}
      />
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthGuard>
          <AppContent />
        </AuthGuard>
      </Router>
    </ErrorBoundary>
  )
}

export default App