import React, { useState, useEffect } from 'react'
import { authService } from '@/services/auth/authService'
import AuthPage from '@/pages/AuthPage'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import './AuthGuard.css'

const AuthGuard = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [authStatus, setAuthStatus] = useState({})

  // Check if authentication is enabled via environment variable
  const isAuthEnabled = import.meta.env.VITE_AUTH_ENABLED !== 'false'

  // Check authentication status on mount
  useEffect(() => {
    // If auth is disabled, skip authentication check
    if (!isAuthEnabled) {
      console.log('Authentication disabled (VITE_AUTH_ENABLED=false), skipping auth check')
      setIsAuthenticated(true)
      setIsLoading(false)
      return
    }

    checkAuthStatus()
  }, [isAuthEnabled])

  // Set up token expiry check interval
  useEffect(() => {
    let expiryCheckInterval

    // Only set up expiry check interval if auth is enabled
    if (isAuthEnabled && isAuthenticated) {
      // Check token expiry every hour
      expiryCheckInterval = setInterval(() => {
        // Update auth status
        const newStatus = authService.getAuthStatus()
        setAuthStatus(newStatus)

        // If token expired, force re-authentication
        if (!newStatus.isAuthenticated) {
          console.log('Token expired, requesting re-authentication')
          setIsAuthenticated(false)
        }
      }, 60 * 60 * 1000) // Every hour
    }

    return () => {
      if (expiryCheckInterval) {
        clearInterval(expiryCheckInterval)
      }
    }
  }, [isAuthEnabled, isAuthenticated])

  const checkAuthStatus = async () => {
    setIsLoading(true)

    try {
      // Get current auth status from service
      const status = authService.getAuthStatus()
      setAuthStatus(status)
      
      if (status.isAuthenticated) {
        console.log('User is authenticated with valid token')
        setIsAuthenticated(true)

        // Log warning if token is expiring soon
        if (status.isExpiringSoon) {
          console.log('Token is expiring soon:', status.expiryMessage)
        }
      } else {
        console.log('User is not authenticated or token is expired')
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Error checking auth status:', error)
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAuthenticated = () => {
    console.log('User successfully authenticated')
    setIsAuthenticated(true)
    
    // Update auth status after successful authentication
    const newStatus = authService.getAuthStatus()
    setAuthStatus(newStatus)
  }

  // Show loading spinner during initial auth check
  if (isLoading) {
    return (
      <div className="auth-guard-loading">
        <div className="loading-content">
          <img src="/assets/images/logo.svg" alt="NeuroClima Bot" className="loading-logo" />
          <LoadingSpinner size="medium" text="Checking authentication..." />
        </div>
      </div>
    )
  }

  // Show auth page if not authenticated
  if (!isAuthenticated) {
    return <AuthPage onAuthenticated={handleAuthenticated} />
  }

  // Show main application if authenticated
  return (
    <>
      {children}
      {/* Optional: Show token expiry warning (only if auth is enabled) */}
      {isAuthEnabled && authStatus.isExpiringSoon && authStatus.daysUntilExpiry <= 3 && (
        <TokenExpiryWarning
          daysRemaining={authStatus.daysUntilExpiry}
          onRefresh={checkAuthStatus}
        />
      )}
    </>
  )
}

// Optional token expiry warning component
const TokenExpiryWarning = ({ daysRemaining, onRefresh }) => {
  const [isVisible, setIsVisible] = useState(true)

  if (!isVisible) return null

  return (
    <div className="token-expiry-warning">
      <div className="expiry-content">
        <span className="expiry-icon">⚠️</span>
        <div className="expiry-text">
          <strong>Token Expiring Soon</strong>
          <p>Your access token expires in {daysRemaining} day{daysRemaining !== 1 ? 's' : ''}.</p>
        </div>
        <div className="expiry-actions">
          <button 
            onClick={() => {
              authService.logout()
              window.location.reload()
            }}
            className="expiry-button refresh-button"
          >
            Get New Token
          </button>
          <button 
            onClick={() => setIsVisible(false)}
            className="expiry-button dismiss-button"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

export default AuthGuard