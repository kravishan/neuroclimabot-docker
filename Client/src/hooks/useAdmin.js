import { useState, useCallback } from 'react'
import { adminApi } from '@/services/api/adminEndpoints'

export const useAdmin = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const executeWithLoading = useCallback(async (apiCall, errorMessage = 'Operation failed') => {
    setLoading(true)
    setError(null)
    
    try {
      const result = await apiCall()
      return result
    } catch (err) {
      const message = err.message || errorMessage
      setError(message)
      throw new Error(message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Authentication
  const login = useCallback((username, password) => 
    executeWithLoading(() => adminApi.login(username, password), 'Login failed')
  , [executeWithLoading])

  // Data fetching
  const getHealth = useCallback(() => 
    executeWithLoading(() => adminApi.getHealth(), 'Failed to fetch health data')
  , [executeWithLoading])

  const getStats = useCallback(() => 
    executeWithLoading(() => adminApi.getStats(), 'Failed to fetch stats')
  , [executeWithLoading])

  const getDocuments = useCallback((params) => 
    executeWithLoading(() => adminApi.getDocuments(params), 'Failed to fetch documents')
  , [executeWithLoading])

  const getLogs = useCallback((params) => 
    executeWithLoading(() => adminApi.getLogs(params), 'Failed to fetch logs')
  , [executeWithLoading])

  const getFeedbackStats = useCallback((days) => 
    executeWithLoading(() => adminApi.getFeedbackStats(days), 'Failed to fetch feedback stats')
  , [executeWithLoading])

  // Admin actions
  const clearCache = useCallback(() => 
    executeWithLoading(() => adminApi.clearCache(), 'Failed to clear cache')
  , [executeWithLoading])

  const cleanupSessions = useCallback(() => 
    executeWithLoading(() => adminApi.cleanupSessions(), 'Failed to cleanup sessions')
  , [executeWithLoading])

  const clearFeedback = useCallback(() => 
    executeWithLoading(() => adminApi.clearFeedback(), 'Failed to clear feedback')
  , [executeWithLoading])

  const clearLogs = useCallback(() => 
    executeWithLoading(() => adminApi.clearLogs(), 'Failed to clear logs')
  , [executeWithLoading])

  // Batch processing
  const processAllBuckets = useCallback((config) => 
    executeWithLoading(() => adminApi.processAllBuckets(config), 'Failed to process buckets')
  , [executeWithLoading])

  const processBucket = useCallback((bucket, config) => 
    executeWithLoading(() => adminApi.processBucket(bucket, config), 'Failed to process bucket')
  , [executeWithLoading])

  // Document operations
  const processDocument = useCallback((docName, bucket, config) => 
    executeWithLoading(() => adminApi.processDocument(docName, bucket, config), 'Failed to process document')
  , [executeWithLoading])

  const getDocumentDetails = useCallback((docName, bucket) => 
    executeWithLoading(() => adminApi.getDocumentDetails(docName, bucket), 'Failed to get document details')
  , [executeWithLoading])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    clearError,
    
    // Authentication
    login,
    
    // Data fetching
    getHealth,
    getStats,
    getDocuments,
    getLogs,
    getFeedbackStats,
    
    // Admin actions
    clearCache,
    cleanupSessions,
    clearFeedback,
    clearLogs,
    
    // Batch processing
    processAllBuckets,
    processBucket,
    
    // Document operations
    processDocument,
    getDocumentDetails
  }
}