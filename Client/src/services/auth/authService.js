import apiClient from '@/services/api/client'

const TOKEN_STORAGE_KEY = 'neuroclima_access_token'
const TOKEN_EXPIRY_KEY = 'neuroclima_token_expiry'

class AuthService {
  constructor() {
    this.token = null
    this.tokenExpiry = null
    this.loadTokenFromStorage()
  }

  // Load token from localStorage on service initialization
  loadTokenFromStorage() {
    try {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
      const storedExpiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
      
      if (storedToken && storedExpiry) {
        const expiryDate = new Date(storedExpiry)
        
        if (expiryDate > new Date()) {
          this.token = storedToken
          this.tokenExpiry = expiryDate
          console.log('Valid token loaded from storage')
        } else {
          console.log('Expired token found, clearing storage')
          this.clearToken()
        }
      }
    } catch (error) {
      console.error('Error loading token from storage:', error)
      this.clearToken()
    }
  }

  // Save token to localStorage
  saveTokenToStorage(token, expiryDate) {
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryDate.toISOString())
      this.token = token
      this.tokenExpiry = expiryDate
      console.log('Token saved to storage')
    } catch (error) {
      console.error('Error saving token to storage:', error)
      throw new Error('Failed to save authentication token')
    }
  }

  // Clear token from storage and memory
  clearToken() {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(TOKEN_EXPIRY_KEY)
      this.token = null
      this.tokenExpiry = null
      console.log('Token cleared from storage')
    } catch (error) {
      console.error('Error clearing token:', error)
    }
  }

  // Request access token via email
  async requestToken(email) {
    try {
      const response = await apiClient.post('/api/v1/auth/request-token', {
        email: email.trim()
      })

      return {
        success: true,
        message: response.data.message || 'Access token has been sent to your email.',
        data: response.data
      }
    } catch (error) {
      console.error('Error requesting token:', error)
      
      let errorMessage = 'Failed to request access token'
      
      if (error.response) {
        const status = error.response.status
        const data = error.response.data
        
        if (status === 400) {
          errorMessage = data.detail || 'Invalid email address'
        } else if (status === 429) {
          errorMessage = 'Too many requests. Please try again later.'
        } else if (status === 500) {
          errorMessage = 'Server error. Please try again later.'
        } else {
          errorMessage = data.detail || errorMessage
        }
      } else if (error.code === 'ECONNABORTED') {
        errorMessage = 'Request timeout. Please try again.'
      } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
        errorMessage = 'Cannot connect to authentication server'
      }

      return {
        success: false,
        error: errorMessage
      }
    }
  }

  // Validate and save token with enhanced error handling
  async validateToken(token) {
    try {
      const response = await apiClient.post('/api/v1/auth/validate-token', {
        token: token.trim()
      })

      if (response.data.success && response.data.valid) {
        // Calculate expiry date from backend response
        const expiresIn = response.data.expires_in || (30 * 24 * 60 * 60) // 30 days in seconds
        const expiryDate = new Date(Date.now() + (expiresIn * 1000))
        
        this.saveTokenToStorage(token.trim(), expiryDate)

        return {
          success: true,
          message: 'Access token validated successfully!',
          expiryDate: expiryDate,
          daysRemaining: response.data.days_remaining,
          hoursRemaining: response.data.hours_remaining
        }
      } else {
        // Handle detailed validation errors from backend
        const errorType = response.data.error_type || 'validation_error'
        let errorMessage = response.data.error || 'Invalid access token'
        
        return {
          success: false,
          error: errorMessage,
          errorType: errorType,
          actionRequired: response.data.action_required || 'request_new_token'
        }
      }
    } catch (error) {
      console.error('Error validating token:', error)
      
      let errorMessage = 'Failed to validate access token'
      let errorType = 'network_error'
      let actionRequired = 'retry_or_request_new_token'
      
      if (error.response) {
        const status = error.response.status
        const data = error.response.data
        
        if (status === 401 && data.detail) {
          // Handle detailed 401 errors from updated backend
          const detail = data.detail
          errorMessage = detail.ui_message || detail.message || 'Authentication failed'
          errorType = detail.error || 'token_error'
          actionRequired = detail.action_required || 'request_new_token'
          
          // Clear token if it's expired or invalid
          if (errorType === 'token_expired' || errorType === 'invalid_token') {
            this.clearToken()
          }
        } else if (status === 400) {
          errorMessage = data.detail?.ui_message || data.detail?.message || data.detail || 'Invalid token format'
          errorType = data.detail?.error || 'format_error'
        } else if (status === 500) {
          errorMessage = 'Server error. Please try again later.'
          errorType = 'server_error'
        } else {
          errorMessage = data.detail?.ui_message || data.detail?.message || data.detail || errorMessage
        }
      }

      return {
        success: false,
        error: errorMessage,
        errorType: errorType,
        actionRequired: actionRequired
      }
    }
  }

  // Enhanced method to handle API call authentication errors
  handleApiAuthError(error) {
    if (error.response && error.response.status === 401) {
      const data = error.response.data
      
      if (data.detail) {
        const detail = data.detail
        const errorType = detail.error || 'authentication_error'
        const uiMessage = detail.ui_message || detail.message || 'Authentication failed'
        
        // Clear token for expired/invalid tokens
        if (errorType === 'token_expired' || errorType === 'invalid_token') {
          this.clearToken()
        }
        
        return {
          isAuthError: true,
          errorType: errorType,
          message: uiMessage,
          actionRequired: detail.action_required || 'request_new_token',
          expiredAt: detail.expired_at,
          daysExpired: detail.days_expired,
          hoursExpired: detail.hours_expired
        }
      }
    }
    
    return {
      isAuthError: false,
      message: 'Network or server error'
    }
  }

  // Check if user has valid token
  isAuthenticated() {
    if (!this.token || !this.tokenExpiry) {
      return false
    }
    
    // Check if token is expired
    return this.tokenExpiry > new Date()
  }

  // Get current token
  getToken() {
    if (this.isAuthenticated()) {
      return this.token
    }
    return null
  }

  // Get token expiry info
  getTokenExpiry() {
    return this.tokenExpiry
  }

  // Get time until token expires
  getTimeUntilExpiry() {
    if (!this.tokenExpiry) {
      return 0
    }
    
    const now = new Date()
    const expiry = new Date(this.tokenExpiry)
    return Math.max(0, expiry.getTime() - now.getTime())
  }

  // Check if token expires soon (within 24 hours)
  isTokenExpiringSoon() {
    const timeUntilExpiry = this.getTimeUntilExpiry()
    const twentyFourHours = 24 * 60 * 60 * 1000
    
    return timeUntilExpiry > 0 && timeUntilExpiry <= twentyFourHours
  }

  // Get formatted expiry message
  getExpiryMessage() {
    if (!this.tokenExpiry) {
      return 'No token available'
    }

    const timeUntilExpiry = this.getTimeUntilExpiry()
    
    if (timeUntilExpiry <= 0) {
      return 'Token has expired'
    }

    const days = Math.floor(timeUntilExpiry / (24 * 60 * 60 * 1000))
    const hours = Math.floor((timeUntilExpiry % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))
    
    if (days > 0) {
      return `Token expires in ${days} day${days !== 1 ? 's' : ''}`
    } else if (hours > 0) {
      return `Token expires in ${hours} hour${hours !== 1 ? 's' : ''}`
    } else {
      const minutes = Math.floor((timeUntilExpiry % (60 * 60 * 1000)) / (60 * 1000))
      return `Token expires in ${minutes} minute${minutes !== 1 ? 's' : ''}`
    }
  }

  // Logout user
  logout() {
    this.clearToken()
    
    // Optionally notify server about logout
    try {
      apiClient.post('/api/v1/auth/logout', {}, {
        timeout: 5000
      }).catch(error => {
        console.warn('Error notifying server about logout:', error)
      })
    } catch (error) {
      console.warn('Error during logout cleanup:', error)
    }
  }

  // Get authentication status with enhanced info
  getAuthStatus() {
    const isAuthenticated = this.isAuthenticated()
    const timeUntilExpiry = this.getTimeUntilExpiry()
    
    return {
      isAuthenticated,
      hasToken: !!this.token,
      tokenExpiry: this.tokenExpiry,
      timeUntilExpiry,
      isExpiringSoon: this.isTokenExpiringSoon(),
      daysUntilExpiry: Math.floor(timeUntilExpiry / (24 * 60 * 60 * 1000)),
      hoursUntilExpiry: Math.floor((timeUntilExpiry % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000)),
      expiryMessage: this.getExpiryMessage()
    }
  }

  // Create user-friendly error messages for UI display
  createUserFriendlyErrorMessage(errorType, originalMessage, additionalInfo = {}) {
    switch (errorType) {
      case 'token_expired':
        if (additionalInfo.daysExpired > 0) {
          return `Your access token expired ${additionalInfo.daysExpired} day${additionalInfo.daysExpired !== 1 ? 's' : ''} ago. Please request a new one.`
        } else if (additionalInfo.hoursExpired > 0) {
          return `Your access token expired ${additionalInfo.hoursExpired} hour${additionalInfo.hoursExpired !== 1 ? 's' : ''} ago. Please request a new one.`
        }
        return 'Your access token has expired. Please request a new one.'
      
      case 'invalid_token':
        return 'The access token you provided is not valid. Please request a new token.'
      
      case 'token_not_found':
        return 'Access token not found. Please request a new token to continue.'
      
      case 'format_error':
        return 'Invalid token format. Please enter a valid 6-digit access code.'
      
      case 'missing_token':
        return 'Please provide an access token to continue.'
      
      default:
        return originalMessage || 'Authentication error. Please try again or request a new token.'
    }
  }
}

export const authService = new AuthService()