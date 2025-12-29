import React, { useState, useRef } from 'react'
import { Send } from 'lucide-react'
import './MessageInput.css'

const MessageInput = ({ onSendMessage, loading, t }) => {
  const [input, setInput] = useState('')
  const textareaRef = useRef(null)

  const handleInputChange = (e) => {
    setInput(e.target.value)
    
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`
    }
  }

  const resetTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = '48px' // Reset to initial height
    }
  }

  const handleSend = () => {
    if (input.trim() && !loading) {
      console.log('Continuing conversation with same session:', input.trim())
      onSendMessage(input)
      setInput('')
      
      // Reset textarea height after clearing input
      setTimeout(() => {
        resetTextareaHeight()
      }, 0)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-input-wrapper-continue">
      <textarea
        ref={textareaRef}
        className="chat-input"
        placeholder={t('askContinue')}
        value={input}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        disabled={loading}
        rows={1}
        style={{ minHeight: '48px', maxHeight: '128px' }}
      />
      <button 
        className="send-button" 
        disabled={loading || !input.trim()} 
        onClick={handleSend} 
        aria-label="Send message"
        title="Send message"
      >
        <Send size={20} className="send-icon" />
      </button>
    </div>
  )
}

export default MessageInput