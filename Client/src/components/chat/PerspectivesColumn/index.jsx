import React, { useCallback, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Compass, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react'
import { SkeletonPerspectives } from '@/components/ui/Loading/SkeletonLoader'
import './PerspectivesColumn.css'

const PerspectivesColumn = ({ 
  isDataLoading, 
  socialTippingPoint, 
  qualifyingFactors = [],
  fadeIn, 
  handleExplore, 
  skipHeader = false, 
  responseId,
  references = [],
  isWebSearch = false,
  expansionState,
  onExpansionChange
}) => {
  const { t } = useTranslation()

  const exploreHandler = useCallback(() => {
    if (isWebSearch) {
      console.warn('Exploration not available for web search results')
      return
    }
    
    if (handleExplore) {
      handleExplore(responseId, references)
    }
  }, [handleExplore, responseId, references, isWebSearch])

  if (isWebSearch) {
    return null
  }

  return (
    <div className="perspectives-column">
      {isDataLoading ? (
        <SkeletonPerspectives />
      ) : (
        <PerspectiveContent 
          fadeIn={fadeIn} 
          socialTippingPoint={socialTippingPoint}
          qualifyingFactors={qualifyingFactors}
          onExplore={exploreHandler} 
          skipHeader={skipHeader}
          references={references}
          isWebSearch={isWebSearch}
          responseId={responseId}
          expansionState={expansionState}
          onExpansionChange={onExpansionChange}
        />
      )}
    </div>
  )
}

const PerspectiveContent = ({ 
  fadeIn, 
  socialTippingPoint, 
  qualifyingFactors = [],
  onExplore, 
  skipHeader, 
  references = [],
  isWebSearch = false,
  responseId,
  expansionState = {},
  onExpansionChange
}) => {
  const { t } = useTranslation()
  
  // Use controlled state from parent if available, otherwise use local state
  const [localShowQualifyingFactors, setLocalShowQualifyingFactors] = useState(false)
  const [localIsExpanded, setLocalIsExpanded] = useState(false)

  // Determine which state to use
  const showQualifyingFactors = expansionState?.showQualifyingFactors ?? localShowQualifyingFactors
  const isExpanded = expansionState?.isExpanded ?? localIsExpanded

  // Reset local state when expansionState changes from parent
  useEffect(() => {
    if (expansionState) {
      setLocalShowQualifyingFactors(expansionState.showQualifyingFactors || false)
      setLocalIsExpanded(expansionState.isExpanded || false)
    }
  }, [expansionState])

  // Character limit for collapsing content
  const CHARACTER_LIMIT = 300

  if (isWebSearch) {
    return null
  }

  if (!socialTippingPoint || socialTippingPoint.trim() === '') {
    return null
  }

  const hasValidReferences = references && references.length > 0 && references.some(ref => ref.doc_name)
  const hasQualifyingFactors = qualifyingFactors && qualifyingFactors.length > 0
  
  // Check if content is too long
  const isContentLong = socialTippingPoint.length > CHARACTER_LIMIT
  const shouldTruncate = isContentLong && !isExpanded
  
  // Get display content
  const displayContent = shouldTruncate 
    ? socialTippingPoint.substring(0, CHARACTER_LIMIT) + '...'
    : socialTippingPoint

  const toggleQualifyingFactors = () => {
    const newValue = !showQualifyingFactors
    if (onExpansionChange) {
      onExpansionChange(responseId, {
        showQualifyingFactors: newValue,
        isExpanded: isExpanded
      })
    } else {
      setLocalShowQualifyingFactors(newValue)
    }
  }

  const toggleExpanded = () => {
    const newValue = !isExpanded
    if (onExpansionChange) {
      onExpansionChange(responseId, {
        showQualifyingFactors: showQualifyingFactors,
        isExpanded: newValue
      })
    } else {
      setLocalIsExpanded(newValue)
    }
  }

  return (
    <>
      <div className={`perspectives-line ${fadeIn ? 'fade-in' : ''}`}>
        <div className="perspective-item">
          <div className="perspective-title">
            <TrendingUp size={16} className="tipping-point-icon" />
            <span>{t('socialTippingPoints')}</span>
          </div>
          
          <div className="perspective-content">
            <div 
              className={`perspective-content-text ${isExpanded ? 'perspective-content-expanded' : ''}`}
              style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}
            >
              {displayContent}
            </div>
          </div>
          
          {/* Controls row with show more on left and qualifying factors on right */}
          {(isContentLong || hasQualifyingFactors) && (
            <div className="perspective-controls">
              {/* Show More/Less Button - Left Side */}
              {isContentLong && (
                <button
                  className="show-more-button"
                  onClick={toggleExpanded}
                  aria-expanded={isExpanded}
                >
                  <span className="show-more-text">
                    {isExpanded ? t('showLess') : t('showMore')}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={14} className="toggle-icon" />
                  ) : (
                    <ChevronDown size={14} className="toggle-icon" />
                  )}
                </button>
              )}
              
              {/* Empty div to push qualifying factors to the right if no show more button */}
              {!isContentLong && <div></div>}
              
              {/* Qualifying Factors Toggle - Right Side */}
              {hasQualifyingFactors && (
                <button
                  className="qualifying-factors-toggle"
                  onClick={toggleQualifyingFactors}
                  aria-expanded={showQualifyingFactors}
                >
                  <span className="toggle-text">
                    {t('qualifyingFactors')} ({qualifyingFactors.length})
                  </span>
                  {showQualifyingFactors ? (
                    <ChevronUp size={14} className="toggle-icon" />
                  ) : (
                    <ChevronDown size={14} className="toggle-icon" />
                  )}
                </button>
              )}
            </div>
          )}
          
          {/* Qualifying Factors List */}
          {showQualifyingFactors && hasQualifyingFactors && (
            <div className="qualifying-factors-list">
              {qualifyingFactors.map((factor, index) => (
                <div key={index} className="qualifying-factor-item">
                  <span className="factor-bullet">•</span>
                  <span className="factor-text">{factor}</span>
                </div>
              ))}
            </div>
          )}
          
          {hasValidReferences && (
            <button 
              className="explore-button scale-in" 
              onClick={onExplore} 
              aria-label={t('explore')} 
              title={t('explore')}
            >
              <Compass size={16} className="tipping-point-icon" />
              {t('explore')}
            </button>
          )}
        </div>
      </div>
    </>
  )
}

export default PerspectivesColumn