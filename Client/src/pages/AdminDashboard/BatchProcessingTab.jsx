import React, { useState, useEffect } from 'react'
import {
  Activity,
  HardDrive,
  Database,
  Play,
  RefreshCw,
  CheckSquare,
  AlertTriangle,
  Pause,
  Trash2,
  Clock,
  Users,
  FileText,
  Zap,
  Settings,
  Info,
  Target
} from 'lucide-react'
import { documentApi } from '@/services/api/documentEndpoints'
import { DOCUMENT_CONFIG } from '@/constants/config'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import './BatchProcessingTab.css'

const BatchProcessingTab = () => {
  const [buckets, setBuckets] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [processingOptions, setProcessingOptions] = useState({
    skipProcessed: DOCUMENT_CONFIG.BATCH_PROCESSING_OPTIONS.SKIP_PROCESSED,
    includeChunking: DOCUMENT_CONFIG.BATCH_PROCESSING_OPTIONS.INCLUDE_CHUNKING,
    includeSummarization: DOCUMENT_CONFIG.BATCH_PROCESSING_OPTIONS.INCLUDE_SUMMARIZATION,
    includeGraphrag: DOCUMENT_CONFIG.BATCH_PROCESSING_OPTIONS.INCLUDE_GRAPHRAG,
    includeStp: DOCUMENT_CONFIG.BATCH_PROCESSING_OPTIONS.INCLUDE_STP, // STP enabled by default
    maxDocumentsPerBucket: null
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)

    try {
      await loadBuckets()
    } catch (error) {
      console.error('Failed to load batch processing data:', error)
      setError('Failed to load data: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadBuckets = async () => {
    try {
      const result = await documentApi.listBuckets()
      console.log('Buckets API response:', result)
      
      let extractedBuckets = []
      
      if (result?.status === 'success' && result?.data) {
        const data = result.data
        extractedBuckets = data.processable_buckets || 
                         data.all_buckets || 
                         data.buckets || 
                         []
      } else if (result?.success && result?.data) {
        const data = result.data
        extractedBuckets = data.processable_buckets || 
                         data.all_buckets || 
                         data.buckets || 
                         []
      } else if (Array.isArray(result)) {
        extractedBuckets = result
      } else if (result?.data && Array.isArray(result.data)) {
        extractedBuckets = result.data
      }
      
      if (Array.isArray(extractedBuckets)) {
        setBuckets(extractedBuckets)
      } else {
        console.warn('Could not extract buckets array')
        setBuckets([])
      }
      
    } catch (error) {
      console.error('Failed to load buckets:', error)
      setBuckets([])
    }
  }


  const processAllBuckets = async () => {
    if (!validateProcessingOptions()) return

    if (!window.confirm('Start batch processing for all buckets? This may take considerable time and resources.')) {
      return
    }

    try {
      const result = await documentApi.batchProcessAll(processingOptions)
      
      let taskId = null
      let message = 'Batch processing started successfully'
      
      if (result?.status === 'success' && result?.data?.task_id) {
        taskId = result.data.task_id
        message = `Batch processing started! Task ID: ${taskId}`
      } else if (result?.success && result?.data?.task_id) {
        taskId = result.data.task_id
        message = `Batch processing started! Task ID: ${taskId}`
      } else if (result?.task_id) {
        taskId = result.task_id
        message = `Batch processing started! Task ID: ${taskId}`
      }
      
      alert(message)
    } catch (error) {
      console.error('Failed to start batch processing:', error)
      alert(`Failed to start batch processing: ${error.message}`)
    }
  }

  const processBucket = async (bucketName) => {
    if (!validateProcessingOptions()) return

    if (!window.confirm(`Process all documents in bucket "${bucketName}"?`)) {
      return
    }

    try {
      const bucketOptions = {
        ...processingOptions,
        maxDocuments: processingOptions.maxDocumentsPerBucket
      }

      const result = await documentApi.batchProcessBucket(bucketName, bucketOptions)

      let taskId = null
      let message = 'Bucket processing started successfully'

      if (result?.status === 'success' && result?.data?.task_id) {
        taskId = result.data.task_id
        message = `Processing started! Task ID: ${taskId}`
      } else if (result?.success && result?.data?.task_id) {
        taskId = result.data.task_id
        message = `Processing started! Task ID: ${taskId}`
      } else if (result?.task_id) {
        taskId = result.task_id
        message = `Processing started! Task ID: ${taskId}`
      }

      alert(message)
    } catch (error) {
      console.error('Failed to start bucket processing:', error)
      alert(`Failed to start bucket processing: ${error.message}`)
    }
  }


  const handleOptionChange = (option, value) => {
    setProcessingOptions(prev => ({
      ...prev,
      [option]: value
    }))
  }

  const validateProcessingOptions = () => {
    const { includeChunking, includeSummarization, includeGraphrag, includeStp } = processingOptions
    
    if (!includeChunking && !includeSummarization && !includeGraphrag && !includeStp) {
      alert('Please select at least one processing option')
      return false
    }
    
    return true
  }

  const getSelectedProcessingTypes = () => {
    const selected = []
    if (processingOptions.includeChunking) selected.push('Chunks')
    if (processingOptions.includeSummarization) selected.push('Summaries')
    if (processingOptions.includeGraphrag) selected.push('GraphRAG')
    if (processingOptions.includeStp) selected.push('STP')
    return selected
  }

  const getFilteredBuckets = () => {
    return buckets.filter(b => typeof b === 'string' ? true : b.is_processable !== false)
  }

  const formatNumber = (value) => {
    if (typeof value === 'number' && !isNaN(value)) {
      return value.toLocaleString()
    }
    return '0'
  }

  if (loading && buckets.length === 0) {
    return (
      <div className="batch-processing-tab">
        <div className="batch-loading">
          <LoadingSpinner size="large" text="Loading batch processing data..." />
        </div>
      </div>
    )
  }

  return (
    <div className="batch-processing-tab">
      {error && (
        <div className="batch-error">
          <AlertTriangle size={18} />
          <div>
            <strong>Error</strong>
            <p>{error}</p>
          </div>
          <button onClick={loadData} className="error-retry">
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      )}

      {/* Processing Options */}
      <div className="batch-section">
        <div className="section-header">
          <Settings size={18} />
          <h3>Processing Configuration</h3>
        </div>
        <div className="options-panel">
          <div className="options-grid">
            <label className="option-checkbox">
              <input
                type="checkbox"
                checked={processingOptions.skipProcessed}
                onChange={(e) => handleOptionChange('skipProcessed', e.target.checked)}
              />
              <span>Skip Already Processed</span>
            </label>
            
            <label className="option-checkbox">
              <input
                type="checkbox"
                checked={processingOptions.includeChunking}
                onChange={(e) => handleOptionChange('includeChunking', e.target.checked)}
              />
              <span>Generate Chunks</span>
            </label>
            
            <label className="option-checkbox">
              <input
                type="checkbox"
                checked={processingOptions.includeSummarization}
                onChange={(e) => handleOptionChange('includeSummarization', e.target.checked)}
              />
              <span>Generate Summaries</span>
            </label>
            
            <label className="option-checkbox">
              <input
                type="checkbox"
                checked={processingOptions.includeGraphrag}
                onChange={(e) => handleOptionChange('includeGraphrag', e.target.checked)}
              />
              <span>Generate GraphRAG</span>
            </label>
            
            {/* STP Processing Option */}
            <label className="option-checkbox">
              <input
                type="checkbox"
                checked={processingOptions.includeStp}
                onChange={(e) => handleOptionChange('includeStp', e.target.checked)}
              />
              <span>
                Process STP Classification
              </span>
            </label>
          </div>
          
          <div className="option-input">
            <label>Max Documents per Bucket:</label>
            <input
              type="number"
              min="1"
              max="1000"
              placeholder="All documents"
              value={processingOptions.maxDocumentsPerBucket || ''}
              onChange={(e) => handleOptionChange('maxDocumentsPerBucket', 
                e.target.value ? parseInt(e.target.value) : null
              )}
            />
          </div>
        </div>
      </div>

      {/* Batch Actions */}
      <div className="batch-section">
        <div className="section-header">
          <HardDrive size={18} />
          <h3>Batch Operations</h3>
        </div>
        
        <div className="batch-actions">
          {/* Process All Button */}
          <div className="batch-card primary">
            <div className="batch-card-header">
              <HardDrive size={16} />
              <h4>Process All Buckets</h4>
            </div>
            <div className="batch-card-content">
              <p>Execute processing across all available storage buckets with selected configuration.</p>
              <div className="batch-info">
                <span>Buckets: {getFilteredBuckets().length}</span>
                <span>Processing: {getSelectedProcessingTypes().join(', ') || 'None'}</span>
              </div>
            </div>
            <div className="batch-card-footer">
              <button
                onClick={processAllBuckets}
                className="batch-action-btn primary"
                disabled={
                  !processingOptions.includeChunking &&
                  !processingOptions.includeSummarization &&
                  !processingOptions.includeGraphrag &&
                  !processingOptions.includeStp
                }
              >
                <Play size={14} />
                Process All Buckets
              </button>
            </div>
          </div>
          
          {/* Individual Buckets */}
          {getFilteredBuckets().map((bucket, index) => {
            const bucketName = typeof bucket === 'string' ? bucket : bucket.bucket_name || bucket.name
            
            return (
              <div key={`${bucketName}-${index}`} className="batch-card">
                <div className="batch-card-header">
                  <Database size={16} />
                  <h4>{bucketName}</h4>
                </div>
                <div className="batch-card-content">
                  <p>Process documents in this bucket with selected configuration.</p>
                  <div className="batch-info">
                    <span>Processing: {getSelectedProcessingTypes().join(', ') || 'None'}</span>
                    <span>Limit: {processingOptions.maxDocumentsPerBucket || 'None'}</span>
                  </div>
                </div>
                <div className="batch-card-footer">
                  <button
                    onClick={() => processBucket(bucketName)}
                    className="batch-action-btn"
                    disabled={
                      !processingOptions.includeChunking &&
                      !processingOptions.includeSummarization &&
                      !processingOptions.includeGraphrag &&
                      !processingOptions.includeStp
                    }
                  >
                    <Play size={14} />
                    Process {bucketName}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default BatchProcessingTab