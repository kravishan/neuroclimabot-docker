/**
 * Session Manager with WebSocket Support
 *
 * Clean, event-driven session management with real-time countdown from server.
 * No client-side timers - server is source of truth for all session state.
 *
 * Features:
 * - WebSocket connection for real-time status updates
 * - Server-side timeout management
 * - Activity tracking via WebSocket
 * - Automatic session cleanup on timeout
 * - Session deletion on page refresh/unload
 */

import { API_CONFIG } from '@/constants/config'
import {
  startConversationSession,
  continueConversationSession,
  endConversationSession,
  startConversationSessionStreaming,
  continueConversationSessionStreaming
} from '@/services/api/endpoints'

class SessionManager {
  constructor() {
    // Session state
    this.sessionId = null
    this.isSessionActive = false
    this.messageCount = 0

    // Processing state (timer pauses during processing)
    this.isProcessing = false
    this.frozenStatus = null

    // WebSocket connection
    this.ws = null
    this.wsReconnectAttempts = 0
    this.maxReconnectAttempts = 3
    this.reconnectDelay = 2000

    // Session status from server
    this.sessionStatus = {
      remainingSeconds: 0,
      minutes: 0,
      seconds: 0,
      isWarning: false,
      isCritical: false,
      lastActivity: null
    }

    // Callbacks
    this.statusUpdateCallbacks = []
    this.sessionExpiredCallback = null
    this.streamingChunkCallbacks = []

    // Activity debouncing
    this.activityDebounceTimer = null
    this.activityDebounceDelay = 1000 // 1 second

    // Setup cleanup on page unload/refresh
    this._setupUnloadHandler()

    console.log('[SessionManager] Initialized with WebSocket support and SSE streaming')
  }

  /**
   * Start a new conversation session with streaming
   */
  async startConversation(query, language = 'en', difficulty = 'low') {
    try {
      console.log('[SessionManager] Starting new conversation with streaming...')

      // Don't pause timer for initial conversation since session doesn't exist yet

      const result = await startConversationSessionStreaming(
        query,
        language,
        difficulty,

        // onChunk callback - notify subscribers of new content chunks
        (chunk, fullText) => {
          console.log('[SessionManager] Stream chunk received')
          this._notifyStreamingChunk(chunk, fullText)
        },

        // onComplete callback - process final result
        (result) => {
          console.log('[SessionManager] Stream completed')
        },

        // onError callback
        (error) => {
          console.error('[SessionManager] Streaming error:', error)
        }
      )

      if (result.session_id) {
        this.sessionId = result.session_id
        this.isSessionActive = true
        this.messageCount = 1

        console.log(`[SessionManager] Session created: ${this.sessionId}`)

        // Connect WebSocket for real-time updates (timer starts when response arrives)
        await this._connectWebSocket()

        return {
          success: true,
          sessionId: this.sessionId,
          sourceType: result.sourceType,
          isWebSearch: result.isWebSearch,
          response: result.response,
          references: result.references || [],
          referenceCount: result.referenceCount || 0,
          totalAvailable: result.totalAvailable || 0,
          queryPreprocessed: result.queryPreprocessed || false,
          originalQuery: result.originalQuery || query,
          processedQuery: result.processedQuery,
          preprocessingDetails: result.preprocessingDetails || {},
          processingTime: result.processingTime || 0,
          searchResultsSummary: result.searchResultsSummary || {}
        }
      }

      throw new Error('No session ID received from server')

    } catch (error) {
      console.error('[SessionManager] Error starting conversation:', error)
      throw error
    }
  }

  /**
   * Continue existing conversation with streaming
   */
  async continueConversation(message, language = null, difficulty = null) {
    try {
      if (!this.sessionId || !this.isSessionActive) {
        throw new Error('No active session')
      }

      console.log('[SessionManager] Continuing conversation with streaming...')

      // Pause timer during processing
      this.startProcessing()

      const result = await continueConversationSessionStreaming(
        this.sessionId,
        message,
        language,
        difficulty,

        // onChunk callback - notify subscribers of new content chunks
        (chunk, fullText) => {
          console.log('[SessionManager] Stream chunk received')
          this._notifyStreamingChunk(chunk, fullText)
        },

        // onComplete callback - process final result
        (result) => {
          console.log('[SessionManager] Stream completed')
        },

        // onError callback
        (error) => {
          console.error('[SessionManager] Streaming error:', error)
        }
      )

      this.messageCount++

      // Resume timer and reset when response arrives
      this.stopProcessing()

      // Record activity via WebSocket (resets timer on backend)
      this._sendActivityPing()

      return {
        success: true,
        sourceType: result.sourceType,
        isWebSearch: result.isWebSearch,
        response: result.response,
        references: result.references || [],
        referenceCount: result.referenceCount || 0,
        totalAvailable: result.totalAvailable || 0,
        queryPreprocessed: result.queryPreprocessed || false,
        originalQuery: result.originalQuery || message,
        processedQuery: result.processedQuery,
        preprocessingDetails: result.preprocessingDetails || {},
        processingTime: result.processingTime || 0,
        searchResultsSummary: result.searchResultsSummary || {},
        memoryContextUsed: result.memoryContextUsed || false
      }

    } catch (error) {
      console.error('[SessionManager] Error continuing conversation:', error)
      // Resume timer even on error
      this.stopProcessing()
      throw error
    }
  }

