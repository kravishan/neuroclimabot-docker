import React from 'react'
import './LoadingSpinner.css'

const LoadingSpinner = ({ size = 'medium', text = 'Loading...', className = '' }) => {
  const sizeClass = `spinner-${size}`
  
  return (
    <div className={`loading-spinner ${className}`}>
      <div className={`spinner ${sizeClass}`}></div>
      {text && <span className="loading-text">{text}</span>}
    </div>
  )
}

export default LoadingSpinner