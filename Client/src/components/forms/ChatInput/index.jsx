import { useState, useCallback, useEffect } from 'react'
import { Send } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useSession } from '@/hooks/useSession'
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
    // If no input, do nothing
    if (!input.trim()) {
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

  // Button is disabled when there's no input
  const isButtonDisabled = !input.trim()

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
          aria-label="Send message"
          style={{
            opacity: isButtonDisabled ? 0.5 : 1,
            cursor: isButtonDisabled ? 'not-allowed' : 'pointer'
          }}
        >
          <Send size={20} className="send-icon" />
        </button>
      </div>
      {error && <p className="error-message">{error}</p>}
    </div>
  )
}

export default ChatInput