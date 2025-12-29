import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { TrendingUp, AlertCircle, RefreshCw } from 'lucide-react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { dashboardApi } from '@/services/api/dashboardEndpoints'
import PopularContent from '@/components/dashboard/PopularContent'
import TrendingKeywords from '@/components/dashboard/TrendingKeywords'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import './DashboardPage.css'

const DashboardPage = () => {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useDocumentTitle('NeuroClima Bot Dashboard')

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true)
      setError(null)

      const result = await dashboardApi.getDashboardData()
      setData(result)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(() => loadData(true), 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !data) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-loading">
          <LoadingSpinner size="large" text="Loading Dashboard..." />
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-container">
        {error && (
          <div className="dashboard-error">
            <AlertCircle size={20} />
            <div className="error-content">
              <strong>Dashboard Error</strong>
              <p>{error}</p>
            </div>
            <button onClick={() => loadData()} className="error-retry-btn">
              <RefreshCw size={14} />
              Retry
            </button>
          </div>
        )}

        {/* Stats Overview */}
        {data?.stats && (
          <section className="user-dashboard-section">
            <div className="user-section-header">
              <TrendingUp size={20} />
              <span>Today's Overview</span>
            </div>
            <div className="chart-grid single-chart">
              <div className="chart-card">
                <div className="stats-grid-inner">
                  <div className="stat-card">
                    <div className="stat-value">{data.stats.total_queries || 0}</div>
                    <div className="stat-label">Total Queries</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{data.stats.unique_users || 0}</div>
                    <div className="stat-label">Unique Sessions</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{data.stats.total_documents || 0}</div>
                    <div className="stat-label">Documents Used</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{data.stats.total_topics || 0}</div>
                    <div className="stat-label">Topics Tracked</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{data.stats.avg_response_time ? `${data.stats.avg_response_time}s` : '0s'}</div>
                    <div className="stat-label">Avg Response Time</div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        <section className="user-dashboard-section">
          <div className="user-section-header">
            <TrendingUp size={20} />
            <span>Popular Content</span>
          </div>
          <PopularContent
            queries={data?.popular_queries}
            documents={data?.popular_documents}
            isLoading={loading}
          />
        </section>

        <section className="user-dashboard-section">
          <div className="user-section-header">
            <TrendingUp size={20} />
            <span>Trending Keywords</span>
          </div>
          <TrendingKeywords
            topics={data?.trending_topics}
            isLoading={loading}
          />
        </section>
      </div>
    </div>
  )
}

export default DashboardPage
