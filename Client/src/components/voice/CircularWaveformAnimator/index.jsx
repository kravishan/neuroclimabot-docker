import React, { useState, useEffect, useRef } from 'react'
import './CircularWaveformAnimator.css'

const CircularWaveformAnimator = ({ state = 'idle', audioAnalyser = null }) => {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)
  const [points] = useState(180)
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height
    const centerX = width / 2
    const centerY = height / 2
    const baseRadius = Math.min(centerX, centerY) - 15
    
    let audioDataBuffer = null
    if (audioAnalyser) {
      audioDataBuffer = new Uint8Array(audioAnalyser.frequencyBinCount)
    }
    
    const animate = () => {
      ctx.clearRect(0, 0, width, height)
      
      const now = Date.now() / 1000
      
      if (state === 'talking' && audioAnalyser && audioDataBuffer) {
        audioAnalyser.getByteFrequencyData(audioDataBuffer)
      }
      
      switch(state) {
        case 'listening':
          drawListeningAnimation(ctx, centerX, centerY, baseRadius, now, points)
          break
        case 'thinking':
          drawThinkingAnimation(ctx, centerX, centerY, baseRadius, now, points)
          break
        case 'talking':
          drawTalkingAnimation(ctx, centerX, centerY, baseRadius, now, points, audioDataBuffer)
          break
        default:
          drawIdleAnimation(ctx, centerX, centerY, baseRadius, now, points)
      }
      
      animationRef.current = requestAnimationFrame(animate)
    }
    
    animate()
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [state, points, audioAnalyser])
  
  const drawIdleAnimation = (ctx, centerX, centerY, baseRadius, now, points) => {
    const canvas = canvasRef.current
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    const innerGradient = ctx.createRadialGradient(
      centerX, centerY, 0,
      centerX, centerY, baseRadius * 0.5
    )
    
    innerGradient.addColorStop(0, 'rgba(66, 133, 244, 0.2)')
    innerGradient.addColorStop(1, 'rgba(66, 133, 244, 0.05)')
    
    ctx.beginPath()
    ctx.arc(centerX, centerY, baseRadius * 0.4, 0, Math.PI * 2)
    ctx.fillStyle = innerGradient
    ctx.fill()
    
    ctx.beginPath()
    const breathFactor = 0.95 + Math.sin(now * 0.5) * 0.05
    const outerRadius = baseRadius * 0.85 * breathFactor
    
    ctx.arc(centerX, centerY, outerRadius, 0, Math.PI * 2)
    ctx.strokeStyle = 'rgba(66, 133, 244, 0.2)'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }
  
  const drawListeningAnimation = (ctx, centerX, centerY, baseRadius, now, points) => {
    // Similar implementation for listening state
    ctx.beginPath()
    ctx.arc(centerX, centerY, baseRadius * 0.6, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(76, 175, 80, 0.3)'
    ctx.fill()
  }
  
  const drawThinkingAnimation = (ctx, centerX, centerY, baseRadius, now, points) => {
    // Similar implementation for thinking state
    ctx.beginPath()
    ctx.arc(centerX, centerY, baseRadius * 0.5, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(255, 193, 7, 0.3)'
    ctx.fill()
  }
  
  const drawTalkingAnimation = (ctx, centerX, centerY, baseRadius, now, points, audioData = null) => {
    // Similar implementation for talking state
    ctx.beginPath()
    ctx.arc(centerX, centerY, baseRadius * 0.7, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(66, 133, 244, 0.4)'
    ctx.fill()
  }
  
  return (
    <canvas 
      ref={canvasRef} 
      width={300} 
      height={300} 
      className="circular-waveform-canvas"
    />
  )
}

export default CircularWaveformAnimator