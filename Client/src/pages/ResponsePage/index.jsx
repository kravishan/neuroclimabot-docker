import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { LightbulbIcon, Coffee, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useSession } from '@/hooks/useSession'
import { sessionManager } from '@/services/session/sessionManager'

// Components
import ResponseContent from '@/components/chat/ResponseContent'
import UserMessage from '@/components/chat/UserMessage'
import MessageInput from '@/components/forms/MessageInput'
import References from '@/components/chat/References'
import PerspectivesColumn from '@/components/chat/PerspectivesColumn'
import { 
  SkeletonTitle, 
  SkeletonResponseContent, 
  SkeletonReferences, 
  SkeletonPerspectives 
} from '@/components/ui/Loading/SkeletonLoader'

import './ResponsePage.css'

const ResponsePage = () => {
  const location = useLocation()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams()

  const {
    sessionStatus,
    isLoading: sessionLoading,
    error: sessionError,
    startConversation,
    continueConversation,
    endSession,
    clearError,
    isSessionActive,
    messageCount: sessionMessageCount,
    updateSessionStatus
  } = useSession()

  const {  
    title: initialTitle = '', 
    question = '', 
    difficultyLevel = 'low', 
    selectedLanguage = 'en'  
  } = location.state || {}

  const [title, setTitle] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [loadingTitle, setLoadingTitle] = useState(true)
  const [loadingResponse, setLoadingResponse] = useState(true)
  const [loadingReferences, setLoadingReferences] = useState(true)
  const [loadingPerspectives, setLoadingPerspectives] = useState(true)
  const [showSessionRestored, setShowSessionRestored] = useState(false)

  const [messageData, setMessageData] = useState({})
  const [loadingMessageData, setLoadingMessageData] = useState({})
  const [loadingMessageReferences, setLoadingMessageReferences] = useState({})

  const [visibleReferencesIds, setVisibleReferencesIds] = useState({})
  const [latestResponseId, setLatestResponseId] = useState(null)
  
  // Track expansion states for each perspective
  const [expandedPerspectives, setExpandedPerspectives] = useState({})

  const [countdownDisplay, setCountdownDisplay] = useState({
    minutes: 20,
    seconds: 0,
    isWarning: false,
    isCritical: false,
    showCountdown: false
  })

  const isDataFetched = useRef(false)
  const messagesEndRef = useRef(null)
  const countdownUpdateRef = useRef(null)

  useDocumentTitle(title)

  // Set up session timeout callback and countdown
  useEffect(() => {
    sessionManager.setTimeoutCallback(() => {
      console.log('Session timeout - redirecting to home')
      navigate('/', { replace: true })
    })

    if (isSessionActive) {
      startCountdownDisplay()
    }

    return () => {
      if (countdownUpdateRef.current) {
        clearInterval(countdownUpdateRef.current)
      }
    }
  }, [isSessionActive, navigate])

  // Track user activity for inactivity monitoring
  useEffect(() => {
    const handleUserActivity = () => {
      if (isSessionActive) {
        sessionManager.onUserActivity()
      }
    }

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
    
    events.forEach(event => {
      document.addEventListener(event, handleUserActivity, { passive: true })
    })

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleUserActivity)
      })
    }
  }, [isSessionActive])

  const startCountdownDisplay = () => {
    if (countdownUpdateRef.current) {
      clearInterval(countdownUpdateRef.current)
    }

    countdownUpdateRef.current = setInterval(() => {
      const status = sessionManager.getSessionStatus()
      
      if (!status.showCountdown) {
        setCountdownDisplay(prev => ({
          ...prev,
          showCountdown: false
        }))
        return
      }

      const remainingMs = status.remainingMs
      
      if (remainingMs <= 0) {
        setCountdownDisplay({
          minutes: 0,
          seconds: 0,
          isWarning: false,
          isCritical: true,
          showCountdown: false
        })
        
        if (countdownUpdateRef.current) {
          clearInterval(countdownUpdateRef.current)
          countdownUpdateRef.current = null
        }
        return
      }

      const totalSeconds = Math.floor(remainingMs / 1000)
      const minutes = Math.floor(totalSeconds / 60)
      const seconds = totalSeconds % 60
      
      const isWarning = minutes < 5 && minutes >= 1
      const isCritical = minutes < 1

      setCountdownDisplay({
        minutes,
        seconds,
        isWarning,
        isCritical,
        showCountdown: true
      })
    }, 1000)
  }

  // Handle URL session ID validation and updates
  useEffect(() => {
    const handleSessionUrl = async () => {
      if (urlSessionId === 'new' && question) {
        console.log('New conversation detected from ChatInput:', question)
        return
      }

      if (urlSessionId && urlSessionId !== 'new' && urlSessionId !== sessionStatus.sessionId) {
        if (sessionStatus.sessionId && sessionStatus.sessionId !== urlSessionId) {
          console.log('URL session mismatch, updating to current session:', sessionStatus.sessionId)
          navigate(`/response/${sessionStatus.sessionId}`, { 
            replace: true,
            state: location.state 
          })
        } else if (!isSessionActive) {
          console.warn('No active session found for URL session ID:', urlSessionId)
          navigate('/', { replace: true })
        }
      }

      if (urlSessionId && urlSessionId !== 'new' && !isSessionActive && !question) {
        console.warn('Invalid session state, redirecting to home')
        navigate('/', { replace: true })
      }
    }

    handleSessionUrl()
  }, [urlSessionId, sessionStatus.sessionId, isSessionActive, navigate, location.state, question])

  // Update URL when session ID becomes available
  useEffect(() => {
    if (sessionStatus.sessionId && urlSessionId === 'new') {
      navigate(`/response/${sessionStatus.sessionId}`, { 
        replace: true,
        state: location.state 
      })
    }
  }, [sessionStatus.sessionId, urlSessionId, navigate, location.state])

  // Show session restored notification
  useEffect(() => {
    if (isSessionActive && sessionMessageCount > 0 && !isDataFetched.current && urlSessionId !== 'new') {
      setShowSessionRestored(true)
      setTimeout(() => setShowSessionRestored(false), 5000)
    }
  }, [isSessionActive, sessionMessageCount, urlSessionId])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Initial Data Fetching with staged loading states
  useEffect(() => {
    if (question && !isDataFetched.current && urlSessionId === 'new') {
      console.log('Starting new conversation from ChatInput:', question)
      setMessages([{ id: 1, type: 'user', content: question }])
      fetchInitialData(question)
      isDataFetched.current = true
    }
    else if (!question && urlSessionId && urlSessionId !== 'new' && isSessionActive) {
      console.log('Existing session detected, no new data fetch needed:', urlSessionId)
      setIsInitialLoading(false)
      setLoadingTitle(false)
      setLoadingResponse(false)
      setLoadingReferences(false)
      setLoadingPerspectives(false)
      setTitle('Continuing Conversation')
      isDataFetched.current = true
    }
    else if (!question && urlSessionId === 'new') {
      console.warn('New session requested but no question provided, redirecting home')
      navigate('/', { replace: true })
    }
  }, [question, urlSessionId, isSessionActive, navigate])

  useEffect(() => {
    if (messages.length > 2) {
      scrollToBottom()
    }
  }, [messages, scrollToBottom])

  // Force session status update when component mounts
  useEffect(() => {
    console.log('ResponsePage: Forcing session status update on mount')
    updateSessionStatus()
  }, [updateSessionStatus])
  
  const fetchInitialData = async (queryText) => {
    setIsInitialLoading(true)
    setLoadingTitle(true)
    setLoadingResponse(true)
    setLoadingReferences(true)
    setLoadingPerspectives(true)
    clearError()
    
    try {
      const result = await startConversation(queryText, selectedLanguage, difficultyLevel)
      
      if (result.success) {
        const { response, references, referenceCount, totalAvailable, sourceType, isWebSearch, usesRag } = result

        // Stage 1: Set title
        setTitle(response.title)
        setLoadingTitle(false)

        await new Promise(resolve => setTimeout(resolve, 300))

        // Stage 2: Set response content
        const assistantMessageId = 2
        setMessages(prevMessages => [
          ...prevMessages,
          { id: assistantMessageId, type: 'assistant', content: response.content }
        ])
        setLatestResponseId(assistantMessageId)
        setLoadingResponse(false)

        await new Promise(resolve => setTimeout(resolve, 400))

        // Stage 3: Set references data
        setMessageData(prevData => ({
          ...prevData,
          [assistantMessageId]: {
            socialTippingPoint: response.socialTippingPoint,
            qualifyingFactors: response.qualifyingFactors || [],
            references: references || [],
            referenceCount: referenceCount || 0,
            totalAvailable: totalAvailable || 0,
            sourceType: sourceType || 'rag',
            isWebSearch: isWebSearch || false,
            usesRag: usesRag !== undefined ? usesRag : true,
            queryPreprocessed: result.queryPreprocessed || false,
            originalQuery: result.originalQuery || queryText,
            processedQuery: result.processedQuery,
            preprocessingDetails: result.preprocessingDetails || {},
            processingTime: result.processingTime || 0,
            searchResultsSummary: result.searchResultsSummary || {}
          }
        }))
        setLoadingReferences(false)
        
        await new Promise(resolve => setTimeout(resolve, 300))
        
        // Stage 4: Set perspectives (only for non-web search)
        setLoadingPerspectives(false)
        setIsInitialLoading(false)
        
        if (result.queryPreprocessed) {
          console.log('[ResponsePage] Query was preprocessed for initial query:')
          console.log(`  Original: "${result.originalQuery}"`)
          console.log(`  Processed: "${result.processedQuery}"`)
          console.log('  Changes:', result.preprocessingDetails.changes_made || [])
        }
      }
    } catch (error) {
      console.error('Error fetching initial data:', error)

      // Determine error message based on error type
      let errorMessage = 'Sorry, we encountered an error. Please try starting a new conversation.'

      if (error.code === 'ECONNABORTED') {
        errorMessage = 'The request took too long to complete. The backend service may be busy or experiencing issues. Please try again later.'
      } else if (error.response) {
        const status = error.response.status
        if (status === 500 || status === 502 || status === 503) {
          errorMessage = 'The backend service is currently unavailable. Please try again later.'
        } else if (status === 404) {
          errorMessage = 'The requested service was not found. Please contact support.'
        } else if (status >= 400) {
          errorMessage = 'There was an error processing your request. Please try again.'
        }
      } else if (error.message.includes('Network Error') || !error.response) {
        errorMessage = 'Unable to connect to the backend service. Please check your internet connection and try again.'
      }

      setTitle('Error Loading Response')

      // Display error message in the assistant response
      const assistantMessageId = 2
      setMessages(prevMessages => [
        ...prevMessages,
        {
          id: assistantMessageId,
          type: 'assistant',
          content: errorMessage,
          isError: true
        }
      ])

      setIsInitialLoading(false)
      setLoadingTitle(false)
      setLoadingResponse(false)
      setLoadingReferences(false)
      setLoadingPerspectives(false)
    }
  }

  const handleToggleReferences = (messageId) => {
    setVisibleReferencesIds(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }))
  }

  // Handler to update perspective expansion state
  const handlePerspectiveExpansionChange = useCallback((messageId, expansionState) => {
    setExpandedPerspectives(prev => ({
      ...prev,
      [messageId]: expansionState
    }))
  }, [])

  const handleSendMessage = async (input) => {
    if (!input.trim()) return
    
    sessionManager.onUserActivity()
    
    if (!isSessionActive) {
      console.error('No active session for continuing conversation')
      navigate('/', { replace: true })
      return
    }
    
    setLoading(true)
    clearError()
    
    const newUserMessage = {
      id: messages.length + 1,
      type: 'user',
      content: input.trim()
    }
  
    const placeholderAIMessageId = newUserMessage.id + 1
    const placeholderAIMessage = {
      id: placeholderAIMessageId,
      type: 'assistant',
      content: '',
      isLoading: true
    }
  
    setMessages(prevMessages => [
      ...prevMessages, 
      newUserMessage, 
      placeholderAIMessage
    ])

    // Set loading states for the new message
    setLoadingMessageData(prev => ({
      ...prev,
      [placeholderAIMessageId]: true
    }))

    setLoadingMessageReferences(prev => ({
      ...prev,
      [placeholderAIMessageId]: true
    }))
    
    setLatestResponseId(placeholderAIMessageId)
    
    // Reset expansion states for all previous messages when new message is added
    setExpandedPerspectives(prev => {
      const newState = {}
      Object.keys(prev).forEach(key => {
        newState[key] = {
          isExpanded: false,
          showQualifyingFactors: false
        }
      })
      return newState
    })
    
    try {
      const result = await continueConversation(input.trim(), selectedLanguage, difficultyLevel)
      
      if (result.success) {
        const { response, references, referenceCount, totalAvailable, sourceType, isWebSearch, usesRag } = result

        // Update message content
        setMessages(prevMessages => {
          return prevMessages.map(msg =>
            msg.id === placeholderAIMessageId
              ? { ...msg, content: response.content, isLoading: false }
              : msg
          )
        })

        // Update message data
        setMessageData(prevData => ({
          ...prevData,
          [placeholderAIMessageId]: {
            socialTippingPoint: response.socialTippingPoint,
            qualifyingFactors: response.qualifyingFactors || [],
            references: references || [],
            referenceCount: referenceCount || 0,
            totalAvailable: totalAvailable || 0,
            sourceType: sourceType || 'rag',
            isWebSearch: isWebSearch || false,
            usesRag: usesRag !== undefined ? usesRag : true,
            queryPreprocessed: result.queryPreprocessed || false,
            originalQuery: result.originalQuery || input.trim(),
            processedQuery: result.processedQuery,
            preprocessingDetails: result.preprocessingDetails || {},
            processingTime: result.processingTime || 0,
            searchResultsSummary: result.searchResultsSummary || {},
            memoryContextUsed: result.memoryContextUsed || false
          }
        }))

        // Clear loading states
        setLoadingMessageData(prev => ({
          ...prev,
          [placeholderAIMessageId]: false
        }))

        setLoadingMessageReferences(prev => ({
          ...prev,
          [placeholderAIMessageId]: false
        }))
        
        if (result.queryPreprocessed) {
          console.log('[ResponsePage] Query was preprocessed for continuous chat:')
          console.log(`  Original: "${result.originalQuery}"`)
          console.log(`  Processed: "${result.processedQuery}"`)
          console.log('  Changes:', result.preprocessingDetails.changes_made || [])
          
          if (result.preprocessingDetails.pronouns_resolved) {
            console.log('  Pronouns resolved:', result.preprocessingDetails.pronouns_resolved)
          }
          
          if (result.memoryContextUsed) {
            console.log('  Session memory context was used for preprocessing')
          }
        }
      }
    } catch (error) {
      console.error('Error in continuous chat:', error)

      // Determine error message based on error type
      let errorMessage = 'Sorry, we encountered an error processing your message. Please try again or start a new conversation.'

      if (error.code === 'ECONNABORTED') {
        errorMessage = 'The request took too long to complete. The backend service may be busy or experiencing issues. Please try again later.'
      } else if (error.response) {
        const status = error.response.status
        if (status === 500 || status === 502 || status === 503) {
          errorMessage = 'The backend service is currently unavailable. Please try again later.'
        } else if (status === 404) {
          errorMessage = 'Session not found. Please start a new conversation.'
        } else if (status >= 400) {
          errorMessage = 'There was an error processing your message. Please try again.'
        }
      } else if (error.message.includes('Network Error') || !error.response) {
        errorMessage = 'Unable to connect to the backend service. Please check your internet connection and try again.'
      }

      setMessages(prevMessages => {
        return prevMessages.map(msg =>
          msg.id === placeholderAIMessageId
            ? {
                ...msg,
                content: errorMessage,
                isLoading: false,
                isError: true
              }
            : msg
        )
      })

      setLoadingMessageData(prev => ({
        ...prev,
        [placeholderAIMessageId]: false
      }))

      setLoadingMessageReferences(prev => ({
        ...prev,
        [placeholderAIMessageId]: false
      }))
    } finally {
      setLoading(false)
    }
  }

  const handleStartNewConversation = async () => {
    await endSession()
    navigate('/', { replace: true })
  }

  const handleExplore = useCallback((responseId, references = []) => {
    const messageInfo = messageData[responseId]
    const tippingPoint = messageInfo?.socialTippingPoint || ''
    const allReferences = references.length > 0 ? references : messageInfo?.references || []

    // Don't allow exploration for web search results
    if (messageInfo?.isWebSearch) {
      console.warn('Exploration not available for web search results')
      return
    }

    const firstReference = allReferences.length > 0 ? allReferences[0] : null
    const secondReference = allReferences.length > 1 ? allReferences[1] : null

    const firstDocName = firstReference?.doc_name || null
    const secondDocName = secondReference?.doc_name || null

    if (!firstDocName) {
      console.warn('No doc_name found in references')
      return
    }

    console.log('Sending doc_names to explore page:', {
      firstDocName,
      secondDocName,
      tippingPoint,
      totalReferences: allReferences.length
    })

    // Pass both doc names to explore page for fallback
    let newTabUrl = `/explore-tipping-points?docname=${encodeURIComponent(firstDocName)}`
    if (secondDocName) {
      newTabUrl += `&fallback=${encodeURIComponent(secondDocName)}`
    }
    window.open(newTabUrl, '_blank', 'noopener,noreferrer')

  }, [messageData])

  const getMessagePairs = () => {
    const pairs = []
    for (let i = 0; i < messages.length; i += 2) {
      if (i + 1 < messages.length) {
        pairs.push({
          userMessage: messages[i],
          assistantMessage: messages[i + 1],
        })
      } else {
        pairs.push({
          userMessage: messages[i],
          assistantMessage: null,
        })
      }
    }
    return pairs
  }

  const messagePairs = getMessagePairs()

  const shouldShowReferences = (messageId) => {
    return messageId === latestResponseId || visibleReferencesIds[messageId] === true
  }

  const getMessageData = (messageId) => {
    return messageData[messageId] || {
      socialTippingPoint: '',
      qualifyingFactors: [],
      references: [],
      referenceCount: 0,
      totalAvailable: 0,
      sourceType: 'rag',
      isWebSearch: false,
      usesRag: true
    }
  }

  // Updated helper function to conditionally show heading based on response position and type
  const getResponseHeading = (msgData, isFirstResponse) => {
    // For web search results, always show "Web search" heading
    if (msgData.isWebSearch) {
      return (
        <>
          <Search size={24} />
          <span>{t('webSearch')}</span>
        </>
      )
    }
    
    // For non-web search results, only show "General perspective" for the first response
    if (isFirstResponse) {
      return (
        <>
          <LightbulbIcon size={24} />
          <span>{t('generalPerspective')}</span>
        </>
      )
    }
    
    // For subsequent non-web search responses, show no heading
    return null
  }

  const formatCountdown = () => {
    const { minutes, seconds } = countdownDisplay
    if (minutes > 0) {
      return `${minutes} min${minutes !== 1 ? 's' : ''}`
    } else {
      return `${seconds}s`
    }
  }

  // Inactivity Warning Component
  const InactivityWarning = () => {
    const { showCountdown, isWarning, isCritical } = countdownDisplay
    
    if (!showCountdown || !isSessionActive) return null
    
    return (
      <div className={`inactivity-warning ${isCritical ? 'critical' : isWarning ? 'warning' : ''}`}>
        <div className="inactivity-content">
          <Coffee size={20} />
          <div className="inactivity-text">
            <p className="inactivity-title">
              {isCritical ? 'Session ending soon!' : 'You seem inactive'}
            </p>
            <p className="inactivity-message">
              Your session will end in {formatCountdown()} due to inactivity. 
              {isCritical ? ' Click anywhere to stay active.' : ' Any interaction will reset the timer.'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Session Restored Notification
  const SessionRestoredNotification = () => {
    if (!showSessionRestored) return null
    
    return (
      <div className="session-restored-notification">
        <Coffee size={16} />
        Unable to restore session - start a new conversation
      </div>
    )
  }

  return (
    <div className="response-container">
      <SessionRestoredNotification />
      <InactivityWarning />
      
      <div className="response-header-row">
        {/* Title skeleton now shows in the correct location */}
        {loadingTitle ? (
          <SkeletonTitle />
        ) : (
          <h3 className="response-title fade-in">
            {title}
          </h3>
        )}
      </div>
      
      <div className="content-wrapper">
        <div className="response-column">
          <div className="user-messages-section">
            {isInitialLoading ? (
              <div className="connected-perspectives-container">
                <div className="message-perspective-pair">
                  <div className="message-content-wrapper">
                    {messages.length > 0 && (
                      <UserMessage content={messages[0].content} />
                    )}
                    
                    {/* Response content - no title skeleton here */}
                    {loadingResponse ? (
                      <div className="loading-message skeleton-with-margin">
                        <SkeletonResponseContent />
                      </div>
                    ) : (
                      messages.length > 1 && (
                        <ResponseContent
                          content={messages[1].content}
                          isDataLoading={false}
                          textComplete={true}
                          fadeIn={true}
                          heading={getResponseHeading(getMessageData(messages[1].id), true)} // Always true for first response
                          responseId={`response-${messages[1].id}`}
                          references={getMessageData(messages[1].id).references || []}
                          isLatestResponse={true}
                          loadingReferences={false}
                          onToggleReferences={() => handleToggleReferences(messages[1].id)}
                          referencesVisible={true}
                          conversationType={getMessageData(messages[1].id).searchResultsSummary?.conversation_type || 'unknown'}
                          language={selectedLanguage}
                        />
                      )
                    )}
                    
                    {loadingReferences ? (
                      <SkeletonReferences count={3} />
                    ) : (
                      messages.length > 1 && (
                        <References 
                          references={getMessageData(messages[1].id).references || []} 
                          isDataLoading={false}
                          fadeIn={true}
                          visible={true}
                          mostRelevantCount={getMessageData(messages[1].id).referenceCount}
                          totalRelevantDocuments={getMessageData(messages[1].id).totalAvailable}
                        />
                      )
                    )}
                  </div>
                  
                  <div className="perspective-wrapper">
                    {loadingPerspectives ? (
                      <div className="skeleton-perspective-container">
                        <SkeletonPerspectives />
                      </div>
                    ) : (
                      messages.length > 1 && !getMessageData(messages[1].id).isWebSearch && getMessageData(messages[1].id).usesRag && (
                        <PerspectivesColumn 
                          isDataLoading={false}
                          socialTippingPoint={getMessageData(messages[1].id).socialTippingPoint || ''}
                          qualifyingFactors={getMessageData(messages[1].id).qualifyingFactors || []}
                          fadeIn={true}
                          handleExplore={handleExplore}
                          skipHeader={true}
                          responseId={messages[1].id}
                          references={getMessageData(messages[1].id).references || []}
                          expansionState={expandedPerspectives[messages[1].id]}
                          onExpansionChange={handlePerspectiveExpansionChange}
                        />
                      )
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="connected-perspectives-container">
                {messagePairs.map((pair, index) => {
                  const msgData = pair.assistantMessage ? getMessageData(pair.assistantMessage.id) : {}
                  const isLoadingData = pair.assistantMessage ? loadingMessageData[pair.assistantMessage.id] : false
                  const isLoadingRefs = pair.assistantMessage ? loadingMessageReferences[pair.assistantMessage.id] : false
                  
                  // Determine if this is the first response (index 0 = first message pair)
                  const isFirstResponse = index === 0
                  
                  return (
                    <div key={pair.userMessage.id} className="message-perspective-pair">
                      <div className="message-content-wrapper">
                        <UserMessage content={pair.userMessage.content} />
                        
                        {pair.assistantMessage && (
                          pair.assistantMessage.isLoading ? (
                            <div className="loading-message skeleton-with-margin">
                              <SkeletonResponseContent />
                            </div>
                          ) : (
                            <ResponseContent
                              content={pair.assistantMessage.content}
                              isDataLoading={false}
                              textComplete={true}
                              fadeIn={true}
                              heading={getResponseHeading(msgData, isFirstResponse)} // Pass whether this is first response
                              responseId={`response-${pair.assistantMessage.id}`}
                              references={msgData.references || []}
                              isLatestResponse={pair.assistantMessage.id === latestResponseId}
                              loadingReferences={false}
                              onToggleReferences={() => handleToggleReferences(pair.assistantMessage.id)}
                              referencesVisible={shouldShowReferences(pair.assistantMessage.id)}
                              isError={pair.assistantMessage.isError}
                              conversationType={msgData.searchResultsSummary?.conversation_type || 'unknown'}
                              language={selectedLanguage}
                            />
                          )
                        )}
                        
                        {pair.assistantMessage && !pair.assistantMessage.isError && (
                          isLoadingRefs ? (
                            <SkeletonReferences count={3} />
                          ) : (
                            <References 
                              references={msgData.references || []} 
                              isDataLoading={false}
                              fadeIn={true}
                              visible={shouldShowReferences(pair.assistantMessage.id)}
                              mostRelevantCount={msgData.referenceCount}
                              totalRelevantDocuments={msgData.totalAvailable}
                            />
                          )
                        )}
                      </div>
                      
                      <div className="perspective-wrapper">
                        {pair.assistantMessage && !pair.assistantMessage.isError && !msgData.isWebSearch && msgData.usesRag && (
                          isLoadingData ? (
                            <div className="skeleton-perspective-container">
                              <SkeletonPerspectives />
                            </div>
                          ) : (
                            <PerspectivesColumn 
                              isDataLoading={false}
                              socialTippingPoint={msgData.socialTippingPoint || ''}
                              qualifyingFactors={msgData.qualifyingFactors || []}
                              fadeIn={true}
                              handleExplore={handleExplore}
                              skipHeader={true}
                              responseId={pair.assistantMessage.id}
                              references={msgData.references || []}
                              expansionState={expandedPerspectives[pair.assistantMessage.id]}
                              onExpansionChange={handlePerspectiveExpansionChange}
                            />
                          )
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          <div className="message-input-container">
            <MessageInput 
              onSendMessage={handleSendMessage}
              loading={loading || sessionLoading}
              t={t}
            />
          </div>
          
          <div className="disclaimer-text-style">
            <p className="disclaimer-message">
              {t('disclaimer')}
              <a href="/disclaimer" className="learn-more-link"  target="_blank" rel="noopener noreferrer">{t('learnMore')}</a>  
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ResponsePage