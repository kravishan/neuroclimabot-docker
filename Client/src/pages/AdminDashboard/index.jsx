import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Database,
  FileText,
  Settings,
  BarChart3,
  Trash2,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Server,
  Home,
  Shield,
  Activity,
  Users,
  Info,
  Globe,
  Target
} from 'lucide-react'
import { adminApi } from '@/services/api/adminEndpoints'
import { processorApi } from '@/services/api/processorEndpoints'
import AdminLogin from '@/components/auth/AdminLogin'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import DocumentsTab from './DocumentsTab'
import BatchProcessingTab from './BatchProcessingTab'
import LogsTab from './LogsTab'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import './AdminDashboard.css'

const AdminDashboard = () => {
  const navigate = useNavigate()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState({
    health: { services: {}, status: 'unknown', details: {} },
    processorHealth: { services: {}, timestamp: null },
    webhookStatus: { enabled: false, timestamp: null },
    stats: {
      sessions: { active: 0, total: 0, avgDuration: 0 },
      performance: { avgResponseTime: 0, cacheHitRate: 0, systemUptime: 0 }
    },
    feedback: {
      totalFeedback: 0,
      positiveCount: 0,
      negativeCount: 0,
      satisfactionRate: 0
    },
    logs: { logs: [], totalLines: 0 }
  })
  const [actionLoading, setActionLoading] = useState({})

  useDocumentTitle('NeuroClima Bot Admin Dashboard')

  // Auth check on mount
  useEffect(() => {
    const adminAuth = localStorage.getItem('admin_authenticated')
    if (adminAuth === 'true') {
      setIsAuthenticated(true)
      loadData()
    }
  }, [])

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
    loadData()
  }

  const handleLogout = () => {
    localStorage.removeItem('admin_authenticated')
    setIsAuthenticated(false)
    navigate('/')
  }

  // Load only overview data initially (lazy loading)
  const loadData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Load only 5 specific endpoints on initial load (added feedback stats)
      const [healthResult, processorHealthResult, webhookStatusResult, statsResult, feedbackResult] = await Promise.allSettled([
        adminApi.getSystemHealth(),         // http://localhost:8000/api/v1/health/
        processorApi.getServicesHealth(),   // http://localhost:5000/services/health
        processorApi.getWebhookStatus(),    // http://localhost:5000/webhook/status
        adminApi.getSystemStats(),          // http://localhost:8000/api/v1/admin/stats
        adminApi.getFeedbackData()          // http://localhost:8000/api/v1/feedback/stats (ALL feedback, not filtered)
      ])

      // Debug logging for processor health
      console.log('[AdminDashboard] Processor health result:', processorHealthResult)
      if (processorHealthResult.status === 'fulfilled') {
        console.log('[AdminDashboard] Processor health value:', processorHealthResult.value)
      } else {
        console.error('[AdminDashboard] Processor health error:', processorHealthResult.reason)
      }

      const newData = {
        health: healthResult.status === 'fulfilled' ? healthResult.value :
          { success: false, services: {}, status: 'error', error: 'Failed to load health data', details: {} },

        processorHealth: processorHealthResult.status === 'fulfilled' ? processorHealthResult.value :
          { success: false, services: {}, timestamp: null, error: 'Failed to load processor health' },

        webhookStatus: webhookStatusResult.status === 'fulfilled' ? webhookStatusResult.value :
          { success: false, enabled: false, timestamp: null, error: 'Failed to load webhook status' },

        stats: statsResult.status === 'fulfilled' ? statsResult.value :
          { success: false, sessions: { active: 0, total: 0, avgDuration: 0 },
            performance: { avgResponseTime: 0, cacheHitRate: 0, systemUptime: 0 },
            error: 'Failed to load stats' },

        feedback: feedbackResult.status === 'fulfilled' ? feedbackResult.value :
          { success: false, totalFeedback: 0, positiveCount: 0, negativeCount: 0, satisfactionRate: 0,
            data: { start_conversation_stats: { up: 0, down: 0 }, continue_conversation_stats: { up: 0, down: 0 }, language_stats: {} },
            error: 'Failed to load feedback data' },

        logs: data.logs // Keep existing logs data
      }

      console.log('[AdminDashboard] Final processor health data:', newData.processorHealth)

      setData(newData)

      // Check if any critical services failed
      const criticalFailures = [
        !newData.health.success && 'Bot Health Check',
        !newData.processorHealth.success && 'Processor Health Check',
        !newData.stats.success && 'System Stats'
      ].filter(Boolean)

      if (criticalFailures.length > 0) {
        setError(`Some services failed to load: ${criticalFailures.join(', ')}`)
      }

    } catch (error) {
      console.error('Failed to load admin data:', error)
      setError('Failed to load admin dashboard data: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // Load logs data when logs tab is clicked
  const loadLogsData = async () => {
    try {
      const logsResult = await adminApi.getSystemLogs(100, null)
      setData(prev => ({
        ...prev,
        logs: logsResult.success ? logsResult :
          { success: false, logs: [], totalLines: 0, error: 'Failed to load logs' }
      }))
    } catch (error) {
      console.error('Failed to load logs:', error)
      setData(prev => ({
        ...prev,
        logs: { success: false, logs: [], totalLines: 0, error: error.message }
      }))
    }
  }

  const performAdminAction = async (action) => {
    const actionNames = {
      clearCache: 'Clear System Cache',
      cleanupSessions: 'Cleanup Expired Sessions',
      clearFeedback: 'Clear All Feedback Data',
      clearLogs: 'Clear System Logs'
    }

    const actionName = actionNames[action] || action

    if (!window.confirm(`Are you sure you want to ${actionName.toLowerCase()}? This action cannot be undone.`)) {
      return
    }

    setActionLoading(prev => ({ ...prev, [action]: true }))

    try {
      const result = await adminApi.performAdminAction(action)

      if (result.success) {
        alert(`${actionName} completed successfully`)
        // Reload data to reflect changes
        loadData()
      } else {
        alert(`${actionName} failed: ${result.message}`)
      }
    } catch (error) {
      console.error(`Admin action ${action} failed:`, error)
      alert(`${actionName} failed: ${error.message}`)
    } finally {
      setActionLoading(prev => ({ ...prev, [action]: false }))
    }
  }

  const toggleWebhook = async () => {
    setActionLoading(prev => ({ ...prev, webhookToggle: true }))

    try {
      const result = await processorApi.toggleWebhook()

      if (result.success) {
        // Update local state
        setData(prev => ({
          ...prev,
          webhookStatus: {
            enabled: result.enabled,
            timestamp: result.timestamp
          }
        }))
        alert(result.message || `Webhook ${result.enabled ? 'enabled' : 'disabled'} successfully`)
      } else {
        alert(`Failed to toggle webhook: ${result.message}`)
      }
    } catch (error) {
      console.error('Webhook toggle failed:', error)
      alert(`Failed to toggle webhook: ${error.message}`)
    } finally {
      setActionLoading(prev => ({ ...prev, webhookToggle: false }))
    }
  }

  // Handle tab change with lazy loading
  const handleTabChange = (tabId) => {
    setActiveTab(tabId)

    // Load data for specific tab if not loaded yet
    if (tabId === 'logs' && (!data.logs.logs || data.logs.logs.length === 0)) {
      loadLogsData()
    }
  }

  // Show login component if not authenticated
  if (!isAuthenticated) {
    return <AdminLogin onLoginSuccess={handleLoginSuccess} />
  }

  // Main dashboard
  return (
    <div className="adm-dashboard">
      <div className="adm-dashboard-container">
        <header className="adm-dashboard-header">
          <div className="adm-header-left">
            <img 
              src="/assets/icons/favicon.png" 
              alt="NeuroClima Bot" 
              className="adm-header-logo"
            />
            <h1>NeuroClima Bot Admin Dashboard</h1>
            {error && (
              <div className="adm-header-error">
                <AlertTriangle size={14} />
                {error}
              </div>
            )}
          </div>
          <div className="adm-header-actions">
            {/* Refresh Button */}
            <button 
              onClick={loadData} 
              className="adm-action-btn adm-header-btn" 
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'adm-spinning' : ''} />
              {loading ? 'Loading...' : 'Refresh'}
            </button>
            
            {/* Traces Button */}
            <button 
              onClick={() => window.open('http://195.148.23.57:3000/project/cmk53xvim0005mq07ah2nexkz', '_blank')} 
              className="adm-action-btn adm-home-btn adm-header-btn"
            >
              <BarChart3 size={16} />
              Traces
            </button>
            
            {/* Logout Button */}
            <button 
              onClick={handleLogout} 
              className="adm-action-btn adm-logout-btn adm-header-btn"
            >
              <Shield size={16} />
              Logout
            </button>
          </div>
        </header>

        <nav className="adm-dashboard-nav">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'documents', label: 'Documents', icon: FileText },
            { id: 'batch', label: 'Batch Processing', icon: Settings },
            { id: 'logs', label: 'System Logs', icon: Database }
          ].map(tab => (
            <button
              key={tab.id}
              className={`adm-nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </nav>

        <main className="adm-dashboard-content">
          {loading && activeTab === 'overview' && (
            <div className="adm-dashboard-loading">
              <LoadingSpinner size="large" text="Loading admin data..." />
            </div>
          )}
          
          {!loading && (
            <>
              {activeTab === 'overview' && (
                <OverviewTab
                  data={data}
                  performAction={performAdminAction}
                  actionLoading={actionLoading}
                  toggleWebhook={toggleWebhook}
                />
              )}
              {activeTab === 'documents' && (
                <DocumentsTab refreshData={loadData} />
              )}
              {activeTab === 'batch' && (
                <BatchProcessingTab />
              )}
              {activeTab === 'logs' && (
                <LogsTab data={data.logs} onRefresh={loadLogsData} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}

// Enhanced Overview Tab Component with Split Health Sections
const OverviewTab = ({ data, performAction, actionLoading, toggleWebhook }) => {
  // Helper function to get service display name for bot services
  const getBotServiceDisplayName = (serviceKey) => {
    const nameMap = {
      'rag': 'RAG Service',
      'milvus': 'Milvus',
      'minio': 'MinIO',
      'redis': 'Redis Cache',
      'database': 'Database'
    }
    return nameMap[serviceKey] || serviceKey.replace(/_/g, ' ').toUpperCase()
  }

  // Helper function to get service display name for processor services
  const getProcessorServiceDisplayName = (serviceKey) => {
    const nameMap = {
      'minio': 'MinIO',
      'milvus': 'Milvus',
      'tracker': 'Tracker',
      'embedder': 'Embedder',
      'batch_processor': 'Batch Processor',
      'processing_queue': 'Processing Queue',
      'graphrag_processor': 'GraphRAG Processor',
      'lancedb_storage': 'LanceDB Storage',
      'stp_processor': 'STP Processor'
    }
    return nameMap[serviceKey] || serviceKey.replace(/_/g, ' ').toUpperCase()
  }

  return (
    <div className="adm-tab-content">
      {/* System Health Bot */}
      <section className="adm-dashboard-section">
        <h2>
          <Server size={20} />
          System Health Bot
        </h2>
        <div className="adm-health-grid">
          {Object.entries(data.health.services || {}).map(([service, status]) => {
            const displayName = getBotServiceDisplayName(service)
            const isHealthy = status === 'healthy'
            const details = data.health.details?.[service]

            return (
              <div key={service} className="adm-health-item" title={details?.message || ''}>
                <div className={`adm-health-status ${isHealthy ? 'adm-success' : 'adm-danger'}`}>
                  {isHealthy ? '✅ Healthy' : '❌ Unhealthy'}
                </div>
                <div className="adm-health-label">{displayName}</div>
                {details?.message && (
                  <div style={{
                    fontSize: '0.7rem',
                    color: '#999',
                    marginTop: '4px',
                    textAlign: 'center'
                  }}>
                    {details.message}
                  </div>
                )}
              </div>
            )
          })}

          {/* Overall bot status */}
          <div className="adm-health-item">
            <div className={`adm-health-status ${data.health.status === 'healthy' ? 'adm-success' : 'adm-danger'}`}>
              {data.health.status === 'healthy' ? '✅ Online' : '❌ Issues'}
            </div>
            <div className="adm-health-label">OVERALL BOT STATUS</div>
          </div>
        </div>
      </section>

      {/* System Health Processor */}
      <section className="adm-dashboard-section">
        <h2>
          <Server size={20} />
          System Health Processor
        </h2>

        {/* Show error message if processor health check failed */}
        {!data.processorHealth.success && (
          <div className="adm-admin-warning" style={{ marginBottom: '16px' }}>
            <AlertTriangle size={16} />
            Failed to load processor health: {data.processorHealth.error}
          </div>
        )}

        <div className="adm-health-grid">
          {Object.entries(data.processorHealth.services || {}).length === 0 && data.processorHealth.success && (
            <div className="adm-health-item" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '20px' }}>
              <div style={{ color: '#999', fontSize: '0.9rem' }}>
                No processor services found
              </div>
            </div>
          )}

          {Object.entries(data.processorHealth.services || {}).map(([service, status]) => {
            const displayName = getProcessorServiceDisplayName(service)
            const isHealthy = status === 'healthy'

            return (
              <div key={service} className="adm-health-item">
                <div className={`adm-health-status ${isHealthy ? 'adm-success' : 'adm-danger'}`}>
                  {isHealthy ? '✅ Healthy' : '❌ Unhealthy'}
                </div>
                <div className="adm-health-label">{displayName}</div>
              </div>
            )
          })}

          {/* Webhook Status and Toggle */}
          <div className="adm-health-item">
            <div className={`adm-health-status ${data.webhookStatus.enabled ? 'adm-success' : 'adm-warning'}`}>
              {data.webhookStatus.enabled ? '✅ Enabled' : '⚠️ Disabled'}
            </div>
            <div className="adm-health-label">WEBHOOK STATUS</div>
            <button
              onClick={toggleWebhook}
              className={`adm-webhook-toggle-btn ${data.webhookStatus.enabled ? 'enabled' : 'disabled'}`}
              disabled={actionLoading.webhookToggle}
              style={{
                marginTop: '8px',
                padding: '4px 12px',
                fontSize: '0.75rem',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading.webhookToggle ? 'not-allowed' : 'pointer',
                backgroundColor: data.webhookStatus.enabled ? '#dc3545' : '#28a745',
                color: 'white',
                opacity: actionLoading.webhookToggle ? 0.6 : 1
              }}
            >
              {actionLoading.webhookToggle ? (
                <RefreshCw size={12} className="adm-spinning" style={{ marginRight: '4px' }} />
              ) : null}
              {data.webhookStatus.enabled ? 'Disable' : 'Enable'}
            </button>
          </div>
        </div>
      </section>

      {/* Session Statistics */}
      <section className="adm-dashboard-section">
        <h2>
          <Activity size={20} />
          Session Statistics
        </h2>
        <div className="adm-stats-grid">
          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <Users size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{data.stats.sessions?.active || 0}</div>
              <div className="adm-stat-label">Active Sessions</div>
            </div>
          </div>

          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <Target size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{data.stats.sessions?.total || 0}</div>
              <div className="adm-stat-label">Total Sessions</div>
            </div>
          </div>

          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <Globe size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{(data.stats.performance?.avgResponseTime || 0).toFixed(2)}s</div>
              <div className="adm-stat-label">Avg Response Time</div>
            </div>
          </div>
        </div>
      </section>

      {/* Feedback Statistics */}
      <section className="adm-dashboard-section">
        <h2>
          <ThumbsUp size={20} />
          Feedback Statistics
        </h2>
        <div className="adm-stats-grid">
          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <Info size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{data.feedback.totalFeedback || 0}</div>
              <div className="adm-stat-label">Total Feedback</div>
            </div>
          </div>

          <div className="adm-stat-card">
            <div className="adm-stat-icon adm-success-icon">
              <ThumbsUp size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{data.feedback.positiveCount || 0}</div>
              <div className="adm-stat-label">Thumbs Up</div>
            </div>
          </div>

          <div className="adm-stat-card">
            <div className="adm-stat-icon adm-danger-icon">
              <ThumbsDown size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{data.feedback.negativeCount || 0}</div>
              <div className="adm-stat-label">Thumbs Down</div>
            </div>
          </div>

          <div className="adm-stat-card">
            <div className="adm-stat-icon">
              <BarChart3 size={20} />
            </div>
            <div className="adm-stat-content">
              <div className="adm-stat-value">{(data.feedback.satisfactionRate || 0).toFixed(1)}%</div>
              <div className="adm-stat-label">Satisfaction Rate</div>
            </div>
          </div>
        </div>

        {/* Conversation Type Breakdown */}
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ fontSize: '0.95rem', marginBottom: '12px', color: '#e0e0e0' }}>
            Feedback by Conversation Type
          </h3>
          <div className="adm-stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <div className="adm-stat-card">
              <div className="adm-stat-content">
                <div className="adm-stat-label" style={{ marginBottom: '8px' }}>Start Conversation</div>
                <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                  <div>
                    <div className="adm-stat-value" style={{ fontSize: '1.2rem', color: '#4caf50' }}>
                      {data.feedback.data?.start_conversation_stats?.up || 0}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#999' }}>Up</div>
                  </div>
                  <div>
                    <div className="adm-stat-value" style={{ fontSize: '1.2rem', color: '#f44336' }}>
                      {data.feedback.data?.start_conversation_stats?.down || 0}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#999' }}>Down</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="adm-stat-card">
              <div className="adm-stat-content">
                <div className="adm-stat-label" style={{ marginBottom: '8px' }}>Continue Conversation</div>
                <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                  <div>
                    <div className="adm-stat-value" style={{ fontSize: '1.2rem', color: '#4caf50' }}>
                      {data.feedback.data?.continue_conversation_stats?.up || 0}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#999' }}>Up</div>
                  </div>
                  <div>
                    <div className="adm-stat-value" style={{ fontSize: '1.2rem', color: '#f44336' }}>
                      {data.feedback.data?.continue_conversation_stats?.down || 0}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#999' }}>Down</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Language Stats */}
        {data.feedback.data?.language_stats && Object.keys(data.feedback.data.language_stats).length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ fontSize: '0.95rem', marginBottom: '12px', color: '#e0e0e0' }}>
              Feedback by Language
            </h3>
            <div className="adm-stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
              {Object.entries(data.feedback.data.language_stats).map(([lang, stats]) => (
                <div key={lang} className="adm-stat-card">
                  <div className="adm-stat-content">
                    <div className="adm-stat-label" style={{ marginBottom: '8px' }}>
                      {lang.toUpperCase()}
                    </div>
                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                      <div>
                        <div className="adm-stat-value" style={{ fontSize: '1.1rem', color: '#4caf50' }}>
                          {stats.up || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#999' }}>Up</div>
                      </div>
                      <div>
                        <div className="adm-stat-value" style={{ fontSize: '1.1rem', color: '#f44336' }}>
                          {stats.down || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#999' }}>Down</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Administrative Actions */}
      <section className="adm-dashboard-section">
        <h2>
          <AlertTriangle size={20} />
          Administrative Actions
        </h2>
        <div className="adm-admin-warning">
          <AlertTriangle size={16} />
          Warning: These actions are permanent and cannot be undone!
        </div>
        <div className="adm-admin-grid">
          <button 
            onClick={() => performAction('clearCache')} 
            className="adm-admin-btn adm-warning"
            disabled={actionLoading.clearCache}
          >
            {actionLoading.clearCache ? (
              <RefreshCw size={16} className="adm-spinning" />
            ) : (
              <Trash2 size={16} />
            )}
            Clear Cache
          </button>
          
          <button 
            onClick={() => performAction('cleanupSessions')} 
            className="adm-admin-btn adm-info"
            disabled={actionLoading.cleanupSessions}
          >
            {actionLoading.cleanupSessions ? (
              <RefreshCw size={16} className="adm-spinning" />
            ) : (
              <RefreshCw size={16} />
            )}
            Cleanup Sessions
          </button>
          
          <button 
            onClick={() => performAction('clearFeedback')} 
            className="adm-admin-btn adm-danger"
            disabled={actionLoading.clearFeedback}
          >
            {actionLoading.clearFeedback ? (
              <RefreshCw size={16} className="adm-spinning" />
            ) : (
              <Trash2 size={16} />
            )}
            Clear Feedback
          </button>
          
          <button 
            onClick={() => performAction('clearLogs')} 
            className="adm-admin-btn adm-danger"
            disabled={actionLoading.clearLogs}
          >
            {actionLoading.clearLogs ? (
              <RefreshCw size={16} className="adm-spinning" />
            ) : (
              <Trash2 size={16} />
            )}
            Clear Logs
          </button>
        </div>
      </section>
    </div>
  )
}

export default AdminDashboard