import { 
  startConversationSession, 
  continueConversationSession, 
  endConversationSession 
} from '@/services/api/endpoints'
import { SESSION_CONFIG } from '@/constants/config'

class SessionManager {
  constructor() {
    this.sessionId = null
    this.isSessionActive = false
    this.messageCount = 0
    this.sessionStartTime = null
    this.lastActivityTime = null
    
    // Use environment variables with proper fallbacks
    this.inactivityDuration = (parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MINUTES) || SESSION_CONFIG.TIMEOUT_MINUTES) * 60 * 1000
    this.warningThreshold = (parseInt(import.meta.env.VITE_INACTIVITY_WARNING_MINUTES) || SESSION_CONFIG.WARNING_MINUTES) * 60 * 1000
    
    this.countdownTimer = null
    this.timeoutCallback = null
    this.isInactive = false
    this.inactivityMonitor = null
    
    console.log('SessionManager initialized with:', {
      inactivityDuration: this.inactivityDuration,
      warningThreshold: this.warningThreshold,
      timeoutMinutes: parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MINUTES) || SESSION_CONFIG.TIMEOUT_MINUTES,
      warningMinutes: parseInt(import.meta.env.VITE_INACTIVITY_WARNING_MINUTES) || SESSION_CONFIG.WARNING_MINUTES
    })
  }

  async startConversation(query, language = 'en', difficulty = 'low') {
    try {
      this.resetSession()
      
      console.log('Starting new conversation via /api/v1/chat/start')
      const result = await startConversationSession(query, language, difficulty)
      
      if (result.success && result.session_id && result.response) {
        this.sessionId = result.session_id
        this.activateSession()
        this.saveSessionToMemory()
        
        console.log('New conversation started successfully:', {
          sessionId: this.sessionId,
          messageCount: this.messageCount,
          sourceType: result.sourceType,
          isWebSearch: result.isWebSearch
        })
        
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
      } else {
        throw new Error(result.error || 'Failed to start conversation or receive response')
      }
    } catch (error) {
      console.error('Error starting conversation:', error)
      this.resetSession()
      throw new Error(error.message || 'Failed to start conversation')
    }
  }

  activateSession() {
    this.isSessionActive = true
    this.messageCount = 1
    this.sessionStartTime = Date.now()
    this.lastActivityTime = Date.now()
    this.isInactive = false
    
    this.startInactivityMonitoring()
    console.log('Session activated after successful LLM response:', this.sessionId)
    console.log('Session timing:', {
      inactivityDuration: this.inactivityDuration,
      warningThreshold: this.warningThreshold
    })
  }

  async continueConversation(message, language, difficulty) {
    if (!this.sessionId || !this.isSessionActive) {
      throw new Error('No active session. Please start a new conversation.')
    }

    try {
      this.recordActivity()

      console.log('Continuing conversation via /api/v1/chat/continue/' + this.sessionId)
      const result = await continueConversationSession(
        this.sessionId, 
        message, 
        language, 
        difficulty
      )

      if (result.success && result.response) {
        this.messageCount += 1
        
        console.log('Conversation continued successfully:', {
          sessionId: this.sessionId,
          messageCount: this.messageCount,
          sourceType: result.sourceType,
          isWebSearch: result.isWebSearch
        })
        
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
      } else {
        if (result.error && (
          result.error.includes('Session not found') || 
          result.error.includes('expired')
        )) {
          this.resetSession()
          throw new Error('Session expired. Please start a new conversation.')
        }
        throw new Error(result.error || 'Failed to continue conversation or receive response')
      }
    } catch (error) {
      console.error('Error continuing conversation:', error)
      
      // Handle session not found errors
      if (error.response?.status === 404 || 
          error.message.includes('Session expired') || 
          error.message.includes('Session not found')) {
        console.warn('Session not found on server, resetting local session')
        this.resetSession()
        throw new Error('Session expired. Please start a new conversation.')
      }
      throw error
    }
  }

  recordActivity() {
    this.lastActivityTime = Date.now()
    
    if (this.isInactive) {
      this.isInactive = false
      this.stopCountdownTimer()
      console.log('User activity detected - stopping inactivity countdown')
    }
  }

  startInactivityMonitoring() {
    this.stopInactivityMonitoring()

    this.inactivityMonitor = setInterval(() => {
      if (!this.isSessionActive) {
        this.stopInactivityMonitoring()
        return
      }

      const timeSinceLastActivity = Date.now() - this.lastActivityTime
      const timeUntilTimeout = this.inactivityDuration - timeSinceLastActivity

      if (timeUntilTimeout <= 0) {
        console.log('Session timeout due to inactivity')
        this.handleSessionTimeout()
      } else if (timeUntilTimeout <= this.warningThreshold && !this.isInactive) {
        console.log('Starting inactivity countdown warning')
        this.isInactive = true
        this.startCountdownTimer()
      }
    }, 5000) // Check every 5 seconds for better responsiveness
  }

  stopInactivityMonitoring() {
    if (this.inactivityMonitor) {
      clearInterval(this.inactivityMonitor)
      this.inactivityMonitor = null
    }
  }

  startCountdownTimer() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }

    console.log('Starting inactivity countdown timer')

    this.countdownTimer = setInterval(() => {
      const timeSinceLastActivity = Date.now() - this.lastActivityTime
      const remainingTime = this.inactivityDuration - timeSinceLastActivity
      
      if (remainingTime <= 0) {
        this.handleSessionTimeout()
      }
    }, 1000)
  }

  stopCountdownTimer() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
      this.countdownTimer = null
    }
  }

  async handleSessionTimeout() {
    console.log('Session timeout reached - ending session')
    
    this.stopCountdownTimer()
    this.stopInactivityMonitoring()

    try {
      await this.endSession()
    } catch (error) {
      console.error('Error ending session on timeout:', error)
    }

    if (this.timeoutCallback) {
      this.timeoutCallback()
    }
  }

  setTimeoutCallback(callback) {
    this.timeoutCallback = callback
  }

  getRemainingTime() {
    if (!this.isSessionActive) {
      return 0
    }
    
    const timeSinceLastActivity = Date.now() - this.lastActivityTime
    const remaining = this.inactivityDuration - timeSinceLastActivity
    return Math.max(0, remaining)
  }

  getRemainingMinutes() {
    const remainingMs = this.getRemainingTime()
    return Math.floor(remainingMs / (60 * 1000))
  }

  getRemainingSeconds() {
    const remainingMs = this.getRemainingTime()
    const totalSeconds = Math.floor(remainingMs / 1000)
    return totalSeconds % 60
  }

  async endSession() {
    if (!this.sessionId) {
      return
    }

    this.stopCountdownTimer()
    this.stopInactivityMonitoring()

    try {
      console.log('Ending session via /api/v1/chat/sessions/' + this.sessionId)
      await endConversationSession(this.sessionId)
      console.log('Session ended successfully')
    } catch (error) {
      console.error('Error ending session:', error)
    } finally {
      this.resetSession()
    }
  }

  resetSession() {
    this.sessionId = null
    this.messageCount = 0
    this.isSessionActive = false
    this.sessionStartTime = null
    this.lastActivityTime = null
    this.isInactive = false
    
    this.stopCountdownTimer()
    this.stopInactivityMonitoring()
    
    this.clearSessionFromMemory()
    console.log('Session reset')
  }

  saveSessionToMemory() {
    if (this.sessionId) {
      window.__neuroClima_sessionId = this.sessionId
    }
  }

  clearSessionFromMemory() {
    delete window.__neuroClima_sessionId
  }

  getSessionUrl() {
    if (this.sessionId) {
      return `/response/${this.sessionId}`
    }
    return null
  }

  getSessionStatus() {
    const remainingMs = this.getRemainingTime()
    const minutes = Math.floor(remainingMs / (60 * 1000))
    const seconds = Math.floor((remainingMs % (60 * 1000)) / 1000)
    
    // Show countdown when warning threshold is reached OR when inactive
    const showCountdown = this.isSessionActive && (remainingMs <= this.warningThreshold || this.isInactive)
    
    return {
      hasActiveSession: this.isSessionActive && this.sessionId !== null,
      sessionId: this.sessionId,
      messageCount: this.messageCount,
      isInactive: this.isInactive,
      remainingMinutes: minutes,
      remainingSeconds: seconds,
      remainingMs: remainingMs,
      showCountdown: showCountdown,
      timeSinceLastActivity: this.lastActivityTime ? Date.now() - this.lastActivityTime : 0,
      // Add these for debugging
      inactivityDuration: this.inactivityDuration,
      warningThreshold: this.warningThreshold,
      lastActivityTime: this.lastActivityTime
    }
  }

  onUserActivity() {
    this.recordActivity()
  }

  async healthCheck() {
    try {
      if (this.sessionId) {
        return true
      }
      return true
    } catch (error) {
      console.error('Session manager health check failed:', error)
      return false
    }
  }

  async getStats() {
    return {
      hasActiveSession: this.isSessionActive,
      sessionId: this.sessionId,
      messageCount: this.messageCount,
      sessionStartTime: this.sessionStartTime,
      lastActivityTime: this.lastActivityTime,
      isInactive: this.isInactive,
      inactivityDuration: this.inactivityDuration,
      warningThreshold: this.warningThreshold
    }
  }
}

export const sessionManager = new SessionManager()