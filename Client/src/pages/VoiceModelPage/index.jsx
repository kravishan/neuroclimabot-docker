import React, { useState, useEffect, useRef } from 'react'
import { Mic, Settings } from 'lucide-react'
import VoiceSettings from '@/components/voice/VoiceSettings'
import CircularWaveformAnimator from '@/components/voice/CircularWaveformAnimator'
import RecordButtonWaveform from '@/components/voice/RecordButtonWaveform'
import './VoiceModelPage.css'

const VoiceModelPage = ({ isSettingsOpen, updateVoiceSettingsOpen }) => {
  const [voiceSettings, setVoiceSettings] = useState({
    voiceType: 'female',
    speakingSpeed: 1.0,
    autoListen: false
  })
  const [aiState, setAiState] = useState('idle') // idle, listening, thinking, talking
  const [isRecording, setIsRecording] = useState(false)
  const [audioAnalyser, setAudioAnalyser] = useState(null)

  const handleVoiceSettingsChange = (newSettings) => {
    setVoiceSettings(newSettings)
  }

  const handleCloseSettings = () => {
    updateVoiceSettingsOpen(false)
  }

  const handleStartRecording = () => {
    setIsRecording(true)
    setAiState('listening')
  }

  const handleStopRecording = () => {
    setIsRecording(false)
    setAiState('thinking')
    
    // Simulate processing
    setTimeout(() => {
      setAiState('talking')
      setTimeout(() => {
        setAiState('idle')
      }, 3000)
    }, 1000)
  }

  return (
    <div className="voice-model-container">
      <div className="visualizer-interface">
        <div className="animation-container">
          <div className={`ai-avatar ${aiState}`}>
            <div className="waveform-container">
              <CircularWaveformAnimator 
                state={aiState} 
                audioAnalyser={audioAnalyser} 
              />
            </div>
          </div>
        </div>

        <div className="ai-state-indicator">
          {aiState === 'idle' && 'Ready'}
          {aiState === 'listening' && 'Listening...'}
          {aiState === 'thinking' && 'Processing...'}
          {aiState === 'talking' && 'Speaking...'}
        </div>

        <div className="control-bar">
          <div className="record-button-container">
            <RecordButtonWaveform 
              isRecording={isRecording} 
              audioAnalyser={audioAnalyser} 
            />
            <button
              className={`record-button ${isRecording ? 'recording' : ''}`}
              onClick={isRecording ? handleStopRecording : handleStartRecording}
              disabled={aiState === 'thinking' || aiState === 'talking'}
            >
              <Mic size={24} />
            </button>
          </div>
        </div>
      </div>

      <VoiceSettings
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
        settings={voiceSettings}
        onSettingsChange={handleVoiceSettingsChange}
      />
    </div>
  )
}

export default VoiceModelPage