import React, { useState } from 'react'
import { 
  Database, 
  AlertTriangle, 
  RefreshCw,
  Filter,
  FileText
} from 'lucide-react'
import { adminApi } from '@/services/api/adminEndpoints'
import './LogsTab.css'

const LogsTab = ({ data, onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [levelFilter, setLevelFilter] = useState('all')

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await onRefresh()
    } finally {
      setLoading(false)
    }
  }

  const filteredLogs = data.logs ? data.logs.filter(log => {
    if (levelFilter === 'all') return true
    return (log.level || 'info').toLowerCase() === levelFilter.toLowerCase()
  }) : []

  return (
    <div className="adm-logs-tab">
      <section className="adm-dashboard-section">
        <h2>
          <Database size={20} />
          System Logs
          {data.totalLines && (
            <span style={{ fontSize: '14px', fontWeight: 'normal', marginLeft: '12px', color: '#999' }}>
              ({data.totalLines} total lines)
            </span>
          )}
        </h2>
        
        {data.error && (
          <div className="adm-dashboard-error">
            <AlertTriangle size={16} />
            <div className="adm-error-content">
              <strong>Logs Error</strong>
              <p>{data.error}</p>
            </div>
          </div>
        )}

        {/* Logs Controls */}
        <div className="adm-logs-controls">
          <div className="adm-logs-filter-group">
            <label>
            </label>
            <select 
              value={levelFilter} 
              onChange={(e) => setLevelFilter(e.target.value)}
              className="adm-logs-filter-select"
            >
              <option value="all">All Levels</option>
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          
          <button 
            onClick={handleRefresh} 
            className="adm-logs-refresh-btn"
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'adm-spinning' : ''} />
            Refresh Logs
          </button>
        </div>
        
        <div className="adm-logs-container">
          {filteredLogs.length > 0 ? (
            filteredLogs.slice(0, 100).map((log, i) => {
              const logLevel = (log.level || 'info').toLowerCase()
              const logTime = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Unknown time'
              const logMessage = log.message || log.raw_log || 'No message'
              
              return (
                <div key={i} className={`adm-log-entry adm-log-${logLevel}`}>
                  <div className="adm-log-time">{logTime}</div>
                  <div className={`adm-log-level adm-log-level-${logLevel}`}>
                    {(log.level || 'INFO').toUpperCase()}
                  </div>
                  <div className="adm-log-message">{logMessage}</div>
                </div>
              )
            })
          ) : data.logs && data.logs.length === 0 ? (
            <div className="adm-logs-empty">
              <FileText size={48} />
              <p>No log entries found</p>
              {levelFilter !== 'all' && (
                <small>Try changing the level filter to see more logs</small>
              )}
            </div>
          ) : (
            <div className="adm-log-entry">
              <div className="adm-log-time">No logs available</div>
              <div className="adm-log-level adm-log-level-info">INFO</div>
              <div className="adm-log-message">
                {data.error ? 'Failed to load system logs' : 'No log entries found'}
              </div>
            </div>
          )}
        </div>

        {data.logs && data.logs.length > 100 && (
          <div style={{ 
            padding: '12px', 
            textAlign: 'center', 
            color: 'var(--adm-secondary)', 
            fontSize: '12px',
            background: 'var(--adm-surface)',
            borderRadius: 'var(--adm-radius-sm)',
            marginTop: '12px'
          }}>
            Showing first 100 of {data.logs.length} log entries
          </div>
        )}
      </section>
    </div>
  )
}

export default LogsTab