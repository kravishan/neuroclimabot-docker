import { useState, useCallback, useEffect } from 'react'
import { sessionManager } from '@/services/session/sessionManager'

export const useSession = () => {
  const [sessionStatus, setSessionStatus] = useState(sessionManager.getSessionStatus())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const updateSessionStatus = useCallback(() => {
    const newStatus = sessionManager.getSessionStatus()
    console.log('useSession: updating session status:', newStatus)
    setSessionStatus(newStatus)
  }, [])

  useEffect(() => {
    let intervalId
    
    // Update session status immediately
    updateSessionStatus()
    
    // Set up regular updates every second
    intervalId = setInterval(() => {
      const newStatus = sessionManager.getSessionStatus()
      setSessionStatus(prevStatus => {
        // Only update if there's actually a change to avoid unnecessary re-renders
        if (JSON.stringify(prevStatus) !== JSON.stringify(newStatus)) {
          console.log('useSession: session status changed:', newStatus)
          return newStatus
        }
        return prevStatus
      })
    }, 1000)

    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [])

  const startConversation = useCallback(async (query, language = 'en', difficulty = 'low') => {
    setIsLoading(true)
    setError(null)
    
    try {
      const result = await sessionManager.startConversation(query, language, difficulty)
      // Force immediate update after starting conversation
      setTimeout(() => {
        updateSessionStatus()
      }, 100)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [updateSessionStatus])

  const continueConversation = useCallback(async (message, language, difficulty) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const result = await sessionManager.continueConversation(message, language, difficulty)
      updateSessionStatus()
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [updateSessionStatus])

  const endSession = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      await sessionManager.endSession()
      updateSessionStatus()
    } catch (err) {
      setError(err.message)
      console.error('Error ending session:', err)
    } finally {
      setIsLoading(false)
    }
  }, [updateSessionStatus])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const resetSession = useCallback(() => {
    sessionManager.resetSession()
    updateSessionStatus()
    setError(null)
  }, [updateSessionStatus])

  const recordActivity = useCallback(() => {
    if (sessionStatus.hasActiveSession) {
      sessionManager.onUserActivity()
      updateSessionStatus()
    }
  }, [sessionStatus.hasActiveSession, updateSessionStatus])

  return {
    sessionStatus,
    isLoading,
    error,
    startConversation,
    continueConversation,
    endSession,
    resetSession,
    recordActivity,
    clearError,
    updateSessionStatus,
    isSessionActive: sessionStatus.hasActiveSession,
    sessionId: sessionStatus.sessionId,
    messageCount: sessionStatus.messageCount,
    remainingMinutes: sessionStatus.remainingMinutes,
    remainingSeconds: sessionStatus.remainingSeconds,
    hasError: !!error,
    isInactive: sessionStatus.isInactive,
    showCountdown: sessionStatus.showCountdown,
    timeSinceLastActivity: sessionStatus.timeSinceLastActivity
  }
}