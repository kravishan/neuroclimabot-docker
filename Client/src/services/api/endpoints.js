import apiClient from './client'
import { API_CONFIG, SESSION_CONFIG } from '@/constants/config'

// Session Management
export const startConversationSession = async (query, language = 'en', difficulty = 'low', retryCount = 0) => {
  try {
    // Clear any existing session before starting new one
    sessionStorage.removeItem(SESSION_CONFIG.STORAGE_KEY)

    const response = await apiClient.post(API_CONFIG.ENDPOINTS.CHAT_START, {
      message: query,
      language,
      difficulty_level: difficulty,
      include_sources: true
    })

    const data = response.data
    
    if (data.session_id) {
      sessionStorage.setItem(SESSION_CONFIG.STORAGE_KEY, data.session_id)
    }
    
    // Determine source type and handle accordingly
    const sourceType = data.source_type || 'rag' // Default to 'rag' if not specified
    const isWebSearch = sourceType === 'web'
    
    // Parse social tipping point - handle both old and new formats
    let socialTippingPoint = ''
    let qualifyingFactors = []
    
    if (data.social_tipping_point) {
      if (typeof data.social_tipping_point === 'string') {
        // Old format - just a string
        socialTippingPoint = data.social_tipping_point
      } else if (typeof data.social_tipping_point === 'object') {
        // New format - object with text and qualifying_factors
        socialTippingPoint = data.social_tipping_point.text || ''
        qualifyingFactors = data.social_tipping_point.qualifying_factors || []
      }
    } else {
      socialTippingPoint = isWebSearch ? '' : 'No specific social tipping point available.'
    }
    
    return {
      success: data.success !== false,
      session_id: data.session_id,
      sourceType: sourceType,
      isWebSearch: isWebSearch,
      usesRag: data.uses_rag !== undefined ? data.uses_rag : true,
      response: {
        title: data.title || 'Climate Information',
        content: data.response || data.message || '',
        socialTippingPoint: socialTippingPoint,
        qualifyingFactors: qualifyingFactors,
      },
      references: (data.sources || []).map(source => ({
        title: source.title || 'Unknown Document',
        doc_name: source.doc_name || source.original_title || source.title || 'Unknown',
        url: source.url || '#',
        similarity_score: source.similarity_score || 0
      })),
      referenceCount: data.sources ? data.sources.length : 0,
      totalAvailable: data.total_references || 0,
      queryPreprocessed: data.specialized_processing?.query_preprocessed || false,
      originalQuery: query,
      processedQuery: data.specialized_processing?.processed_query || null,
      preprocessingDetails: data.specialized_processing || {},
      processingTime: data.processing_time || 0,
      searchResultsSummary: {
        conversation_type: data.conversation_type || 'start',
        message_count: data.message_count || 1,
        source_type: sourceType
      }
    }
  } catch (error) {
    if (retryCount < 2 && (!error.response || error.code === 'ECONNABORTED')) {
      console.log(`Retrying start conversation request (${retryCount + 1}/2)...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      return startConversationSession(query, language, difficulty, retryCount + 1)
    }
    throw error
  }
}

export const continueConversationSession = async (sessionId, message, language = null, difficulty = null, retryCount = 0) => {
  try {
    if (!sessionId) {
      sessionId = sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)
    }

    if (!sessionId) {
      throw new Error('No session ID available. Please start a new conversation.')
    }

    const requestBody = {
      message,
      include_sources: true
    }

    if (language) requestBody.language = language
    if (difficulty) requestBody.difficulty_level = difficulty

    // Use the continue endpoint with session_id in URL
    const response = await apiClient.post(`${API_CONFIG.ENDPOINTS.CHAT_CONTINUE}/${sessionId}`, requestBody)
    
    const data = response.data
    
    // Determine source type and handle accordingly
    const sourceType = data.source_type || 'rag' // Default to 'rag' if not specified
    const isWebSearch = sourceType === 'web'
    
    // Parse social tipping point - handle both old and new formats
    let socialTippingPoint = ''
    let qualifyingFactors = []
    
    if (data.social_tipping_point) {
      if (typeof data.social_tipping_point === 'string') {
        // Old format - just a string
        socialTippingPoint = data.social_tipping_point
      } else if (typeof data.social_tipping_point === 'object') {
        // New format - object with text and qualifying_factors
        socialTippingPoint = data.social_tipping_point.text || ''
        qualifyingFactors = data.social_tipping_point.qualifying_factors || []
      }
    } else {
      socialTippingPoint = isWebSearch ? '' : 'No specific social tipping point available.'
    }
    
    return {
      success: data.success !== false,
      session_id: data.session_id || sessionId,
      sourceType: sourceType,
      isWebSearch: isWebSearch,
      usesRag: data.uses_rag !== undefined ? data.uses_rag : true,
      response: {
        title: data.title || 'Climate Discussion Continues',
        content: data.response || data.message || '',
        socialTippingPoint: socialTippingPoint,
        qualifyingFactors: qualifyingFactors,
      },
      references: (data.sources || []).map(source => ({
        title: source.title || 'Unknown Document',
        doc_name: source.doc_name || source.original_title || source.title || 'Unknown',
        url: source.url || '#',
        similarity_score: source.similarity_score || 0
      })),
      referenceCount: data.sources ? data.sources.length : 0,
      totalAvailable: data.total_references || 0,
      queryPreprocessed: data.specialized_processing?.query_preprocessed || false,
      originalQuery: message,
      processedQuery: data.specialized_processing?.processed_query || null,
      preprocessingDetails: data.specialized_processing || {},
      processingTime: data.processing_time || 0,
      searchResultsSummary: {
        conversation_type: data.conversation_type || 'continue',
        message_count: data.message_count || 1,
        source_type: sourceType
      },
      memoryContextUsed: data.specialized_processing?.context_used ? true : false
    }
  } catch (error) {
    if (retryCount < 2 && (!error.response || error.code === 'ECONNABORTED')) {
      console.log(`Retrying continue conversation request (${retryCount + 1}/2)...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      return continueConversationSession(sessionId, message, language, difficulty, retryCount + 1)
    }
    throw error
  }
}

export const endConversationSession = async (sessionId = null, retryCount = 0) => {
  try {
    if (!sessionId) {
      sessionId = sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)
    }

    if (!sessionId) {
      console.warn('No session ID to end')
      return { success: true, message: 'No active session to end' }
    }

    const response = await apiClient.delete(`${API_CONFIG.ENDPOINTS.SESSIONS}/${sessionId}`)
    
    sessionStorage.removeItem(SESSION_CONFIG.STORAGE_KEY)
    
    return response.data
  } catch (error) {
    if (retryCount < 1 && (!error.response || error.code === 'ECONNABORTED')) {
      console.log(`Retrying end session request (${retryCount + 1}/1)...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      return endConversationSession(sessionId, retryCount + 1)
    }
    throw error
  }
}

// Feedback
export const sendResponseFeedback = async (responseId, feedbackType, userId = 'anonymous', comment = '', conversationType = 'unknown', language = 'en', retryCount = 0) => {
  try {
    const sessionId = sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)

    const response = await apiClient.post(API_CONFIG.ENDPOINTS.FEEDBACK, {
      response_id: responseId,
      feedback: feedbackType,  // "up" or "down"
      session_id: sessionId || null,
      response_language: language,
      conversation_type: conversationType || 'unknown'
    })

    return response.data
  } catch (error) {
    if (retryCount < 2 && (!error.response || error.code === 'ECONNABORTED')) {
      console.log(`Retrying feedback submission (${retryCount + 1}/2)...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      return sendResponseFeedback(responseId, feedbackType, userId, comment, conversationType, language, retryCount + 1)
    }
    throw error
  }
}

// Enhanced Graph Visualization with new backend integration
export const fetchTippingPointsGraphByDocName = async (docName, options = {}) => {
  try {
    console.log('🔍 Sending GraphRAG API request for doc_name:', docName)

    if (!docName || typeof docName !== 'string') {
      throw new Error('Invalid doc_name provided')
    }

    // Simplified request body - only send doc_name
    const apiRequestBody = {
      doc_name: docName.trim()
    }

    console.log('📤 API request body:', apiRequestBody)

    const response = await apiClient.post(API_CONFIG.ENDPOINTS.GRAPH, apiRequestBody, {
      timeout: 45000, // Increased timeout for enhanced processing
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    console.log('📥 GraphRAG API response:', response.data)

    // Handle array response - take first element
    const responseData = Array.isArray(response.data) ? response.data[0] : response.data

    if (responseData.success) {
      const nodes = responseData.nodes || []
      const links = responseData.links || []
      const communities = responseData.communities || []
      const claims = responseData.claims || []
      const community_reports = responseData.community_reports || []
      const metadata = responseData.metadata || {}

      console.log('📊 Graph data received:')
      console.log(`   📍 Entities: ${nodes.length}`)
      console.log(`   🔗 Relationships: ${links.length}`)
      console.log(`   🏘️ Communities: ${communities.length}`)
      console.log(`   📋 Claims: ${claims.length}`)
      console.log(`   📄 Reports: ${community_reports.length}`)

      // Clean and prepare nodes for react-force-graph
      const processedNodes = nodes.map(node => {
        const cleanDescription = node.description ? node.description.replace(/^["']|["']$/g, '') : ''
        return {
          ...node,
          description: cleanDescription,
          val: node.val || node.size || 10
        }
      })

      // Clean and prepare links for react-force-graph
      const processedLinks = links.map(link => {
        const cleanDescription = link.description ? link.description.replace(/^["']|["']$/g, '') : ''
        return {
          ...link,
          description: cleanDescription
        }
      })

      // Return all data for UI display
      return {
        success: true,
        graph: {
          nodes: processedNodes,
          links: processedLinks,
          communities: communities,
          claims: claims,
          community_reports: community_reports,
          metadata: metadata
        },
        // Also provide direct access to data for tabs
        entities: processedNodes,
        relationships: processedLinks,
        communities: communities,
        claims: claims,
        community_reports: community_reports,
        metadata: metadata
      }
    } else {
      // Handle case where API returns success=false or error status
      console.warn('GraphRAG API returned error:', responseData.error)
      return {
        success: false,
        error: responseData.error || 'GraphRAG API returned no data',
        graph: {
          nodes: [],
          links: [],
          communities: [],
          claims: [],
          community_reports: [],
          metadata: responseData.metadata || {}
        },
        entities: [],
        relationships: [],
        communities: [],
        claims: [],
        community_reports: [],
        metadata: responseData.metadata || {}
      }
    }
  } catch (error) {
    console.error('Error fetching GraphRAG data:', error)
    
    // Enhanced error handling
    let errorMessage = 'Failed to connect to GraphRAG service'
    
    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const data = error.response.data
      
      if (status === 404) {
        errorMessage = `Document '${docName}' not found in GraphRAG database`
      } else if (status === 500) {
        errorMessage = data?.detail || 'GraphRAG server error'
      } else if (status === 422) {
        errorMessage = data?.detail || 'Invalid request parameters for GraphRAG'
      } else {
        errorMessage = data?.detail || `GraphRAG API error (${status})`
      }
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = 'GraphRAG API timeout - server may be processing complex graph relationships'
    } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      errorMessage = 'Cannot connect to GraphRAG server'
    }
    
    return {
      success: false,
      error: errorMessage,
      graph: {
        nodes: [],
        links: [],
        communities: [],
        claims: [],
        community_reports: [],
        metadata: {
          entities_count: 0,
          relationships_count: 0,
          communities_count: 0,
          claims_count: 0,
          community_reports_count: 0,
          processing_timestamp: new Date().toISOString(),
          doc_name: docName
        }
      }
    }
  }
}

// Helper function for default node colors
const getDefaultNodeColor = (nodeType) => {
  const colorMap = {
    'PERSON': '#FF6B6B',
    'ORGANIZATION': '#4ECDC4',
    'LOCATION': '#45B7D1',
    'RESEARCH_TOPIC': '#F7DC6F',
    'TECHNOLOGY': '#FF9F43',
    'SYSTEM': '#6C5CE7',
    'UNKNOWN': '#BDC3C7'
  }
  return colorMap[nodeType?.toUpperCase()] || '#BDC3C7'
}

// Health Checks
export const checkApiHealth = async () => {
  try {
    const response = await apiClient.get(API_CONFIG.ENDPOINTS.HEALTH)
    return response.data
  } catch (error) {
    console.error('Error checking API health:', error)
    throw error
  }
}

// GraphRAG health check
export const checkGraphRAGHealth = async () => {
  try {
    const response = await apiClient.get('/api/v1/graph/health')
    return {
      ...response.data,
      enhanced_features: {
        intelligent_link_generation: true,
        semantic_relationship_detection: true,
        react_force_graph_compatibility: true
      }
    }
  } catch (error) {
    console.error('Error checking GraphRAG health:', error)
    throw error
  }
}

// Utility Functions
export const getCurrentSessionId = () => {
  return sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)
}

export const clearCurrentSession = () => {
  sessionStorage.removeItem(SESSION_CONFIG.STORAGE_KEY)
}

export const hasActiveSession = () => {
  return !!sessionStorage.getItem(SESSION_CONFIG.STORAGE_KEY)
}