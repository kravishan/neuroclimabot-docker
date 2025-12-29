import { useState, useCallback, useEffect } from 'react'
import { Send, Mic } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useSession } from '@/hooks/useSession'
import { FEATURE_FLAGS } from '@/constants/config'
import './ChatInput.css'

const ChatInput = ({ difficultyLevel = 'low', selectedLanguage = 'en' }) => {
  const { t } = useTranslation()
  const [input, setInput] = useState('')
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  
  const { endSession, isSessionActive } = useSession()

  useEffect(() => {
    document.getElementById('chat-textarea')?.focus()
  }, [])

  const handleInputChange = useCallback((e) => {
    const trimmedValue = e.target.value
    setInput(trimmedValue)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`
  }, [])

  const handleSubmit = useCallback(async () => {
    // If no input and voice model is disabled, do nothing
    if (!input.trim() && !FEATURE_FLAGS.VOICE_MODEL) {
      return
    }
    
    // If no input but voice model is enabled, navigate to voice model
    if (!input.trim() && FEATURE_FLAGS.VOICE_MODEL) {
      navigate('/voice-model')
      return
    }
    
    setError(null)

    try {
      if (isSessionActive) {
        console.log('Ending existing session before starting new conversation')
        await endSession()
      }

      navigate('/response/new', {
        state: {
          title: input,
          question: input,
          isLoading: true,
          difficultyLevel,
          selectedLanguage,
        },
      })

      setInput('')
    } catch (error) {
      console.error('Error ending previous session:', error)
      setError('Failed to start new conversation. Please try again.')
    }
  }, [input, navigate, difficultyLevel, selectedLanguage, endSession, isSessionActive])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Determine what icon to show and button behavior
  const showMicIcon = !input.trim() && FEATURE_FLAGS.VOICE_MODEL
  const showSendIcon = input.trim()
  const isButtonDisabled = !input.trim() && !FEATURE_FLAGS.VOICE_MODEL

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <textarea
          id="chat-textarea"
          className="chat-input"
          placeholder={t('askAnything')}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          aria-label="Chat input"
        />
        <button
          className="send-button"
          onClick={handleSubmit}
          disabled={isButtonDisabled}
          aria-label={
            showSendIcon 
              ? 'Send message' 
              : showMicIcon 
                ? 'Use voice input' 
                : 'Enter a message to send'
          }
          style={{
            opacity: isButtonDisabled ? 0 : 1,
            cursor: isButtonDisabled ? 'not-allowed' : 'pointer'
          }}
        >
          {showSendIcon ? (
            <Send size={20} className="send-icon" />
          ) : showMicIcon ? (
            <Mic size={20} className="mic-icon" />
          ) : (
            <Send size={20} className="send-icon" />
          )}
        </button>
      </div>
      {error && <p className="error-message">{error}</p>}
    </div>
  )
}

export default ChatInput