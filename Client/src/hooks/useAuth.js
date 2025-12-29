import { useState, useEffect, useCallback } from 'react'
import { authService } from '@/services/auth/authService'

export const useAuth = () => {
  const [authStatus, setAuthStatus] = useState({
    isAuthenticated: false,
    hasToken: false,
    tokenExpiry: null,
    timeUntilExpiry: 0,
    isExpiringSoon: false,
    daysUntilExpiry: 0
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  // Update auth status
  const updateAuthStatus = useCallback(() => {
    try {
      const status = authService.getAuthStatus()
      setAuthStatus(status)
      setError(null)
    } catch (err) {
      console.error('Error updating auth status:', err)
      setError(err.message)
    }
  }, [])

  // Initialize auth status on mount
  useEffect(() => {
    updateAuthStatus()
    setIsLoading(false)
  }, [updateAuthStatus])

  // Set up periodic status updates
  useEffect(() => {
    const interval = setInterval(() => {
      updateAuthStatus()
    }, 60000) // Update every minute

    return () => clearInterval(interval)
  }, [updateAuthStatus])

  // Request access token
  const requestToken = useCallback(async (email) => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await authService.requestToken(email)
      updateAuthStatus()
      
      if (result.success) {
        return {
          success: true,
          message: result.message
        }
      } else {
        setError(result.error)
        return {
          success: false,
          error: result.error
        }
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to request access token'
      setError(errorMessage)
      return {
        success: false,
        error: errorMessage
      }
    } finally {
      setIsLoading(false)
    }
  }, [updateAuthStatus])

  // Validate access token
  const validateToken = useCallback(async (token) => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await authService.validateToken(token)
      updateAuthStatus()
      
      if (result.success) {
        return {
          success: true,
          message: result.message
        }
      } else {
        setError(result.error)
        return {
          success: false,
          error: result.error
        }
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to validate access token'
      setError(errorMessage)
      return {
        success: false,
        error: errorMessage
      }
    } finally {
      setIsLoading(false)
    }
  }, [updateAuthStatus])

  // Logout user
  const logout = useCallback(() => {
    setIsLoading(true)
    setError(null)

    try {
      authService.logout()
      updateAuthStatus()
    } catch (err) {
      console.error('Error during logout:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [updateAuthStatus])

  // Refresh token
  const refreshToken = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const refreshed = await authService.refreshTokenIfNeeded()
      updateAuthStatus()
      
      return {
        success: refreshed,
        message: refreshed ? 'Token refreshed successfully' : 'Token refresh not needed'
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to refresh token'
      setError(errorMessage)
      return {
        success: false,
        error: errorMessage
      }
    } finally {
      setIsLoading(false)
    }
  }, [updateAuthStatus])

  // Clear error
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // Get current token
  const getToken = useCallback(() => {
    return authService.getToken()
  }, [])

  // Format time until expiry
  const formatTimeUntilExpiry = useCallback(() => {
    const { timeUntilExpiry } = authStatus
    
    if (timeUntilExpiry <= 0) return 'Expired'
    
    const days = Math.floor(timeUntilExpiry / (24 * 60 * 60 * 1000))
    const hours = Math.floor((timeUntilExpiry % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))
    const minutes = Math.floor((timeUntilExpiry % (60 * 60 * 1000)) / (60 * 1000))
    
    if (days > 0) {
      return `${days} day${days !== 1 ? 's' : ''}`
    } else if (hours > 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''}`
    } else if (minutes > 0) {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`
    } else {
      return 'Less than 1 minute'
    }
  }, [authStatus.timeUntilExpiry])

  return {
    // Status
    ...authStatus,
    isLoading,
    error,
    
    // Actions
    requestToken,
    validateToken,
    logout,
    refreshToken,
    clearError,
    getToken,
    updateAuthStatus,
    
    // Utilities
    formatTimeUntilExpiry
  }
}