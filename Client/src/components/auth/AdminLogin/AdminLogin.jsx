import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  User,
  Lock,
  Shield,
  AlertTriangle,
  RefreshCw
} from 'lucide-react'
import { API_CONFIG } from '@/constants/config'
import './AdminLogin.css'

const AdminLogin = ({ onLoginSuccess }) => {
  const navigate = useNavigate()
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginLoading(true)
    setLoginError('')
    
    const formData = new FormData(e.target)
    const username = formData.get('username')
    const password = formData.get('password')

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      
      const result = await response.json()
      
      if (result.success) {
        sessionStorage.setItem('admin_authenticated', 'true')
        onLoginSuccess()
      } else {
        setLoginError(result.message || 'Invalid credentials. Please check your username and password.')
      }
    } catch (error) {
      setLoginError('Connection failed. Please check your network and try again.')
      console.error('Login error:', error)
    } finally {
      setLoginLoading(false)
    }
  }

  return (
    <div className="admin-login">
      <div className="login-container">
        <div className="login-header">
          <img 
            src="/assets/icons/favicon.png" 
            alt="NeuroClima Logo" 
            className="login-logo"
          />
          <h1>NeuroClima Bot Admin</h1>
          <p className="login-subtitle">
            Administrative Dashboard Access
          </p>
        </div>
        
        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <label>
              <User size={16} />
              Username
            </label>
            <input 
              type="text" 
              name="username" 
              placeholder="Enter your username"
              required 
              disabled={loginLoading}
            />
          </div>
          
          <div className="input-group">
            <label>
              <Lock size={16} />
              Password
            </label>
            <input 
              type="password" 
              name="password" 
              placeholder="Enter your password"
              required 
              disabled={loginLoading}
            />
          </div>
          
          {loginError && (
            <div className="login-error">
              <AlertTriangle size={16} />
              {loginError}
            </div>
          )}
          
          <button 
            type="submit" 
            className={`login-btn ${loginLoading ? 'loading' : ''}`}
            disabled={loginLoading}
          >
            {loginLoading ? (
              <>
                <RefreshCw size={16} />
                Authenticating...
              </>
            ) : (
              <>
                <Shield size={16} />
                Access Dashboard
              </>
            )}
          </button>
        </form>
        
        <div className="login-footer">
          <p>
            Secure administrative access for NeuroClima Bot system
            <br />
            <a href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
              Return to main application
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AdminLogin