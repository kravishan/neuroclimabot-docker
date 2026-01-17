import React from 'react'
import { Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ROUTES } from '@/constants/routes'

// Page Components
import HomePage from '@/pages/HomePage'
import ResponsePage from '@/pages/ResponsePage'
import VoiceModelPage from '@/pages/VoiceModelPage'
import ExplorePage from '@/pages/ExplorePage'
import QuestionnairePage from '@/pages/QuestionnairePage'
import DashboardPage from '@/pages/DashboardPage'
import AdminDashboard from '@/pages/AdminDashboard'
import { PrivacyPolicy, Disclaimer, TermsOfUse, LearnMore } from '@/pages/LegalPages'
import NotFoundPage from '@/pages/NotFoundPage'

const AppRoutes = ({ selectedLanguage, difficultyLevel, isVoiceSettingsOpen, updateVoiceSettingsOpen }) => {
  const { t } = useTranslation()

  return (
    <Routes>
      <Route
        path={ROUTES.HOME}
        element={
          <HomePage 
            selectedLanguage={selectedLanguage} 
            difficultyLevel={difficultyLevel} 
          />
        }
      />
      
      <Route path={ROUTES.RESPONSE} element={<ResponsePage />} />
      
      <Route 
        path={ROUTES.VOICE_MODEL} 
        element={
          <VoiceModelPage 
            isSettingsOpen={isVoiceSettingsOpen}
            updateVoiceSettingsOpen={updateVoiceSettingsOpen}
          />
        } 
      />
      
      <Route path={ROUTES.EXPLORE} element={<ExplorePage />} />
      <Route path={ROUTES.QUESTIONNAIRE} element={<QuestionnairePage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path={ROUTES.PRIVACY} element={<PrivacyPolicy />} />
      <Route path={ROUTES.DISCLAIMER} element={<Disclaimer />} />
      <Route path={ROUTES.TERMS} element={<TermsOfUse />} />
      <Route path={ROUTES.LEARN_MORE} element={<LearnMore />} />
      <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
    </Routes>
  )
}

export default AppRoutes