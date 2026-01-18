import { API_CONFIG } from '@/constants/config'

/**
 * API request wrapper with proper error handling
 */
const documentApiRequest = async (endpoint, options = {}) => {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
  
  try {
    const response = await fetch(`${API_CONFIG.DOCUMENT_URL}${endpoint}`, {
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
      const errorMessage = errorData?.detail || 
                          errorData?.message || 
                          `Document API Error: ${response.status} ${response.statusText}`
      throw new Error(errorMessage)
    }
    
    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)
    
    if (error.name === 'AbortError') {
      throw new Error('Request timeout - document API is taking too long to respond')
    }
    
    throw error
  }
}

/**
 * Document API service with comprehensive error handling and STP support
 */
export const documentApi = {
  // Document Processing with STP support
  processDocumentEnhanced: async (bucket, filename, options = {}) => {
    const params = new URLSearchParams()
    if (options.includeStp) {
      params.append('include_stp', 'true')
    }
    
    const endpoint = `/process/document${params.toString() ? `?${params}` : ''}`
    
    return documentApiRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        bucket,
        filename,
        include_chunking: options.includeChunking ?? true,
        include_summarization: options.includeSummarization ?? true,
        include_graphrag: options.includeGraphrag ?? true
      })
    })
  },
  
  processChunksOnly: async (bucket, filename) => {
    return documentApiRequest('/process/chunks', {
      method: 'POST',
      body: JSON.stringify({ bucket, filename })
    })
  },
  
  processSummaryOnly: async (bucket, filename) => {
    return documentApiRequest('/process/summary', {
      method: 'POST',
      body: JSON.stringify({ bucket, filename })
    })
  },
  
  processGraphRAGOnly: async (bucket, filename) => {
    return documentApiRequest('/process/graphrag', {
      method: 'POST',
      body: JSON.stringify({ bucket, filename })
    })
  },
  
  // NEW: STP Processing
  processStpOnly: async (bucket, filename) => {
    return documentApiRequest('/process/stp', {
      method: 'POST',
      body: JSON.stringify({ bucket, filename })
    })
  },
  
  // Search Operations
  searchChunks: async (query, bucket = null, limit = 10) => {
    return documentApiRequest('/search/chunks', {
      method: 'POST',
      body: JSON.stringify({ query, bucket, limit })
    })
  },
  
  searchSummaries: async (query, bucket = null, limit = 10) => {
    return documentApiRequest('/search/summaries', {
      method: 'POST',
      body: JSON.stringify({ query, bucket, limit })
    })
  },
  
  hybridSearch: async (query, bucket = null, chunkLimit = 5, summaryLimit = 3) => {
    const params = new URLSearchParams({
      query,
      chunk_limit: chunkLimit.toString(),
      summary_limit: summaryLimit.toString()
    })
    
    if (bucket) {
      params.append('bucket', bucket)
    }
    
    return documentApiRequest(`/search/hybrid?${params}`, {
      method: 'POST'
    })
  },
  
  // Batch Processing Operations with STP support
  batchProcessAll: async (options = {}) => {
    const params = new URLSearchParams()
    if (options.includeStp) {
      params.append('include_stp', 'true')
    }
    
    const endpoint = `/batch/process-all${params.toString() ? `?${params}` : ''}`
    
    const requestBody = {
      skip_processed: options.skipProcessed ?? true,
      include_chunking: options.includeChunking ?? true,
      include_summarization: options.includeSummarization ?? true,
      include_graphrag: options.includeGraphrag ?? true
    }
    
    if (options.maxDocumentsPerBucket) {
      requestBody.max_documents_per_bucket = options.maxDocumentsPerBucket
    }
    
    return documentApiRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify(requestBody)
    })
  },
  
  batchProcessBucket: async (bucket, options = {}) => {
    const params = new URLSearchParams()
    if (options.includeStp) {
      params.append('include_stp', 'true')
    }
    
    const endpoint = `/batch/process-bucket${params.toString() ? `?${params}` : ''}`
    
    const requestBody = {
      bucket,
      skip_processed: options.skipProcessed ?? true,
      include_chunking: options.includeChunking ?? true,
      include_summarization: options.includeSummarization ?? true,
      include_graphrag: options.includeGraphrag ?? true
    }
    
    if (options.maxDocuments) {
      requestBody.max_documents = options.maxDocuments
    }
    
    return documentApiRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify(requestBody)
    })
  },
  
  // Task Management
  getTaskStatus: async (taskId) => {
    return documentApiRequest(`/tasks/${taskId}`)
  },
  
  getAllTasks: async () => {
    return documentApiRequest('/tasks')
  },
  
  cleanupTasks: async (maxAgeHours = 24) => {
    return documentApiRequest(`/tasks/cleanup?max_age_hours=${maxAgeHours}`, {
      method: 'DELETE'
    })
  },
  
  // Queue Management
  addToQueue: async (bucket, filename, filePath = null) => {
    return documentApiRequest('/queue/add-task', {
      method: 'POST',
      body: JSON.stringify({ 
        bucket, 
        filename, 
        file_path: filePath 
      })
    })
  },

  // Document Tracking & Statistics
  getDocumentStatus: async (docName, bucket) => {
    const params = new URLSearchParams({ bucket })
    return documentApiRequest(`/tracking/document/${encodeURIComponent(docName)}?${params}`)
  },
  
  getAllDocuments: async (bucket = null) => {
    const params = new URLSearchParams()
    if (bucket) {
      params.append('bucket', bucket)
    }
    return documentApiRequest(`/tracking/documents?${params}`)
  },
  
  getProcessingStats: async () => {
    return documentApiRequest('/tracking/stats')
  },
  
  // MinIO & Storage Operations
  listBuckets: async () => {
    return documentApiRequest('/minio/buckets')
  },
  
  listBucketObjects: async (bucketName, limit = 100, offset = 0) => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString()
    })
    return documentApiRequest(`/minio/bucket/${bucketName}/objects?${params}`)
  },
  
  // Document Details
  getDocumentDetails: async (bucket, filename) => {
    const params = new URLSearchParams({ bucket })
    return documentApiRequest(`/tracking/document/${encodeURIComponent(filename)}?${params}`)
  },
  
  // Health Check
  getDocumentApiHealth: async () => {
    return documentApiRequest('/health')
  },
  
  // STP Health Check
  getStpHealth: async () => {
    return documentApiRequest('/stp/health')
  },
  
  // STP Statistics
  getStpStats: async () => {
    return documentApiRequest('/stp/stats')
  },
  
  // Advanced Processing Options with STP
  processWithCustomOptions: async (bucket, filename, customOptions) => {
    const params = new URLSearchParams()
    if (customOptions.includeStp) {
      params.append('include_stp', 'true')
    }
    
    const endpoint = `/process/document${params.toString() ? `?${params}` : ''}`
    
    const requestBody = {
      bucket,
      filename,
      include_chunking: customOptions.chunks ?? false,
      include_summarization: customOptions.summary ?? false,
      include_graphrag: customOptions.graphrag ?? false,
      ...customOptions.additionalParams
    }
    
    return documentApiRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify(requestBody)
    })
  },
  
  // Bulk Document Operations
  bulkProcessDocuments: async (documents, options = {}) => {
    const results = []
    
    for (const doc of documents) {
      try {
        const result = await documentApi.processDocumentEnhanced(
          doc.bucket, 
          doc.filename, 
          options
        )
        results.push({
          document: doc,
          status: 'success',
          result: result
        })
      } catch (error) {
        results.push({
          document: doc,
          status: 'failed',
          error: error.message
        })
      }
    }
    
    return {
      success: true,
      results: results,
      summary: {
        total: documents.length,
        successful: results.filter(r => r.status === 'success').length,
        failed: results.filter(r => r.status === 'failed').length
      }
    }
  },
  
  // Advanced Search
  searchWithFilters: async (query, filters = {}) => {
    const requestBody = {
      query,
      bucket: filters.bucket,
      limit: filters.limit || 10,
      include_metadata: filters.includeMetadata ?? false,
      similarity_threshold: filters.similarityThreshold
    }
    
    return documentApiRequest('/search/advanced', {
      method: 'POST',
      body: JSON.stringify(requestBody)
    })
  }
}

/**
 * Utility functions for API responses
 */
export const documentApiUtils = {
  /**
   * Check if a response indicates success
   */
  isSuccessResponse: (response) => {
    return response?.success === true || response?.status === 'success'
  },
  
  /**
   * Extract task ID from various response formats
   */
  extractTaskId: (response) => {
    return response?.task_id || response?.data?.task_id || null
  },
  
  /**
   * Format processing options for display
   */
  formatProcessingOptions: (options) => {
    const enabled = []
    if (options.includeChunking) enabled.push('Chunking')
    if (options.includeSummarization) enabled.push('Summarization')
    if (options.includeGraphrag) enabled.push('GraphRAG')
    if (options.includeStp) enabled.push('STP')
    return enabled.length > 0 ? enabled.join(', ') : 'None'
  },
  
  /**
   * Validate processing options
   */
  validateProcessingOptions: (options) => {
    const hasAnyOption = options.includeChunking || 
                        options.includeSummarization || 
                        options.includeGraphrag ||
                        options.includeStp
    
    if (!hasAnyOption) {
      throw new Error('At least one processing option must be enabled')
    }
    
    return true
  }
}

export default documentApi