  /**
   * End the current session
   */
  async endSession() {
    try {
      if (!this.sessionId) {
        console.warn('[SessionManager] No session to end')
        return
      }

      console.log(`[SessionManager] Ending session ${this.sessionId}`)

      // Close WebSocket first
      this._disconnectWebSocket()

      // Delete session on server
      await endConversationSession(this.sessionId)

      // Reset local state
      this._resetSession()

    } catch (error) {
      console.error('[SessionManager] Error ending session:', error)
      // Reset anyway
      this._resetSession()
    }
  }

  /**
   * Record user activity
   */
  onUserActivity() {
    if (!this.isSessionActive) return

    // Debounce activity pings (max 1 per second)
    if (this.activityDebounceTimer) {
      clearTimeout(this.activityDebounceTimer)
    }

    this.activityDebounceTimer = setTimeout(() => {
      this._sendActivityPing()
    }, this.activityDebounceDelay)
  }

  /**
   * Start processing (pause timer in UI)
   */
  startProcessing() {
    if (!this.isSessionActive) return

    console.log('[SessionManager] Processing started - timer frozen')
    this.isProcessing = true

    // Freeze current countdown state
    this.frozenStatus = { ...this.sessionStatus }
  }

  /**
   * Stop processing (resume timer in UI)
   */
  stopProcessing() {
    if (!this.isSessionActive) return

    console.log('[SessionManager] Processing completed - timer resumed')
    this.isProcessing = false
    this.frozenStatus = null

    // Notify subscribers to refresh with current time
    this._notifyStatusUpdate()
  }

  /**
   * Get current session status
   */
  getSessionStatus() {
    return {
      sessionId: this.sessionId,
      isSessionActive: this.isSessionActive,
      messageCount: this.messageCount,
      isProcessing: this.isProcessing,
      // Use frozen status during processing, otherwise use current status
      ...(this.isProcessing && this.frozenStatus ? this.frozenStatus : this.sessionStatus)
    }
  }

  /**
   * Subscribe to status updates
   */
  onStatusUpdate(callback) {
    this.statusUpdateCallbacks.push(callback)

    // Return unsubscribe function
    return () => {
      this.statusUpdateCallbacks = this.statusUpdateCallbacks.filter(cb => cb !== callback)
    }
  }

  /**
   * Set callback for session expiration
   */
  onSessionExpired(callback) {
    this.sessionExpiredCallback = callback
  }

  /**
   * Subscribe to streaming chunk updates
   */
  onStreamingChunk(callback) {
    this.streamingChunkCallbacks.push(callback)

    // Return unsubscribe function
    return () => {
      this.streamingChunkCallbacks = this.streamingChunkCallbacks.filter(cb => cb !== callback)
    }
  }

  /**
   * Notify all streaming chunk subscribers
   */
  _notifyStreamingChunk(chunk, fullText) {
    this.streamingChunkCallbacks.forEach(callback => {
      try {
        callback({ chunk, fullText })
      } catch (error) {
        console.error('[SessionManager] Error in streaming chunk callback:', error)
      }
    })
  }

  /**
   * Reset session state
   */
  _resetSession() {
    this.sessionId = null
    this.isSessionActive = false
    this.messageCount = 0
    this.isProcessing = false
    this.frozenStatus = null
    this.sessionStatus = {
      remainingSeconds: 0,
      minutes: 0,
      seconds: 0,
      isWarning: false,
      isCritical: false,
      lastActivity: null
    }

    if (this.activityDebounceTimer) {
      clearTimeout(this.activityDebounceTimer)
      this.activityDebounceTimer = null
    }

    console.log('[SessionManager] Session reset')
  }

