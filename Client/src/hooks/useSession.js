/**
 * useSession Hook
 *
 * React hook for managing session state with WebSocket real-time updates.
 * Subscribes to WebSocket status updates from SessionManager.
 */

import { useState, useCallback, useEffect } from 'react'
import { sessionManager } from '@/services/session/sessionManager'

export const useSession = () => {
  const [sessionStatus, setSessionStatus] = useState(sessionManager.getSessionStatus())
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Subscribe to WebSocket status updates
  useEffect(() => {
    console.log('[useSession] Subscribing to session status updates')

    // Set initial status
    setSessionStatus(sessionManager.getSessionStatus())

    // Subscribe to status updates from WebSocket
    const unsubscribe = sessionManager.onStatusUpdate((status) => {
      console.log('[useSession] Status update received:', status)
      setSessionStatus(status)
    })

    // Cleanup: Unsubscribe on unmount
    return () => {
      console.log('[useSession] Unsubscribing from session status updates')
      unsubscribe()
    }
  }, [])

  const startConversation = useCallback(async (query, language = 'en', difficulty = 'low') => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await sessionManager.startConversation(query, language, difficulty)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const continueConversation = useCallback(async (message, language, difficulty) => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await sessionManager.continueConversation(message, language, difficulty)
      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const endSession = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      await sessionManager.endSession()
    } catch (err) {
      setError(err.message)
      console.error('[useSession] Error ending session:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const recordActivity = useCallback(() => {
    if (sessionStatus.isSessionActive) {
      sessionManager.onUserActivity()
    }
  }, [sessionStatus.isSessionActive])

  return {
    // State
    sessionStatus,
    isLoading,
    error,

    // Methods
    startConversation,
    continueConversation,
    endSession,
    recordActivity,
    clearError,

    // Computed properties (for backward compatibility)
    isSessionActive: sessionStatus.isSessionActive,
    sessionId: sessionStatus.sessionId,
    messageCount: sessionStatus.messageCount,
    remainingMinutes: sessionStatus.minutes,
    remainingSeconds: sessionStatus.seconds,
    hasError: !!error,
    isWarning: sessionStatus.isWarning,
    isCritical: sessionStatus.isCritical,
    showCountdown: sessionStatus.isWarning || sessionStatus.isCritical
  }
}