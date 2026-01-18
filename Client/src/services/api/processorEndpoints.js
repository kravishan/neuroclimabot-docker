import { EXTERNAL_SERVICES } from '@/constants/config'

const processorRequest = async (endpoint, options = {}) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), EXTERNAL_SERVICES.PROCESSOR.TIMEOUT)

  const url = `${EXTERNAL_SERVICES.PROCESSOR.BASE_URL}${endpoint}`
  console.log(`[ProcessorAPI] Making request to: ${url}`)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    clearTimeout(timeoutId)

    console.log(`[ProcessorAPI] Response status for ${endpoint}:`, response.status)

    // Check if response is JSON
    const contentType = response.headers.get('content-type')
    const isJson = contentType && contentType.includes('application/json')

    if (!isJson) {
      const text = await response.text()
      console.error(`[ProcessorAPI] Non-JSON response for ${endpoint}:`, text.substring(0, 200))
      throw new Error(`Service returned HTML instead of JSON. The processor service may not be properly configured or accessible at ${url}`)
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      const errorMsg = errorData?.detail || errorData?.message || `API Error: ${response.status}`
      console.error(`[ProcessorAPI] Error response for ${endpoint}:`, errorMsg)
      throw new Error(errorMsg)
    }

    const data = await response.json()
    console.log(`[ProcessorAPI] Success response for ${endpoint}:`, data)
    return data
  } catch (error) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      console.error(`[ProcessorAPI] Request timeout for ${endpoint}`)
      throw new Error('Request timeout')
    }

    console.error(`[ProcessorAPI] Request failed for ${endpoint}:`, error)
    throw error
  }
}

export const processorApi = {
  // Get services health status
  getServicesHealth: async () => {
    console.log('[ProcessorAPI] getServicesHealth called')
    try {
      const data = await processorRequest(EXTERNAL_SERVICES.PROCESSOR.ENDPOINTS.SERVICES_HEALTH)
      console.log('[ProcessorAPI] getServicesHealth response:', data)
      console.log('[ProcessorAPI] Services in response:', data.services)
      return {
        success: true,
        data: data,
        services: data.services || {},
        timestamp: data.timestamp
      }
    } catch (error) {
      console.error('[ProcessorAPI] getServicesHealth error:', error.message)
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