  /**
   * Connect to WebSocket for real-time status updates
   */
  async _connectWebSocket() {
    if (!this.sessionId) {
      console.warn('[SessionManager] Cannot connect WebSocket: No session ID')
      return
    }

    // Close existing connection if any
    this._disconnectWebSocket()

    try {
      // Get WebSocket URL (replace http with ws, https with wss)
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const baseUrl = API_CONFIG.BASE_URL.replace(/^https?:/, wsProtocol)
      const wsUrl = `${baseUrl}/api/v1/chat/sessions/${this.sessionId}/ws`

      console.log(`[SessionManager] Connecting to WebSocket: ${wsUrl}`)

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[SessionManager] WebSocket connected')
        this.wsReconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this._handleWebSocketMessage(data)
        } catch (error) {
          console.error('[SessionManager] Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('[SessionManager] WebSocket error:', error)
      }

      this.ws.onclose = () => {
        console.log('[SessionManager] WebSocket closed')
        this.ws = null

        // Try to reconnect if session is still active
        if (this.isSessionActive && this.wsReconnectAttempts < this.maxReconnectAttempts) {
          this.wsReconnectAttempts++
          console.log(`[SessionManager] Reconnecting... (attempt ${this.wsReconnectAttempts}/${this.maxReconnectAttempts})`)

          setTimeout(() => {
            this._connectWebSocket()
          }, this.reconnectDelay)
        }
      }

    } catch (error) {
      console.error('[SessionManager] Error connecting WebSocket:', error)
    }
  }

  /**
   * Disconnect WebSocket
   */
  _disconnectWebSocket() {
    if (this.ws) {
      try {
        this.ws.close()
      } catch (error) {
        console.error('[SessionManager] Error closing WebSocket:', error)
      }
      this.ws = null
    }
  }

  /**
   * Handle WebSocket messages from server
   */
  _handleWebSocketMessage(data) {
    switch (data.type) {
      case 'connected':
        console.log('[SessionManager] WebSocket connection confirmed')
        break

      case 'status_update':
        // Update session status from server
        this.sessionStatus = {
          remainingSeconds: data.remaining_seconds,
          minutes: data.minutes,
          seconds: data.seconds,
          isWarning: data.is_warning,
          isCritical: data.is_critical,
          lastActivity: data.last_activity
        }

        // Only notify subscribers if not processing (timer frozen during processing)
        if (!this.isProcessing) {
          this._notifyStatusUpdate()
        }
        break

      case 'session_expired':
        console.warn('[SessionManager] Session expired:', data.message)
        this._handleSessionExpired()
        break

      case 'activity_recorded':
        console.debug('[SessionManager] Activity recorded by server')
        break

      case 'error':
        console.error('[SessionManager] WebSocket error:', data.message)
        break

      default:
        console.warn('[SessionManager] Unknown message type:', data.type)
    }
  }

  /**
   * Send activity ping to server via WebSocket
   */
  _sendActivityPing() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({
          type: 'activity'
        }))
        console.debug('[SessionManager] Activity ping sent')
      } catch (error) {
        console.error('[SessionManager] Error sending activity ping:', error)
      }
    }
  }

  /**
   * Notify all status update subscribers
   */
  _notifyStatusUpdate() {
    const status = this.getSessionStatus()
    this.statusUpdateCallbacks.forEach(callback => {
      try {
        callback(status)
      } catch (error) {
        console.error('[SessionManager] Error in status update callback:', error)
      }
    })
  }

  /**
   * Handle session expiration
   */
  _handleSessionExpired() {
    this._disconnectWebSocket()
    this._resetSession()

    if (this.sessionExpiredCallback) {
      try {
        this.sessionExpiredCallback()
      } catch (error) {
        console.error('[SessionManager] Error in session expired callback:', error)
      }
    }
  }

  /**
   * Setup handler to delete session on page refresh/unload
   */
  _setupUnloadHandler() {
    window.addEventListener('beforeunload', () => {
      if (this.sessionId && this.isSessionActive) {
        console.log('[SessionManager] Page unloading, deleting session...')

        // Use sendBeacon for reliable async request during unload
        // This is more reliable than fetch/axios during page unload
        const deleteUrl = `${API_CONFIG.BASE_URL}/api/v1/chat/sessions/${this.sessionId}`

        // Try sendBeacon first (most reliable)
        if (navigator.sendBeacon) {
          // sendBeacon only supports POST, but we can use it with a delete endpoint
          // that accepts POST with X-HTTP-Method-Override header
          const blob = new Blob([JSON.stringify({})], { type: 'application/json' })
          navigator.sendBeacon(deleteUrl, blob)
        } else {
          // Fallback to synchronous XHR (not ideal but works)
          try {
            const xhr = new XMLHttpRequest()
            xhr.open('DELETE', deleteUrl, false) // synchronous
            xhr.setRequestHeader('Content-Type', 'application/json')

            // Add auth token if available
            const token = localStorage.getItem('auth_token')
            if (token) {
              xhr.setRequestHeader('Authorization', `Bearer ${token}`)
            }

            xhr.send()
          } catch (error) {
            console.error('[SessionManager] Error deleting session on unload:', error)
          }
        }

        // Close WebSocket
        this._disconnectWebSocket()
      }
    })
  }
}

// Export singleton instance
export const sessionManager = new SessionManager()