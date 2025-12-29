import React, { useState, useEffect, useRef } from 'react'
import { Settings, X, Volume2, Clock, Mic } from 'lucide-react'
import './VoiceSettings.css'

const VoiceSettings = ({ isOpen, onClose, settings, onSettingsChange }) => {
  const [localSettings, setLocalSettings] = useState(settings)
  const settingsRef = useRef(null)

  useEffect(() => {
    setLocalSettings(settings)
  }, [settings])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (settingsRef.current && !settingsRef.current.contains(event.target)) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  const handleApplySettings = () => {
    onSettingsChange(localSettings)
    onClose()
  }

  const handleChange = (setting, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [setting]: value
    }))
  }

  if (!isOpen) return null

  return (
    <div className="settings-overlay">
      <div className="settings-panel" ref={settingsRef}>
        <div className="settings-header">
          <h3>Voice Settings</h3>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="settings-content">
          <div className="settings-section">
            <div className="settings-label">
              <Volume2 size={18} />
              <span>Voice Type</span>
            </div>
            <div className="settings-options">
              <button 
                className={`setting-option ${localSettings.voiceType === 'female' ? 'selected' : ''}`}
                onClick={() => handleChange('voiceType', 'female')}
              >
                Female (Nova)
              </button>
              <button 
                className={`setting-option ${localSettings.voiceType === 'male' ? 'selected' : ''}`}
                onClick={() => handleChange('voiceType', 'male')}
              >
                Male (Alloy)
              </button>
            </div>
          </div>

          <div className="settings-section">
            <div className="settings-label">
              <Clock size={18} />
              <span>Speaking Speed</span>
            </div>
            <div className="settings-slider">
              <input 
                type="range" 
                min="0.5" 
                max="1.5" 
                step="0.1" 
                value={localSettings.speakingSpeed} 
                onChange={(e) => handleChange('speakingSpeed', parseFloat(e.target.value))}
              />
              <div className="speed-value">{localSettings.speakingSpeed}x</div>
            </div>
          </div>

          <div className="settings-section">
            <div className="settings-label">
              <Mic size={18} />
              <span>Auto Listen Mode</span>
            </div>
            <div className="toggle-container">
              <label className="toggle">
                <input 
                  type="checkbox"
                  checked={localSettings.autoListen}
                  onChange={(e) => handleChange('autoListen', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button className="cancel-button" onClick={onClose}>Cancel</button>
          <button className="apply-button" onClick={handleApplySettings}>Apply</button>
        </div>
      </div>
    </div>
  )
}

export default VoiceSettings