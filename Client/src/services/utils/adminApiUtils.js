import { API_CONFIG, DOCUMENT_CONFIG, ADMIN_CONFIG } from '@/constants/config'

export class AdminApiError extends Error {
  constructor(message, status, endpoint) {
    super(message)
    this.name = 'AdminApiError'
    this.status = status
    this.endpoint = endpoint
  }
}

export const apiUtils = {
  /**
   * API request with retry logic and better error handling
   */
  async request(url, options = {}, useDocumentApi = false) {
    const baseUrl = useDocumentApi ? API_CONFIG.DOCUMENT_URL : API_CONFIG.BASE_URL
    const fullUrl = `${baseUrl}${url}`
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: DOCUMENT_CONFIG.RETRY_CONFIG.TIMEOUT,
      ...options
    }

    let lastError
    const maxRetries = options.noRetry ? 1 : DOCUMENT_CONFIG.RETRY_CONFIG.MAX_RETRIES

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(
          () => controller.abort(),
          defaultOptions.timeout
        )

        const response = await fetch(fullUrl, {
          ...defaultOptions,
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          const errorData = await response.json().catch(() => null)
          const errorMessage = errorData?.detail || errorData?.message || `API Error: ${response.status}`
          throw new AdminApiError(errorMessage, response.status, url)
        }

        return await response.json()

      } catch (error) {
        lastError = error
        
        if (error.name === 'AbortError') {
          lastError = new AdminApiError('Request timeout', 408, url)
        }

        console.warn(`API request attempt ${attempt}/${maxRetries} failed:`, error.message)

        // Don't retry on client errors (4xx) except for timeouts
        if (error.status >= 400 && error.status < 500 && error.status !== 408) {
          break
        }

        // Wait before retrying (except on last attempt)
        if (attempt < maxRetries) {
          await new Promise(resolve => 
            setTimeout(resolve, DOCUMENT_CONFIG.RETRY_CONFIG.RETRY_DELAY * attempt)
          )
        }
      }
    }

    throw lastError
  },

  /**
   * Process API response and handle different response formats
   */
  processResponse(response, expectedDataKey = 'data') {
    // Handle different response formats from the two APIs
    if (response.success === false) {
      throw new Error(response.error || response.message || 'API request failed')
    }

    // Server 1 format: { success: true, data: {...} }
    if (response.success && response[expectedDataKey]) {
      return response[expectedDataKey]
    }

    // Server 2 format: { success: true, message: "...", task_id: "..." }
    if (response.success) {
      return response
    }

    // Direct data response
    if (!response.success && !response.error) {
      return response
    }

    throw new Error('Unexpected response format')
  },

  /**
   * Standardize document data format
   */
  standardizeDocuments(documents) {
    if (!Array.isArray(documents)) {
      return []
    }

    return documents.map(doc => ({
      name: doc.name || doc.doc_name || doc.filename || 'Unknown',
      bucket: doc.bucket || 'unknown',
      status: doc.status || 'pending',
      size: doc.size || null,
      last_processed: doc.last_processed || doc.processed_at || null,
      ...doc
    }))
  },

  /**
   * Standardize bucket data format 
   */
  standardizeBuckets(buckets) {
    if (!Array.isArray(buckets)) {
      return []
    }

    return buckets.map(bucket => {
      if (typeof bucket === 'string') {
        return {
          bucket_name: bucket,
          name: bucket,
          is_processable: true,
          document_count: 'Unknown'
        }
      }
      
      return {
        bucket_name: bucket.bucket_name || bucket.name,
        name: bucket.bucket_name || bucket.name,
        is_processable: bucket.is_processable !== false,
        document_count: bucket.document_count || 'Unknown',
        ...bucket
      }
    })
  },

  /**
   * Format processing options for API requests
   */
  formatProcessingOptions(options) {
    return {
      skip_processed: options.skipProcessed ?? true,
      include_chunking: options.includeChunking ?? true,
      include_summarization: options.includeSummarization ?? true,
      include_graphrag: options.includeGraphrag ?? true,
      max_documents_per_bucket: options.maxDocumentsPerBucket || null,
      max_documents: options.maxDocuments || null
    }
  },

  /**
   * Parse task status response
   */
  parseTaskStatus(response) {
    const data = response.data || response
    
    return {
      total: data.total_tasks || 0,
      running: data.status_breakdown?.running || 0,
      pending: data.status_breakdown?.pending || 0,
      completed: data.status_breakdown?.completed || 0,
      failed: data.status_breakdown?.failed || 0,
      hasActive: (data.status_breakdown?.running || 0) + (data.status_breakdown?.pending || 0) > 0
    }
  },

  /**
   * Format error messages for user display
   */
  formatErrorMessage(error, context = '') {
    if (error instanceof AdminApiError) {
      const contextMsg = context ? `${context}: ` : ''
      
      switch (error.status) {
        case 404:
          return `${contextMsg}Resource not found`
        case 401:
          return `${contextMsg}Authentication required`
        case 403:
          return `${contextMsg}Access denied`
        case 408:
          return `${contextMsg}Request timeout`
        case 500:
          return `${contextMsg}Server error`
        case 503:
          return `${contextMsg}Service unavailable`
        default:
          return `${contextMsg}${error.message}`
      }
    }

    return error.message || 'An unexpected error occurred'
  },

  /**
   * Check if error is retryable
   */
  isRetryableError(error) {
    if (error instanceof AdminApiError) {
      // Retry on server errors and timeouts
      return error.status >= 500 || error.status === 408
    }
    
    // Retry on network errors
    return error.name === 'NetworkError' || error.code === 'ECONNREFUSED'
  },

  /**
   * Validate processing options
   */
  validateProcessingOptions(options) {
    const hasAnyProcessing = 
      options.includeChunking || 
      options.includeSummarization || 
      options.includeGraphrag

    if (!hasAnyProcessing) {
      throw new Error('At least one processing option must be enabled')
    }

    if (options.maxDocumentsPerBucket && options.maxDocumentsPerBucket < 1) {
      throw new Error('Maximum documents per bucket must be at least 1')
    }

    return true
  },

  /**
   * Get polling interval for a specific data type
   */
  getPollingInterval(type) {
    return ADMIN_CONFIG.POLLING_INTERVALS[type.toUpperCase()] || 5000
  }
}

export default apiUtils