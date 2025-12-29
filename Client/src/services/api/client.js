import axios from 'axios'
import { API_CONFIG, SESSION_CONFIG } from '@/constants/config'
import { authService } from '@/services/auth/authService'

const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
})

// Request interceptor - Updated to include auth token
apiClient.interceptors.request.use(
  (config) => {
    const sessionId = sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)

    // Check if authentication is enabled
    const isAuthEnabled = import.meta.env.VITE_AUTH_ENABLED !== 'false'

    // Get auth token (will be null if auth is disabled or no token available)
    let authToken = null

    // Add auth token to all requests (only if auth is enabled)
    if (isAuthEnabled) {
      authToken = authService.getToken()
      if (authToken) {
        config.headers['Authorization'] = `Bearer ${authToken}`
        console.log('Added auth token to request:', config.url)
      } else {
        console.warn('No auth token available for request:', config.url)
      }
    } else {
      console.log('Authentication disabled, skipping auth token for request:', config.url)
    }

    // Add session ID to headers for continue and session management endpoints
    if (sessionId && (
      config.url?.includes('/continue/') ||
      config.url?.includes('/sessions/')
    )) {
      config.headers['X-Session-ID'] = sessionId
    }

    // Add content type for JSON requests
    if (!config.headers['Content-Type']) {
      config.headers['Content-Type'] = 'application/json'
    }

    console.log('API Request:', {
      method: config.method?.toUpperCase(),
      url: config.url,
      hasAuthToken: !!authToken,
      hasSessionId: !!sessionId,
      sessionInUrl: config.url?.includes('/continue/') || config.url?.includes('/sessions/')
    })

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - Updated to handle auth errors
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      status: response.status,
      url: response.config?.url,
      hasSessionId: !!response.data?.session_id
    })
    return response
  },
  (error) => {
    console.error('API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message: error.response?.data?.detail || error.message
    })
    
    // Handle authentication errors (only if auth is enabled)
    const isAuthEnabled = import.meta.env.VITE_AUTH_ENABLED !== 'false'
    if (isAuthEnabled && error.response?.status === 401) {
      console.warn('Authentication failed - token may be invalid or expired')

      // Check if this is not an auth endpoint to avoid loops
      if (!error.config?.url?.includes('/auth/')) {
        console.log('Clearing invalid token and redirecting to auth')
        authService.clearToken()

        // Trigger a page reload to show auth page
        setTimeout(() => {
          window.location.reload()
        }, 100)
      }
    }
    
    // Handle session-related errors
    if (error.response?.status === 404 && error.config?.url?.includes('/continue/')) {
      console.warn('Session not found - clearing stored session ID')
      sessionStorage.removeItem(SESSION_CONFIG.STORAGE_KEY)
    }
    
    // Handle rate limiting or server errors
    if (error.response?.status === 429) {
      console.warn('Rate limit exceeded')
    }
    
    if (error.response?.status >= 500) {
      console.error('Server error occurred')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient