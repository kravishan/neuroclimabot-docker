import { API_CONFIG, EXTERNAL_SERVICES } from '@/constants/config'

const apiRequest = async (endpoint, options = {}) => {
  const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(errorData?.detail || errorData?.message || `API Error: ${response.status}`)
  }
  
  return response.json()
}

// External service health check with timeout
const externalHealthCheck = async (baseUrl, endpoint, timeout = 10000) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const data = await response.json()
    return {
      success: true,
      data: data,
      status: 'healthy'
    }
  } catch (error) {
    clearTimeout(timeoutId)
    
    if (error.name === 'AbortError') {
      return {
        success: false,
        error: 'Timeout',
        status: 'unhealthy'
      }
    }
    
    return {
      success: false,
      error: error.message,
      status: 'unhealthy'
    }
  }
}

export const adminApi = {
  // Authentication
  login: (username, password) => 
    apiRequest('/api/v1/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    }),

  // Health check - Main API
  getHealth: () => apiRequest('/api/v1/health/'),
  
  // Health check - Translation Service
  getTranslateHealth: async () => {
    return externalHealthCheck(
      EXTERNAL_SERVICES.TRANSLATE_API.BASE_URL,
      API_CONFIG.ENDPOINTS.TRANSLATE_HEALTH,
      EXTERNAL_SERVICES.TRANSLATE_API.TIMEOUT
    )
  },
  
  // Health check - STP Service
  getStpHealth: async () => {
    return externalHealthCheck(
      EXTERNAL_SERVICES.STP_SERVICE.BASE_URL,
      API_CONFIG.ENDPOINTS.STP_HEALTH,
      EXTERNAL_SERVICES.STP_SERVICE.TIMEOUT
    )
  },
  
  // System stats
  getStats: () => apiRequest('/api/v1/admin/stats'),
  
  // Documents - Updated to handle both admin and document API responses
  getDocuments: (params = {}) => {
    const searchParams = new URLSearchParams(params)
    return apiRequest(`/api/v1/admin/documents?${searchParams}`)
  },
  
  // Logs
  getLogs: (params = {}) => {
    const searchParams = new URLSearchParams(params)
    return apiRequest(`/api/v1/admin/logs?${searchParams}`)
  },
  
  // Feedback stats
  getFeedbackStats: (days = 30) => 
    apiRequest(`/api/v1/feedback/stats?days=${days}`),
  
  // Admin actions
  clearCache: () => 
    apiRequest('/api/v1/admin/cache/clear', { method: 'POST' }),
  
  cleanupSessions: () => 
    apiRequest('/api/v1/admin/cleanup/sessions', { method: 'POST' }),
  
  clearFeedback: () => 
    apiRequest('/api/v1/admin/feedback/clear', { method: 'POST' }),
  
  clearLogs: () => 
    apiRequest('/api/v1/admin/logs/clear', { method: 'POST' }),
  
  // Batch processing - These now call the document API
  processAllBuckets: (config = {}) => 
    apiRequest('/api/v1/admin/batch/process-all', {
      method: 'POST',
      body: JSON.stringify(config)
    }),
  
  processBucket: (bucket, config = {}) => 
    apiRequest('/api/v1/admin/batch/process-bucket', {
      method: 'POST',
      body: JSON.stringify({ bucket, ...config })
    }),
  
  // Document actions
  processDocument: (docName, bucket, config = {}) => 
    apiRequest('/api/v1/admin/documents/process', {
      method: 'POST',
      body: JSON.stringify({ 
        document: docName, 
        bucket, 
        ...config 
      })
    }),
  
  getDocumentDetails: (docName, bucket) => 
    apiRequest(`/api/v1/admin/documents/details?name=${encodeURIComponent(docName)}&bucket=${encodeURIComponent(bucket)}`),

  // Methods for better error handling and data formatting
  getSystemHealth: async () => {
    try {
      const mainHealthData = await apiRequest('/api/v1/health/')
      const mainServices = mainHealthData?.services || {}

      // Determine overall status
      const allHealthy = Object.values(mainServices).every(status => status === 'healthy')

      return {
        success: true,
        data: {
          services: mainServices,
          status: allHealthy ? 'healthy' : 'degraded',
          details: {}
        },
        services: mainServices,
        status: allHealthy ? 'healthy' : 'degraded'
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        services: {},
        status: 'error'
      }
    }
  },

  getSystemStats: async () => {
    try {
      const stats = await apiRequest('/api/v1/admin/stats')
      return {
        success: true,
        data: stats,
        sessions: {
          active: stats.active_sessions || 0,
          total: stats.total_sessions || 0,
          avgDuration: stats.avg_session_duration || 0
        },
        performance: {
          avgResponseTime: stats.avg_response_time || 0,
          cacheHitRate: stats.cache_hit_rate || 0,
          systemUptime: stats.system_uptime || 0
        }
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        sessions: { active: 0, total: 0, avgDuration: 0 },
        performance: { avgResponseTime: 0, cacheHitRate: 0, systemUptime: 0 }
      }
    }
  },

  getFeedbackData: async () => {
    try {
      const feedback = await apiRequest('/api/v1/feedback/stats')
      return {
        success: true,
        data: feedback,
        totalFeedback: feedback.total_feedback || 0,
        positiveCount: feedback.positive_count || 0,
        negativeCount: feedback.negative_count || 0,
        satisfactionRate: feedback.satisfaction_rate || 0
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        totalFeedback: 0,
        positiveCount: 0,
        negativeCount: 0,
        satisfactionRate: 0
      }
    }
  },

  getSystemLogs: async (limit = 100, level = null) => {
    try {
      const params = new URLSearchParams({ limit: limit.toString() })
      if (level) params.append('level', level)
      
      const logs = await apiRequest(`/api/v1/admin/logs?${params}`)
      return {
        success: true,
        data: logs,
        logs: logs.logs || [],
        totalLines: logs.total_lines || 0
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        logs: [],
        totalLines: 0
      }
    }
  },

  // Safe admin actions with confirmation
  performAdminAction: async (action) => {
    try {
      const endpoints = {
        clearCache: '/api/v1/admin/cache/clear',
        cleanupSessions: '/api/v1/admin/cleanup/sessions', 
        clearFeedback: '/api/v1/admin/feedback/clear',
        clearLogs: '/api/v1/admin/logs/clear'
      }

      const endpoint = endpoints[action]
      if (!endpoint) {
        throw new Error(`Unknown admin action: ${action}`)
      }

      const result = await apiRequest(endpoint, { method: 'POST' })
      return {
        success: true,
        data: result,
        message: result.message || `${action} completed successfully`
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: `Failed to ${action}: ${error.message}`
      }
    }
  }
}