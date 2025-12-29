import React, { useState, useRef, useEffect } from 'react'
import { Copy, Check, ThumbsUp, ThumbsDown, Volume2, Square, ChevronDown, ChevronUp } from 'lucide-react'
import { sendResponseFeedback } from '@/services/api/endpoints'
import { SkeletonResponseContent } from '@/components/ui/Loading/SkeletonLoader'
import './ResponseContent.css'

const ResponseContent = ({
  content,
  isDataLoading,
  textComplete,
  fadeIn,
  heading,
  responseId,
  references,
  mostRelevantCount,
  totalRelevantDocuments,
  isLatestResponse,
  loadingReferences,
  onToggleReferences,
  referencesVisible,
  isError,
  conversationType,
  language = 'en'
}) => {
  const [showCopySuccess, setShowCopySuccess] = useState(false)
  const [copyTooltip, setCopyTooltip] = useState('Copy to clipboard')
  const [feedbackGiven, setFeedbackGiven] = useState(null)
  const [feedbackStatus, setFeedbackStatus] = useState(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const textRef = useRef(null)
  const utteranceRef = useRef(null)
  
  // Load voices when component mounts
  useEffect(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = () => {
        const voices = window.speechSynthesis.getVoices()
        console.log('Available voices loaded:', voices.length)
      }
      
      window.speechSynthesis.getVoices()
    }
    
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  const handleCopy = () => {
    const copyTextToClipboard = (text) => {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.top = '0'
      textArea.style.left = '0'
      textArea.style.width = '2em'
      textArea.style.height = '2em'
      textArea.style.padding = '0'
      textArea.style.border = 'none'
      textArea.style.outline = 'none'
      textArea.style.boxShadow = 'none'
      textArea.style.background = 'transparent'
      
      document.body.appendChild(textArea)
      textArea.select()
      
      let success = false
      
      try {
        success = document.execCommand('copy')
      } catch (err) {
        console.error('Failed to copy text: ', err)
      }
      
      document.body.removeChild(textArea)
      return success
    }
    
    if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText(content)
        .then(() => {
          setShowCopySuccess(true)
          setCopyTooltip('Copied!')
          
          setTimeout(() => {
            setShowCopySuccess(false)
            setCopyTooltip('Copy to clipboard')
          }, 2000)
        })
        .catch(err => {
          console.error('Failed to copy text with Clipboard API: ', err)
          const success = copyTextToClipboard(content)
          if (success) {
            setShowCopySuccess(true)
            setCopyTooltip('Copied!')
            
            setTimeout(() => {
              setShowCopySuccess(false)
              setCopyTooltip('Copy to clipboard')
            }, 2000)
          } else {
            setCopyTooltip('Copy failed')
            
            setTimeout(() => {
              setCopyTooltip('Copy to clipboard')
            }, 2000)
          }
        })
    } else {
      const success = copyTextToClipboard(content)
      if (success) {
        setShowCopySuccess(true)
        setCopyTooltip('Copied!')
        
        setTimeout(() => {
          setShowCopySuccess(false)
          setCopyTooltip('Copy to clipboard')
        }, 2000)
      } else {
        setCopyTooltip('Copy failed')
        
        setTimeout(() => {
          setCopyTooltip('Copy to clipboard')
        }, 2000)
      }
    }
  }

  const handleThumbsUp = () => {
    // Allow changing from down to up
    setFeedbackGiven('up')
    sendFeedback('up')
  }

  const handleThumbsDown = () => {
    // Allow changing from up to down
    setFeedbackGiven('down')
    sendFeedback('down')
  }

  const sendFeedback = async (feedbackType) => {
    try {
      setFeedbackStatus('sending')

      const result = await sendResponseFeedback(
        responseId || `response-${Date.now()}`,
        feedbackType,
        'anonymous',
        '',
        conversationType || 'unknown',
        language
      )

      setFeedbackStatus('success')
      console.log('Feedback submitted successfully:', result)
    } catch (error) {
      setFeedbackStatus('error')
      console.error('Error submitting feedback:', error)
    }
  }
  
  const toggleReferences = () => {
    if (onToggleReferences) {
      onToggleReferences()
    }
  }

  const getBestVoice = () => {
    if (!('speechSynthesis' in window)) return null

    const voices = window.speechSynthesis.getVoices()
    if (!voices || voices.length === 0) return null

    // Map language codes to locale preferences
    const languageToLocale = {
      'en': ['en-US', 'en-GB', 'en'],
      'it': ['it-IT', 'it'],
      'pt': ['pt-BR', 'pt-PT', 'pt'],
      'el': ['el-GR', 'el']
    }

    const locales = languageToLocale[language] || ['en-US', 'en']

    // Voice quality preferences (in order of preference)
    const qualityKeywords = ['premium', 'neural', 'enhanced', 'natural', 'google', 'microsoft']

    // First, try to find high-quality voices for the target language
    for (const locale of locales) {
      const localeMatches = voices.filter(voice =>
        voice.lang.toLowerCase().includes(locale.toLowerCase())
      )

      if (localeMatches.length === 0) continue

      // Try to find a high-quality voice
      for (const keyword of qualityKeywords) {
        const qualityMatch = localeMatches.find(voice =>
          voice.name.toLowerCase().includes(keyword.toLowerCase())
        )
        if (qualityMatch) {
          console.log(`Selected high-quality voice: ${qualityMatch.name} (${qualityMatch.lang})`)
          return qualityMatch
        }
      }

      // If no high-quality voice found, return first voice for this locale
      console.log(`Selected voice: ${localeMatches[0].name} (${localeMatches[0].lang})`)
      return localeMatches[0]
    }

    // Fallback to first available voice
    console.log(`Fallback voice: ${voices[0].name} (${voices[0].lang})`)
    return voices[0]
  }

  const handleReadAloud = () => {
    if (isSpeaking) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
        setIsSpeaking(false)
        utteranceRef.current = null
      }
    } else {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
        
        const utterance = new SpeechSynthesisUtterance(content)
        
        const voice = getBestVoice()
        if (voice) {
          utterance.voice = voice
          console.log(`Using voice: ${voice.name} (${voice.lang})`)
        }
        
        utterance.rate = 0.92
        utterance.pitch = 1.0
        utterance.volume = 1.0
        
        utterance.onstart = () => {
          setIsSpeaking(true)
          console.log('Speech started')
        }
        
        utterance.onend = () => {
          setIsSpeaking(false)
          console.log('Speech ended normally')
          utteranceRef.current = null
        }
        
        utterance.onerror = (event) => {
          console.error('Speech synthesis error:', event)
          setIsSpeaking(false)
          utteranceRef.current = null
        }
        
        utteranceRef.current = utterance
        window.speechSynthesis.speak(utterance)
        
        const intervalId = setInterval(() => {
          if (utteranceRef.current && window.speechSynthesis.speaking) {
            window.speechSynthesis.pause()
            window.speechSynthesis.resume()
            console.log('Keeping speech synthesis alive')
          } else {
            clearInterval(intervalId)
          }
        }, 10000)
      }
    }
  }

  const processMarkdownInText = (text) => {
    const parts = []
    let lastIndex = 0
    
    const boldRegex = /(\*{4}|\*{2})(.*?)\1/g
    let match
    
    while ((match = boldRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index))
      }
      
      parts.push(<strong key={match.index}>{match[2]}</strong>)
      lastIndex = match.index + match[0].length
    }
    
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex))
    }
    
    return parts.length > 1 ? parts : text
  }

  const renderContent = (text) => {
    // Check for numbered list pattern
    const listRegex = /\d+\.\s\*\*(.*?)\*\*:\s(.*?)(?=(\n\d+\.\s\*\*|$))/gs
    const matches = [...text.matchAll(listRegex)]

    if (matches.length > 0) {
      const firstMatchIndex = matches[0].index
      const textBeforeList = text.substring(0, firstMatchIndex).trim()
      
      return (
        <div>
          {textBeforeList && (
            <div style={{ whiteSpace: 'pre-line', marginBottom: '16px' }}>
              {processMarkdownInText(textBeforeList)}
            </div>
          )}
          
          <ol style={{ marginTop: textBeforeList ? '0' : '16px' }}>
            {matches.map((match, index) => (
              <li key={index} style={{ marginBottom: '8px' }}>
                <strong>{match[1]}</strong>: {match[2]}
              </li>
            ))}
          </ol>
          
          {(() => {
            const lastMatch = matches[matches.length - 1]
            const lastMatchEnd = lastMatch.index + lastMatch[0].length
            const textAfterList = text.substring(lastMatchEnd).trim()
            
            if (textAfterList) {
              return (
                <div style={{ whiteSpace: 'pre-line', marginTop: '16px' }}>
                  {processMarkdownInText(textAfterList)}
                </div>
              )
            }
            return null
          })()}
        </div>
      )
    }

    // Handle regular bullet lists (•, -, *)
    const bulletListRegex = /^[\s]*[•\-\*]\s+(.+)$/gm
    const bulletMatches = [...text.matchAll(bulletListRegex)]
    
    if (bulletMatches.length > 0) {
      const firstBulletIndex = bulletMatches[0].index
      const lastBulletMatch = bulletMatches[bulletMatches.length - 1]
      const lastBulletEnd = lastBulletMatch.index + lastBulletMatch[0].length
      
      const textBeforeList = text.substring(0, firstBulletIndex).trim()
      const textAfterList = text.substring(lastBulletEnd).trim()
      
      return (
        <div>
          {textBeforeList && (
            <div style={{ whiteSpace: 'pre-line', marginBottom: '16px' }}>
              {processMarkdownInText(textBeforeList)}
            </div>
          )}
          
          <ul style={{ marginTop: textBeforeList ? '0' : '16px' }}>
            {bulletMatches.map((match, index) => (
              <li key={index} style={{ marginBottom: '4px' }}>
                {processMarkdownInText(match[1])}
              </li>
            ))}
          </ul>
          
          {textAfterList && (
            <div style={{ whiteSpace: 'pre-line', marginTop: '16px' }}>
              {processMarkdownInText(textAfterList)}
            </div>
          )}
        </div>
      )
    }

    // Handle markdown-style bold text (both ** and ****)
    const processedContent = processMarkdownInText(text)
    
    return (
      <div style={{ whiteSpace: 'pre-line' }}>
        {Array.isArray(processedContent) ? (
          processedContent.map((part, index) => (
            <React.Fragment key={index}>{part}</React.Fragment>
          ))
        ) : (
          processedContent
        )}
      </div>
    )
  }

  // Show toggle button only if references exist and it's not the latest response
  const shouldShowToggleButton = references && references.length > 0 && !isLatestResponse

  if (isError) {
    return (
      <div className={`response-content error-state ${fadeIn ? 'fade-in' : ''}`}>
        {heading && <div className="response-header">{heading}</div>}
        <div className="response-text error-text">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className={`response-content ${fadeIn ? 'fade-in' : ''}`}>
      {heading && <div className="response-header">{heading}</div>}
      <div ref={textRef} className="response-text">
        {isDataLoading ? (
          <SkeletonResponseContent />
        ) : (
          renderContent(content)
        )}
      </div>
      
      {!isDataLoading && (
        <>
          <div className="response-actions">
            <div className="tooltip-container">
              <button 
                onClick={handleCopy} 
                className={`action-button copy-button ${showCopySuccess ? 'success' : ''}`}
                aria-label="Copy to clipboard"
              >
                {showCopySuccess ? <Check size={20} /> : <Copy size={20} />}
              </button>
              <div className="tooltip">{copyTooltip}</div>
            </div>
            
            <div className="tooltip-container">
              <button
                onClick={handleReadAloud}
                className={`action-button read-aloud-button ${isSpeaking ? 'speaking' : ''}`}
                aria-label={isSpeaking ? 'Stop reading' : 'Read aloud'}
              >
                {isSpeaking ? <Square size={20} /> : <Volume2 size={20} />}
              </button>
              <div className="tooltip">{isSpeaking ? 'Stop reading' : 'Read aloud'}</div>
            </div>
            
            <div className="tooltip-container">
              <button
                onClick={handleThumbsUp}
                className={`action-button thumbs-button ${feedbackGiven === 'up' ? 'active' : ''}`}
                aria-label="Like this response"
                disabled={feedbackStatus === 'sending'}
              >
                <ThumbsUp size={20} />
              </button>
              <div className="tooltip">{feedbackGiven === 'up' ? 'Liked' : 'Like this response'}</div>
            </div>

            <div className="tooltip-container">
              <button
                onClick={handleThumbsDown}
                className={`action-button thumbs-button ${feedbackGiven === 'down' ? 'active' : ''}`}
                aria-label="Dislike this response"
                disabled={feedbackStatus === 'sending'}
              >
                <ThumbsDown size={20} />
              </button>
              <div className="tooltip">{feedbackGiven === 'down' ? 'Disliked' : 'Dislike this response'}</div>
            </div>
          </div>
          
          {shouldShowToggleButton && (
            <div className="references-toggle-container">
              <button 
                onClick={toggleReferences} 
                className="references-toggle-button"
                aria-label="Toggle references visibility"
              >
                <span>
                  {referencesVisible ? 'Hide References' : 'Show References'}
                </span>
                {referencesVisible ? <ChevronUp size={18} /> : <ChevronDown size={18} />} 
              </button>
            </div>
          )}
        </>
      )}
      
      {feedbackStatus === 'error' && (
        <div className="feedback-error-message">
          Failed to submit feedback. Please try again.
        </div>
      )}
    </div>
  )
}

export default ResponseContent