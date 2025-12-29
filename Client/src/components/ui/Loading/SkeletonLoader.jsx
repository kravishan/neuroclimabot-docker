import React from 'react'
import './SkeletonLoader.css'

export const SkeletonPulse = ({ className = '', style = {} }) => (
  <div className={`skeleton-pulse ${className}`} style={style}></div>
)

export const SkeletonTitle = () => (
  <div className="skeleton-title pulse" style={{ 
    width: '70%', 
    height: '32px',
    marginBottom: '8px',
    borderRadius: '6px'
  }}></div>
)

export const SkeletonParagraph = ({ lines = 3 }) => (
  <div className="skeleton-paragraph">
    {Array(lines).fill().map((_, i) => (
      <div 
        key={i} 
        className="skeleton-line pulse" 
        style={{ 
          width: i === lines - 1 ? `${Math.floor(Math.random() * 30) + 60}%` : `${Math.floor(Math.random() * 20) + 80}%`,
          height: '18px',
          marginBottom: '12px',
          borderRadius: '4px',
          animationDelay: `${i * 0.1}s`
        }}
      ></div>
    ))}
  </div>
)

export const SkeletonResponseContent = () => (
  <div className="skeleton-response">
    <div className="skeleton-response-header pulse" style={{
      width: '40%',
      height: '24px',
      marginBottom: '16px',
      borderRadius: '4px'
    }}></div>
    <SkeletonParagraph lines={5} />
    <div className="skeleton-actions" style={{
      display: 'flex',
      gap: '12px',
      marginTop: '20px'
    }}>
      {Array(4).fill().map((_, i) => (
        <div 
          key={i}
          className="skeleton-action-button pulse" 
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            animationDelay: `${i * 0.05}s`
          }}
        ></div>
      ))}
    </div>
  </div>
)

export const SkeletonReferences = ({ count = 3 }) => (
  <div className="skeleton-references">
    <div className="skeleton-references-header" style={{ 
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      marginBottom: '16px'
    }}>
      {/* Book icon skeleton */}
      <div className="pulse" style={{
        width: '20px',
        height: '20px',
        borderRadius: '4px'
      }}></div>
      {/* References title skeleton */}
      <div className="pulse" style={{ 
        width: '120px', 
        height: '18px',
        borderRadius: '4px'
      }}></div>
      {/* Count skeleton */}
      <div className="pulse" style={{ 
        width: '80px', 
        height: '14px',
        borderRadius: '4px',
        marginLeft: 'auto'
      }}></div>
    </div>
    <div className="skeleton-references-grid">
      {Array(count).fill().map((_, i) => (
        <div 
          key={i} 
          className="skeleton-reference-box"
          style={{ 
            height: '120px',
            borderRadius: '8px',
            border: '1px solid #eee',
            background: 'linear-gradient(145deg, #ecf5ee10, #defce50e)',
            position: 'relative',
            overflow: 'hidden',
            padding: '12px',
            animationDelay: `${i * 0.1}s`
          }}
        >
          {/* Reference header */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'flex-start',
            marginBottom: '8px',
            gap: '8px'
          }}>
            {/* Title skeleton */}
            <div className="pulse" style={{
              width: '70%',
              height: '16px',
              borderRadius: '4px'
            }}></div>
            {/* Score skeleton */}
            <div className="pulse" style={{
              width: '40px',
              height: '20px',
              borderRadius: '10px'
            }}></div>
          </div>
          
          {/* Document info skeleton */}
          <div className="pulse" style={{
            width: '85%',
            height: '14px',
            borderRadius: '4px',
            marginBottom: '8px'
          }}></div>
          <div className="pulse" style={{
            width: '60%',
            height: '14px',
            borderRadius: '4px'
          }}></div>
        </div>
      ))}
    </div>
  </div>
)

export const SkeletonPerspectives = () => (
  <div className="skeleton-perspectives">
    <div className="skeleton-perspectives-header pulse" style={{ 
      width: '180px', 
      height: '20px', 
      marginBottom: '16px', 
      marginLeft: '20px',
      borderRadius: '4px'
    }}></div>
    <div className="skeleton-perspective-item pulse" style={{ 
      height: '140px', 
      marginLeft: '20px',
      borderRadius: '8px',
      animationDelay: '0.2s'
    }}></div>
  </div>
)