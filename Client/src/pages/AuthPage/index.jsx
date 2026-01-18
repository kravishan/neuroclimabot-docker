import React, { useState } from 'react'
import { Mail, Key, ArrowRight, Shield, CheckCircle, AlertCircle, Lock } from 'lucide-react'
import { authService } from '@/services/auth/authService'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import './AuthPage.css'

const AuthPage = ({ onAuthenticated }) => {
  const [activeTab, setActiveTab] = useState('request') // 'request' or 'enter'
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState({ type: '', content: '' })
  
  // Request token form state
  const [email, setEmail] = useState('')
  
  // Enter token form state
  const [token, setToken] = useState('')

  const handleRequestToken = async (e) => {
    e.preventDefault()
    
    if (!email.trim()) {
      setMessage({ type: 'error', content: 'Please enter your email address' })
      return
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email.trim())) {
      setMessage({ type: 'error', content: 'Please enter a valid email address' })
      return
    }

    setIsLoading(true)
    setMessage({ type: '', content: '' })

    try {
      const result = await authService.requestToken(email.trim())
      
      if (result.success) {
        setMessage({ 
          type: 'success', 
          content: result.message || 'Access token has been sent to your email. Please check your inbox and enter the token below.' 
        })
        setActiveTab('enter')
        setEmail('')
      } else {
        setMessage({ type: 'error', content: result.error })
      }
    } catch (error) {
      console.error('Error requesting token:', error)
      setMessage({ type: 'error', content: 'An unexpected error occurred. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleValidateToken = async (e) => {
    e.preventDefault()
    
    if (!token.trim()) {
      setMessage({ type: 'error', content: 'Please enter your access token.' })
      return
    }

    setIsLoading(true)
    setMessage({ type: '', content: '' })

    try {
      const result = await authService.validateToken(token.trim())
      
      if (result.success) {
        setMessage({ type: 'success', content: result.message })
        
        // Give user a moment to see the success message
        setTimeout(() => {
          onAuthenticated()
        }, 1000)
      } else {
        setMessage({ type: 'error', content: result.error })
      }
    } catch (error) {
      console.error('Error validating token:', error)
      setMessage({ type: 'error', content: 'An unexpected error occurred. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const clearMessage = () => {
    setMessage({ type: '', content: '' })
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        {/* Header */}
        <div className="auth-header">
          <h1 className="auth-title">Welcome to NeuroClima Bot</h1>
        </div>

        {/* Tab Navigation */}
        <div className="auth-tabs">
          <button 
            className={`auth-tab ${activeTab === 'request' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('request')
              clearMessage()
            }}
          >
            <Mail size={18} />
            Request Token
          </button>
          <button 
            className={`auth-tab ${activeTab === 'enter' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('enter')
              clearMessage()
            }}
          >
            <Key size={18} />
            Enter Token
          </button>
        </div>

        {/* Message Display */}
        {message.content && (
          <div className={`auth-message ${message.type}`}>
            {message.type === 'success' ? (
              <CheckCircle size={20} />
            ) : (
              <AlertCircle size={20} />
            )}
            <span>{message.content}</span>
          </div>
        )}

        {/* Request Token Form */}
        {activeTab === 'request' && (
          <div className="auth-form-container">
            <form onSubmit={handleRequestToken} className="auth-form">
              <div className="form-group-auth">
                <label htmlFor="email" className="form-label-auth">
                  <Mail size={16} />
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="form-input"
                  disabled={isLoading}
                  required
                />
              </div>

              <button 
                type="submit" 
                className="auth-submit-button"
                disabled={isLoading || !email.trim()}
              >
                {isLoading ? (
                  <LoadingSpinner size="small" text="" />
                ) : (
                  <>
                    <span>Send Access Token</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-info">
              <div className="info-item">
                <Shield size={16} />
                <span>We'll send a secure access token to your email</span>
              </div>
              <div className="info-item">
                <CheckCircle size={16} />
                <span>Token is valid for 7 days</span>
              </div>
              <div className="info-item">
                <Lock size={16} />
                <span>We only keep the token and never store your email</span>
              </div>
            </div>
          </div>
        )}

        {/* Enter Token Form */}
        {activeTab === 'enter' && (
          <div className="auth-form-container">
            <form onSubmit={handleValidateToken} className="auth-form">
              <div className="form-group-auth">
                <label htmlFor="token" className="form-label-auth">
                  <Key size={16} />
                  Access Token
                </label>
                <input
                  type="text"
                  id="token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste your access token here"
                  className="form-input token-input"
                  disabled={isLoading}
                  required
                />
              </div>

              <button 
                type="submit" 
                className="auth-submit-button"
                disabled={isLoading || !token.trim()}
              >
                {isLoading ? (
                  <LoadingSpinner size="small" text="" />
                ) : (
                  <>
                    <span>Validate Token</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-info">
              <p className="auth-text-info">Enter the token you received via email</p>
              <p className="auth-text-info">Your token will be saved in your browser</p>
              <div className="info-item">
                <Lock size={16} />
                <span>We only keep the token and never store your email</span>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="auth-footer">
          <p className="auth-footer-text">
            Need help? Contact us at{' '}
            <a href="mailto:info@bot.neuroclima.eu" className="auth-footer-link">
              info@bot.neuroclima.eu
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthPage