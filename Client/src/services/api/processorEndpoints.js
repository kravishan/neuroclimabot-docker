import { EXTERNAL_SERVICES } from '@/constants/config'

const processorRequest = async (endpoint, options = {}) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), EXTERNAL_SERVICES.PROCESSOR.TIMEOUT)

  try {
    const response = await fetch(`${EXTERNAL_SERVICES.PROCESSOR.BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.detail || errorData?.message || `API Error: ${response.status}`)
    }

    return response.json()
  } catch (error) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new Error('Request timeout')
    }

    throw error
  }
}

export const processorApi = {
  // Get services health status
  getServicesHealth: async () => {
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.SERVICES_HEALTH)
      return {
        success: true,
        data: data,
        services: data.services || {},
        timestamp: data.timestamp
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        services: {},
        timestamp: new Date().toISOString()
      }
    }
  },

  // Get webhook status
  getWebhookStatus: async () => {
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.WEBHOOK_STATUS)
      return {
        success: true,
        data: data,
        enabled: data.enabled,
        timestamp: data.timestamp
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        enabled: false,
        timestamp: new Date().toISOString()
      }
    }
  },

  // Enable webhook
  enableWebhook: async () => {
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.WEBHOOK_ENABLE, {
        method: 'POST'
      })
      return {
        success: true,
        data: data,
        enabled: data.enabled,
        message: data.message,
        timestamp: data.timestamp
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: `Failed to enable webhook: ${error.message}`
      }
    }
  },

  // Disable webhook
  disableWebhook: async () => {
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.WEBHOOK_DISABLE, {
        method: 'POST'
      })
      return {
        success: true,
        data: data,
        enabled: data.enabled,
        message: data.message,
        timestamp: data.timestamp
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: `Failed to disable webhook: ${error.message}`
      }
    }
  },

  // Toggle webhook
  toggleWebhook: async () => {
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.WEBHOOK_TOGGLE, {
        method: 'POST'
      })
      return {
        success: true,
        data: data,
        enabled: data.enabled,
        message: data.message,
        timestamp: data.timestamp
      }
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: `Failed to toggle webhook: ${error.message}`
      }
    }
  }
}
