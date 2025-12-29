import React, { useState, useEffect } from 'react'
import {
  FileText,
  Eye,
  Play,
  RefreshCw,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader,
  Target
} from 'lucide-react'
import { documentApi } from '@/services/api/documentEndpoints'
import { DOCUMENT_CONFIG } from '@/constants/config'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import DocumentDetailsModal from './DocumentDetailsModal'
import './DocumentsTab.css'

const DocumentsTab = ({ refreshData }) => {
  const [loading, setLoading] = useState(false)
  const [selectedBucket, setSelectedBucket] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [documents, setDocuments] = useState([])
  const [buckets, setBuckets] = useState([])
  const [currentPage, setCurrentPage] = useState(1)
  const [documentsPerPage] = useState(DOCUMENT_CONFIG.DOCUMENTS_PER_PAGE)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    partial: 0
  })
  const [processingDocuments, setProcessingDocuments] = useState(new Set())

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState(null)

  useEffect(() => {
    loadDocumentData()
  }, [])

  const loadDocumentData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const docsResponse = await documentApi.getAllDocuments()
      let extractedDocs = []
      
      if (docsResponse?.success && docsResponse?.data?.documents) {
        extractedDocs = docsResponse.data.documents
      } else if (docsResponse?.data?.documents) {
        extractedDocs = docsResponse.data.documents
      } else if (docsResponse?.documents) {
        extractedDocs = docsResponse.documents
      } else if (Array.isArray(docsResponse)) {
        extractedDocs = docsResponse
      }
      
      setDocuments(Array.isArray(extractedDocs) ? extractedDocs : [])
      calculateStats(extractedDocs)
      await loadBuckets()
      
    } catch (error) {
      console.error('Failed to load document data:', error)
      setError('Failed to load document data: ' + error.message)
      setDocuments([])
      setBuckets([])
    } finally {
      setLoading(false)
    }
  }

  const loadBuckets = async () => {
    try {
      const bucketsResponse = await documentApi.listBuckets()
      let extractedBuckets = []
      
      if (bucketsResponse?.success && bucketsResponse?.data) {
        extractedBuckets = bucketsResponse.data.processable_buckets || 
                          bucketsResponse.data.all_buckets || []
      } else if (bucketsResponse?.data) {
        extractedBuckets = bucketsResponse.data.processable_buckets || 
                          bucketsResponse.data.all_buckets || []
      } else if (Array.isArray(bucketsResponse)) {
        extractedBuckets = bucketsResponse
      }
      
      const processableBuckets = extractedBuckets.filter(bucket => {
        const bucketName = typeof bucket === 'string' ? bucket : bucket.bucket_name || bucket.name
        return bucketName && !['metadata', 'stp'].includes(bucketName.toLowerCase())
      })
      
      setBuckets(processableBuckets)
    } catch (error) {
      console.error('Failed to load buckets:', error)
      setBuckets([])
    }
  }

  const calculateStats = (docs) => {
    const stats = {
      total: docs.length,
      completed: 0,
      partial: 0
    }

    docs.forEach(doc => {
      // Normalize boolean values from database (1/0 or true/false)
      const hasChunks = doc.chunks_done === 1 || doc.chunks_done === true
      const hasSummary = doc.summary_done === 1 || doc.summary_done === true
      const hasGraphRAG = doc.graphrag_done === 1 || doc.graphrag_done === true
      const hasStp = doc.stp_done === 1 || doc.stp_done === true

      const isComplete = hasChunks && hasSummary && hasGraphRAG && hasStp
      const hasAnyProcessing = hasChunks || hasSummary || hasGraphRAG || hasStp

      if (isComplete) {
        stats.completed++
      } else if (hasAnyProcessing) {
        stats.partial++
      }
    })

    setStats(stats)
  }

  const processDocument = async (bucket, filename, processType = 'all') => {
    const docKey = `${bucket}-${filename}`
    
    if (processingDocuments.has(docKey)) {
      return
    }

    setProcessingDocuments(prev => new Set([...prev, docKey]))

    try {
      let result
      const options = {
        includeChunking: true,
        includeSummarization: true,
        includeGraphrag: true,
        includeStp: false
      }

      switch (processType) {
        case 'chunks':
          options.includeSummarization = false
          options.includeGraphrag = false
          options.includeStp = false
          result = await documentApi.processChunksOnly(bucket, filename)
          break
        case 'summary':
          options.includeChunking = false
          options.includeGraphrag = false
          options.includeStp = false
          result = await documentApi.processSummaryOnly(bucket, filename)
          break
        case 'graphrag':
          options.includeChunking = false
          options.includeSummarization = false
          options.includeStp = false
          result = await documentApi.processGraphRAGOnly(bucket, filename)
          break
        case 'stp':
          options.includeChunking = false
          options.includeSummarization = false
          options.includeGraphrag = false
          options.includeStp = true
          result = await documentApi.processStpOnly(bucket, filename)
          break
        default:
          result = await documentApi.processDocumentEnhanced(bucket, filename, options)
      }
      
      let taskId = null
      if (result?.success && result?.data?.task_id) {
        taskId = result.data.task_id
      } else if (result?.task_id) {
        taskId = result.task_id
      }
      
      if (taskId) {
        console.log(`Processing started! Task ID: ${taskId}`)
      }
    } catch (error) {
      console.error('Failed to process document:', error)
    } finally {
      setProcessingDocuments(prev => {
        const newSet = new Set(prev)
        newSet.delete(docKey)
        return newSet
      })
    }
  }

  const getStatusBadge = (doc) => {
    // Normalize boolean values from database
    const hasChunks = doc.chunks_done === 1 || doc.chunks_done === true
    const hasSummary = doc.summary_done === 1 || doc.summary_done === true
    const hasGraphRAG = doc.graphrag_done === 1 || doc.graphrag_done === true
    const hasStp = doc.stp_done === 1 || doc.stp_done === true
    
    const isComplete = hasChunks && hasSummary && hasGraphRAG && hasStp
    const hasAnyProcessing = hasChunks || hasSummary || hasGraphRAG || hasStp
    
    if (isComplete) {
      return <span className="adm-status-badge adm-complete">Complete</span>
    } else if (hasAnyProcessing) {
      return <span className="adm-status-badge adm-partial">Partial</span>
    } else {
      return <span className="adm-status-badge adm-pending">Pending</span>
    }
  }

  const handleViewDetails = (document) => {
    setSelectedDocument(document)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedDocument(null)
  }

  // Filter documents
  const filteredDocuments = documents.filter(doc => {
    const docName = doc.name || doc.doc_name || doc.filename || ''
    const docBucket = doc.bucket || doc.bucket_source || ''
    
    const matchesBucket = selectedBucket === 'all' || docBucket === selectedBucket
    const matchesSearch = !searchQuery || docName.toLowerCase().includes(searchQuery.toLowerCase())
    
    return matchesBucket && matchesSearch
  })

  // Pagination
  const indexOfLastDoc = currentPage * documentsPerPage
  const indexOfFirstDoc = indexOfLastDoc - documentsPerPage
  const currentDocs = filteredDocuments.slice(indexOfFirstDoc, indexOfLastDoc)
  const totalPages = Math.ceil(filteredDocuments.length / documentsPerPage)

  const handlePageChange = (newPage) => {
    setCurrentPage(Math.max(1, Math.min(totalPages, newPage)))
  }

  if (loading && documents.length === 0) {
    return (
      <div className="adm-documents-tab">
        <div className="adm-dashboard-loading">
          <LoadingSpinner size="large" text="Loading documents..." />
        </div>
      </div>
    )
  }

  return (
    <div className="adm-documents-tab">
      {error && (
        <div className="adm-error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
          <button onClick={loadDocumentData} className="adm-retry-btn">
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      )}

      {/* Statistics Cards */}
      <div className="adm-stats-section">
        <div className="adm-stats-grid">
          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <FileText size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{stats.total}</div>
              <div className="adm-stat-label">Total Documents</div>
            </div>
          </div>
          <div className="adm-stat-card">
            <div className="adm-stat-icon adm-success">
              <CheckCircle size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{stats.completed}</div>
              <div className="adm-stat-label">Completed</div>
            </div>
          </div>
          <div className="adm-stat-card">
            <div className="adm-stat-icon adm-warning">
              <Clock size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{stats.partial}</div>
              <div className="adm-stat-label">Partial</div>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="adm-controls-section">
        <div className="adm-control-group">
          <label>
            <Filter size={16} />
            Bucket Filter
          </label>
          <select 
            value={selectedBucket} 
            onChange={(e) => setSelectedBucket(e.target.value)}
            className="adm-select-input"
          >
            <option value="all">All Buckets ({buckets.length})</option>
            {buckets.map((bucket, index) => {
              const bucketName = typeof bucket === 'string' ? bucket : 
                               bucket.bucket_name || bucket.name || `Bucket ${index + 1}`
              return (
                <option key={bucketName} value={bucketName}>{bucketName}</option>
              )
            })}
          </select>
        </div>
        
        <div className="adm-control-group">
          <label>
            <Search size={16} />
            Search Documents
          </label>
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="adm-text-input"
          />
        </div>
        
        <button 
          onClick={loadDocumentData} 
          className="adm-refresh-btn"
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Documents Table */}
      <div className="adm-table-container">
        <table className="adm-documents-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Bucket</th>
              <th>Chunks</th>
              <th>Summary</th>
              <th>GraphRAG</th>
              <th>STP</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {currentDocs.length > 0 ? (
              currentDocs.map((doc, i) => {
                const docName = doc.name || doc.doc_name || doc.filename || `Document ${i + 1}`
                const docBucket = doc.bucket || doc.bucket_source || 'unknown'
                const docKey = `${docBucket}-${docName}`
                
                // Normalize boolean values from database (1/0 or true/false)
                const hasChunks = doc.chunks_done === 1 || doc.chunks_done === true
                const hasSummary = doc.summary_done === 1 || doc.summary_done === true
                const hasGraphRAG = doc.graphrag_done === 1 || doc.graphrag_done === true
                const hasStp = doc.stp_done === 1 || doc.stp_done === true
                
                return (
                  <tr key={docKey}>
                    <td className="adm-document-cell">
                      <div className="adm-document-name" title={docName}>
                        {docName.length > 50 ? docName.substring(0, 50) + '...' : docName}
                      </div>
                    </td>
                    <td>
                      <span className="adm-bucket-badge">{docBucket}</span>
                    </td>
                    <td>
                      <div className={`adm-status-indicator ${hasChunks ? 'adm-complete' : 'adm-pending'}`}>
                        {hasChunks ? <CheckCircle size={16} /> : <Clock size={16} />}
                      </div>
                    </td>
                    <td>
                      <div className={`adm-status-indicator ${hasSummary ? 'adm-complete' : 'adm-pending'}`}>
                        {hasSummary ? <CheckCircle size={16} /> : <Clock size={16} />}
                      </div>
                    </td>
                    <td>
                      <div className={`adm-status-indicator ${hasGraphRAG ? 'adm-complete' : 'adm-pending'}`}>
                        {hasGraphRAG ? <CheckCircle size={16} /> : <Clock size={16} />}
                      </div>
                    </td>
                    <td>
                      <div className={`adm-status-indicator ${hasStp ? 'adm-complete' : 'adm-pending'}`}>
                        {hasStp ? <Target size={16} /> : <Clock size={16} />}
                      </div>
                    </td>
                    <td>{getStatusBadge(doc)}</td>
                    <td>
                      <div className="adm-action-buttons">
                        <button 
                          className="adm-action-btn adm-view-btn" 
                          title="View Details"
                          onClick={() => handleViewDetails(doc)}
                        >
                          <Eye size={14} />
                        </button>
                        <button 
                          className={`adm-action-btn adm-process-btn ${processingDocuments.has(docKey) ? 'adm-processing' : ''}`}
                          title="Process Document"
                          onClick={() => processDocument(docBucket, docName, 'all')}
                          disabled={processingDocuments.has(docKey)}
                        >
                          {processingDocuments.has(docKey) ? (
                            <Loader size={14} className="animate-spin" />
                          ) : (
                            <Play size={14} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan="8" className="adm-empty-state">
                  {loading ? (
                    <LoadingSpinner size="small" text="Loading documents..." />
                  ) : filteredDocuments.length === 0 && documents.length > 0 ? (
                    'No documents match your filters'
                  ) : (
                    'No documents found'
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="adm-pagination">
          <button 
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="adm-pagination-btn"
          >
            <ChevronLeft size={16} />
            Previous
          </button>
          <div className="adm-pagination-info">
            <span className="adm-page-numbers">
              Page {currentPage} of {totalPages}
            </span>
            <span className="adm-total-count">
              Showing {indexOfFirstDoc + 1}-{Math.min(indexOfLastDoc, filteredDocuments.length)} of {filteredDocuments.length}
            </span>
          </div>
          <button 
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="adm-pagination-btn"
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Document Details Modal */}
      <DocumentDetailsModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        document={selectedDocument}
        onProcessDocument={processDocument}
        processingDocuments={processingDocuments}
      />
    </div>
  )
}

export default DocumentsTab