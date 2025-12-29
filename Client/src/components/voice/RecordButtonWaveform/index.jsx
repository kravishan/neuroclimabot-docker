import React, { useState, useEffect, useRef, useCallback } from 'react'
import './RecordButtonWaveform.css'

const RecordButtonWaveform = ({ isRecording, audioAnalyser }) => {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)
  const audioDataRef = useRef(Array(40).fill(0))
  const [points] = useState(40)
  
  const processAudioData = useCallback((dataArray, pointCount) => {
    const sampleSize = Math.floor(dataArray.length / 4)
    const samples = dataArray.slice(0, sampleSize)
    
    const result = []
    const step = samples.length / pointCount
    
    for (let i = 0; i < pointCount; i++) {
      const startIdx = Math.floor(i * step)
      const endIdx = Math.floor((i + 1) * step)
      
      let sum = 0
      for (let j = startIdx; j < endIdx; j++) {
        sum += samples[j] || 0
      }
      
      const avg = sum / (endIdx - startIdx)
      result.push(0.2 + (avg / 255) * 0.8)
    }
    
    return result
  }, [])
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    
    const drawRecordingWaveform = () => {
      if (!canvas) return
      
      const width = canvas.width
      const height = canvas.height
      const centerX = width / 2
      const centerY = height / 2
      const buttonRadius = 32
      const maxRadius = 55
      
      ctx.clearRect(0, 0, width, height)
      
      if (isRecording && audioAnalyser) {
        const dataArray = new Uint8Array(audioAnalyser.frequencyBinCount)
        audioAnalyser.getByteFrequencyData(dataArray)
        audioDataRef.current = processAudioData(dataArray, points)
      }
      
      ctx.beginPath()
      
      for (let i = 0; i <= points; i++) {
        const angle = (i / points) * Math.PI * 2
        
        let amplitude = 0
        if (isRecording && audioDataRef.current.length > 0) {
          const dataIndex = i % points
          amplitude = buttonRadius + (audioDataRef.current[dataIndex] * (maxRadius - buttonRadius))
        } else {
          amplitude = buttonRadius + 5
        }
        
        const x = centerX + Math.cos(angle) * amplitude
        const y = centerY + Math.sin(angle) * amplitude
        
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      
      ctx.closePath()
      
      if (isRecording) {
        const gradient = ctx.createRadialGradient(
          centerX, centerY, buttonRadius - 5,
          centerX, centerY, maxRadius + 5
        )
        
        gradient.addColorStop(0, 'rgba(76, 175, 80, 0.6)')
        gradient.addColorStop(1, 'rgba(76, 175, 80, 0.1)')
        
        ctx.fillStyle = gradient
        ctx.fill()
        
        ctx.shadowColor = 'rgba(144, 207, 155, 0.89)'
        ctx.shadowBlur = 10
        ctx.strokeStyle = 'rgba(182, 233, 191, 0.5)'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.shadowBlur = 0
      } else {
        ctx.strokeStyle = 'rgba(58, 125, 69, 0.3)'
        ctx.lineWidth = 1
        ctx.stroke()
      }
      
      animationRef.current = requestAnimationFrame(drawRecordingWaveform)
    }
    
    drawRecordingWaveform()
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isRecording, points, processAudioData, audioAnalyser])
  
  return (
    <canvas 
      ref={canvasRef} 
      width={120} 
      height={120} 
      className="record-button-waveform"
    />
  )
}

export default RecordButtonWaveform