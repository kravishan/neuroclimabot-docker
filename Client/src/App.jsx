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
  const [isPrivacySettingsOpen, setIsPrivacySettingsOpen] = useState(false)

  const location = useLocation()
  const isHomePage = location.pathname === '/' || location.pathname === '/index'
  const isResponsePage = location.pathname.includes('/response/')
  const isAdminPage = location.pathname === '/admin'

  // Get session status with WebSocket-based countdown
  const {
    sessionStatus,
    isSessionActive,
    remainingMinutes,
    remainingSeconds,
    isWarning,
    isCritical,
    showCountdown
  } = useSession()

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
          />
        </main>
      </div>
    )
  }
  
  // Create countdown display object for Header (WebSocket-based)
  const countdownDisplay = {
    minutes: remainingMinutes,
    seconds: remainingSeconds,
    isWarning,
    isCritical,
    showCountdown
  }

  return (
    <div className={`app-container ${isHomePage ? 'blurred-bg' : ''}`}>
      <Header
        selectedLanguage={selectedLanguage}
        changeLanguage={changeLanguage}
        difficultyLevel={difficultyLevel}
        setDifficultyLevel={setDifficultyLevel}
        onPrivacySettingsOpen={handlePrivacySettingsOpen}
        sessionStatus={sessionStatus}
        countdownDisplay={countdownDisplay}
      />

      <main className="main-content">
        <AppRoutes
          selectedLanguage={selectedLanguage}
          difficultyLevel={difficultyLevel}
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