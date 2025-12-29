import React, { useState, useEffect } from 'react'
import { 
  X, 
  FileText, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Loader,
  RefreshCw,
  Database,
  Hash,
  Network,
  Users,
  Calendar,
  Play,
  RotateCcw,
  Target,
  TrendingUp,
  BarChart2,
  Package
} from 'lucide-react'
import { documentApi } from '@/services/api/documentEndpoints'
import './DocumentDetailsModal.css'

const DocumentDetailsModal = ({ isOpen, onClose, document, onProcessDocument, processingDocuments }) => {
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (isOpen && document) {
      loadDocumentDetails()
    }
  }, [isOpen, document])

  const loadDocumentDetails = async () => {
    if (!document) return
    
    setLoading(true)
    setError(null)
    
    try {
      const docName = document.name || document.doc_name || document.filename
      const docBucket = document.bucket || document.bucket_source || 'unknown'
      
      const response = await documentApi.getDocumentStatus(docName, docBucket)
      
      // Extract data from API response
      let detailsData = response?.data || response || {}
      
      // Normalize boolean values from database (1/0 to true/false)
      const normalizedDetails = {
        ...document,
        ...detailsData,
        docName,
        docBucket,
        // Normalize chunks
        chunks_done: detailsData.chunks_done === 1 || detailsData.chunks_done === true,
        chunks_count: detailsData.chunks_count || 0,
        // Normalize summary
        summary_done: detailsData.summary_done === 1 || detailsData.summary_done === true,
        // Normalize GraphRAG
        graphrag_done: detailsData.graphrag_done === 1 || detailsData.graphrag_done === true,
        graphrag_entities_count: detailsData.graphrag_entities_count || 0,
        graphrag_relationships_count: detailsData.graphrag_relationships_count || 0,
        graphrag_communities_count: detailsData.graphrag_communities_count || 0,
        // Normalize STP
        stp_done: detailsData.stp_done === 1 || detailsData.stp_done === true,
        stp_chunks_count: detailsData.stp_chunks_count || 0,
        stp_stp_count: detailsData.stp_stp_count || 0,
        stp_non_stp_count: detailsData.stp_non_stp_count || 0,
        // Overall completion
        is_complete: (detailsData.chunks_done === 1 || detailsData.chunks_done === true) &&
                    (detailsData.summary_done === 1 || detailsData.summary_done === true) &&
                    (detailsData.graphrag_done === 1 || detailsData.graphrag_done === true) &&
                    (detailsData.stp_done === 1 || detailsData.stp_done === true)
      }
      
      setDetails(normalizedDetails)
    } catch (err) {
      console.error('Failed to load document details:', err)
      setError(err.message)
      // Still set basic details from document prop
      setDetails({
        ...document,
        docName: document.name || document.doc_name || document.filename,
        docBucket: document.bucket || document.bucket_source || 'unknown',
        chunks_done: document.chunks_done === 1 || document.chunks_done === true,
        summary_done: document.summary_done === 1 || document.summary_done === true,
        graphrag_done: document.graphrag_done === 1 || document.graphrag_done === true,
        stp_done: document.stp_done === 1 || document.stp_done === true
      })
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadDocumentDetails()
    setRefreshing(false)
  }

  const handleProcessDocument = async (processType) => {
    if (!details || !onProcessDocument) return
    
    await onProcessDocument(details.docBucket, details.docName, processType)
    // Refresh details after processing
    setTimeout(() => {
      loadDocumentDetails()
    }, 1000)
  }

  const getDocumentKey = () => {
    if (!details) return ''
    return `${details.docBucket}-${details.docName}`
  }

  const isProcessing = () => {
    const docKey = getDocumentKey()
    if (!docKey || !processingDocuments) return false
    
    return processingDocuments.has && processingDocuments.has(docKey)
  }

  const getStatusIcon = (done) => {
    if (done === true) {
      return <CheckCircle size={16} className="status-icon-complete" />
    } else if (done === false) {
      return <Clock size={16} className="status-icon-pending" />
    }
    return <AlertCircle size={16} className="status-icon-error" />
  }

  const getStatusText = (done) => {
    if (done === true) return 'Complete'
    if (done === false) return 'Pending'
    return 'Error'
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Not available'
    try {
      return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch (e) {
      return dateString
    }
  }

  const formatNumber = (value) => {
    if (typeof value === 'number' && !isNaN(value)) {
      return value.toLocaleString()
    }
    return '0'
  }

  const calculateStpPercentage = () => {
    if (!details || !details.chunks_count || details.chunks_count === 0) {
      return '0%'
    }
    const percentage = (details.stp_stp_count / details.chunks_count) * 100
    return `${percentage.toFixed(1)}%`
  }

  if (!isOpen) return null

  return (
    <div className="document-modal-overlay">
      <div className="document-modal">
        {/* Header */}
        <div className="document-modal-header">
          <div className="modal-title-section">
            <FileText size={20} />
            <h2>Document Details</h2>
          </div>
          <div className="modal-header-actions">
            <button 
              onClick={handleRefresh} 
              className="modal-header-btn"
              disabled={refreshing}
              title="Refresh"
            >
              <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
            </button>
            <button onClick={onClose} className="modal-header-btn close-btn">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="document-modal-content">
          {loading && !details ? (
            <div className="modal-loading">
              <Loader size={24} className="spinning" />
              <span>Loading document details...</span>
            </div>
          ) : (
            <>
              {error && (
                <div className="modal-error">
                  <AlertCircle size={16} />
                  <span>Error: {error}</span>
                </div>
              )}

              {details && (
                <div className="document-details">
                  {/* Document Information */}
                  <div className="details-section">
                    <h3>Document Information</h3>
                    <div className="details-grid">
                      <div className="detail-row">
                        <label>Name:</label>
                        <span className="detail-value" title={details.docName}>
                          {details.docName}
                        </span>
                      </div>
                      <div className="detail-row">
                        <label>Source Bucket:</label>
                        <span className="detail-value bucket-name">
                          {details.docBucket || details.bucket_source}
                        </span>
                      </div>
                      <div className="detail-row">
                        <label>Document ID:</label>
                        <span className="detail-value doc-id">#{details.id || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <label>Status:</label>
                        <span className={`detail-value status-badge ${details.is_complete ? 'complete' : 'incomplete'}`}>
                          {details.is_complete ? 'Complete' : 'Processing'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Processing Overview - Simple Status Display */}
                  <div className="details-section">
                    <h3>Processing Overview</h3>
                    <div className="processing-grid">
                      {/* Chunks Processing */}
                      <div className="processing-item">
                        <div className="processing-item-header">
                          <div className="processing-header">
                            {getStatusIcon(details.chunks_done)}
                            <span>Chunks Processing</span>
                          </div>
                          <button
                            className={`processing-action-btn ${details.chunks_done ? 'reprocess' : 'process'} ${isProcessing() ? 'processing' : ''}`}
                            onClick={() => handleProcessDocument('chunks')}
                            disabled={isProcessing()}
                            title={details.chunks_done ? 'Process chunks again' : 'Process chunks'}
                          >
                            {isProcessing() ? (
                              <Loader size={14} className="spinning" />
                            ) : details.chunks_done ? (
                              <RotateCcw size={14} />
                            ) : (
                              <Play size={14} />
                            )}
                            {details.chunks_done ? 'Process Again' : 'Process Chunks'}
                          </button>
                        </div>
                        <div className="processing-stats">
                          <span className="stat-value">{getStatusText(details.chunks_done)}</span>
                          <span className="stat-label">status</span>
                        </div>
                      </div>

                      {/* Summary Generation */}
                      <div className="processing-item">
                        <div className="processing-item-header">
                          <div className="processing-header">
                            {getStatusIcon(details.summary_done)}
                            <span>Summary Generation</span>
                          </div>
                          <button
                            className={`processing-action-btn ${details.summary_done ? 'reprocess' : 'process'} ${isProcessing() ? 'processing' : ''}`}
                            onClick={() => handleProcessDocument('summary')}
                            disabled={isProcessing()}
                            title={details.summary_done ? 'Generate summary again' : 'Generate summary'}
                          >
                            {isProcessing() ? (
                              <Loader size={14} className="spinning" />
                            ) : details.summary_done ? (
                              <RotateCcw size={14} />
                            ) : (
                              <Play size={14} />
                            )}
                            {details.summary_done ? 'Generate Again' : 'Generate Summary'}
                          </button>
                        </div>
                        <div className="processing-stats">
                          <span className="stat-value">{getStatusText(details.summary_done)}</span>
                          <span className="stat-label">status</span>
                        </div>
                      </div>

                      {/* GraphRAG Processing */}
                      <div className="processing-item">
                        <div className="processing-item-header">
                          <div className="processing-header">
                            {getStatusIcon(details.graphrag_done)}
                            <span>GraphRAG Processing</span>
                          </div>
                          <button
                            className={`processing-action-btn ${details.graphrag_done ? 'reprocess' : 'process'} ${isProcessing() ? 'processing' : ''}`}
                            onClick={() => handleProcessDocument('graphrag')}
                            disabled={isProcessing()}
                            title={details.graphrag_done ? 'Process GraphRAG again' : 'Process GraphRAG'}
                          >
                            {isProcessing() ? (
                              <Loader size={14} className="spinning" />
                            ) : details.graphrag_done ? (
                              <RotateCcw size={14} />
                            ) : (
                              <Play size={14} />
                            )}
                            {details.graphrag_done ? 'Process Again' : 'Process GraphRAG'}
                          </button>
                        </div>
                        <div className="processing-stats">
                          <span className="stat-value">{getStatusText(details.graphrag_done)}</span>
                          <span className="stat-label">status</span>
                        </div>
                      </div>

                      {/* STP Processing */}
                      <div className="processing-item">
                        <div className="processing-item-header">
                          <div className="processing-header">
                            {getStatusIcon(details.stp_done)}
                            <span>STP Classification</span>
                          </div>
                          <button
                            className={`processing-action-btn ${details.stp_done ? 'reprocess' : 'process'} ${isProcessing() ? 'processing' : ''}`}
                            onClick={() => handleProcessDocument('stp')}
                            disabled={isProcessing()}
                            title={details.stp_done ? 'Process STP again' : 'Process STP'}
                          >
                            {isProcessing() ? (
                              <Loader size={14} className="spinning" />
                            ) : details.stp_done ? (
                              <RotateCcw size={14} />
                            ) : (
                              <Play size={14} />
                            )}
                            {details.stp_done ? 'Process Again' : 'Process STP'}
                          </button>
                        </div>
                        <div className="processing-stats">
                          <span className="stat-value">{getStatusText(details.stp_done)}</span>
                          <span className="stat-label">status</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Chunks Statistics - Only show if chunks processing is complete */}
                  {details.chunks_done && details.chunks_count > 0 && (
                    <div className="details-section">
                      <h3>Chunks Processing Details</h3>
                      <div className="stats-grid">
                        <div className="stat-card">
                          <div className="stat-icon chunks-icon">
                            <Hash size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.chunks_count)}</div>
                            <div className="stat-description">Total Chunks Generated</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon" style={{ background: 'rgba(0, 155, 153, 0.1)', color: '#009b99' }}>
                            <CheckCircle size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">Complete</div>
                            <div className="stat-description">Processing Status</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* GraphRAG Statistics - Only show if processing is complete */}
                  {details.graphrag_done && (
                    <div className="details-section">
                      <h3>GraphRAG Statistics</h3>
                      <div className="stats-grid">
                        <div className="stat-card">
                          <div className="stat-icon entities-icon">
                            <Network size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.graphrag_entities_count)}</div>
                            <div className="stat-description">Entities Extracted</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon relationships-icon">
                            <Database size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.graphrag_relationships_count)}</div>
                            <div className="stat-description">Relationships Found</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon communities-icon">
                            <Users size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.graphrag_communities_count)}</div>
                            <div className="stat-description">Communities Detected</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon chunks-icon">
                            <Hash size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.chunks_count)}</div>
                            <div className="stat-description">Total Chunks</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* STP Statistics - Only show if STP processing is complete */}
                  {details.stp_done && details.stp_chunks_count !== undefined && (
                    <div className="details-section">
                      <h3>STP Classification Statistics</h3>
                      <div className="stats-grid">
                        <div className="stat-card">
                          <div className="stat-icon" style={{ background: 'rgba(249, 157, 28, 0.1)', color: '#f99d1c' }}>
                            <Target size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.stp_stp_count)}</div>
                            <div className="stat-description">STP Chunks Identified</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon" style={{ background: 'rgba(0, 174, 239, 0.1)', color: '#00aef0' }}>
                            <Package size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.stp_non_stp_count)}</div>
                            <div className="stat-description">Non-STP Chunks</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon" style={{ background: 'rgba(0, 155, 153, 0.1)', color: '#009b99' }}>
                            <TrendingUp size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{calculateStpPercentage()}</div>
                            <div className="stat-description">STP Classification Rate</div>
                          </div>
                        </div>

                        <div className="stat-card">
                          <div className="stat-icon" style={{ background: 'rgba(153, 102, 255, 0.1)', color: '#9966ff' }}>
                            <BarChart2 size={18} />
                          </div>
                          <div className="stat-info">
                            <div className="stat-number">{formatNumber(details.stp_chunks_count)}</div>
                            <div className="stat-description">Total STP Processed</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Timeline */}
                  <div className="details-section">
                    <h3>Timeline</h3>
                    <div className="timeline">
                      <div className="timeline-entry">
                        <Calendar size={14} />
                        <div className="timeline-info">
                          <span className="timeline-label">Created:</span>
                          <span className="timeline-date">{formatDate(details.created_at)}</span>
                        </div>
                      </div>
                      <div className="timeline-entry">
                        <Calendar size={14} />
                        <div className="timeline-info">
                          <span className="timeline-label">Last Updated:</span>
                          <span className="timeline-date">{formatDate(details.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default DocumentDetailsModal