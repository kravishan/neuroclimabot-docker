import apiClient from './client'
import { API_CONFIG } from '@/constants/config'

// Dashboard API endpoints
export const dashboardApi = {
  // Get complete dashboard data
  async getDashboardData(limit = 10) {
    try {
      const response = await apiClient.get(`/api/v1/analytics/dashboard?limit=${limit}`)
      
      if (response.data && response.data.data) {
        return response.data.data
      } else {
        throw new Error('Invalid dashboard response format')
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      
      let errorMessage = 'Failed to load dashboard data'
      
      if (error.response) {
        const status = error.response.status
        const data = error.response.data
        
        if (status === 404) {
          errorMessage = 'Dashboard service not found'
        } else if (status === 500) {
          errorMessage = data?.detail || 'Dashboard server error'
        } else if (status === 422) {
          errorMessage = data?.detail || 'Invalid dashboard request parameters'
        } else if (status === 401) {
          errorMessage = 'Authentication required for dashboard access'
        } else {
          errorMessage = data?.detail || `Dashboard API error (${status})`
        }
      } else if (error.code === 'ECONNABORTED') {
        errorMessage = 'Dashboard API timeout'
      } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
        errorMessage = 'Cannot connect to dashboard server'
      }
      
      throw new Error(errorMessage)
    }
  },

  // Get system metrics
  async getSystemMetrics() {
    try {
      const response = await apiClient.get('/api/v1/analytics/system-metrics')
      return response.data
    } catch (error) {
      console.error('Error fetching system metrics:', error)
      throw error
    }
  },

  // Get trending topics
  async getTrendingTopics(limit = 10) {
    try {
      const response = await apiClient.get(`/api/v1/analytics/trending-topics?limit=${limit}`)
      return response.data
    } catch (error) {
      console.error('Error fetching trending topics:', error)
      throw error
    }
  },

  // Get popular queries
  async getPopularQueries(limit = 10) {
    try {
      const response = await apiClient.get(`/api/v1/analytics/popular-queries?limit=${limit}`)
      return response.data
    } catch (error) {
      console.error('Error fetching popular queries:', error)
      throw error
    }
  },

  // Get popular documents
  async getPopularDocuments(limit = 10) {
    try {
      const response = await apiClient.get(`/api/v1/analytics/popular-documents?limit=${limit}`)
      return response.data
    } catch (error) {
      console.error('Error fetching popular documents:', error)
      throw error
    }
  },

  // Get content analytics (source types, languages)
  async getContentAnalytics() {
    try {
      const response = await apiClient.get('/api/v1/analytics/content-stats')
      return response.data
    } catch (error) {
      console.error('Error fetching content analytics:', error)
      throw error
    }
  },

  // Health check for dashboard API
  async healthCheck() {
    try {
      const response = await apiClient.get('/api/v1/analytics/health')
      return response.data
    } catch (error) {
      console.error('Error checking dashboard health:', error)
      throw error
    }
  }
}

// Legacy compatibility - you can remove this if you update the config
export const DASHBOARD_CONFIG = {
  ENDPOINTS: {
    DASHBOARD: '/api/v1/analytics/dashboard',
    SYSTEM_METRICS: '/api/v1/analytics/system-metrics',
    TRENDING_TOPICS: '/api/v1/analytics/trending-topics',
    POPULAR_QUERIES: '/api/v1/analytics/popular-queries',
    POPULAR_DOCUMENTS: '/api/v1/analytics/popular-documents',
    CONTENT_ANALYTICS: '/api/v1/analytics/content-stats',
    HEALTH: '/api/v1/analytics/health'
  }
}