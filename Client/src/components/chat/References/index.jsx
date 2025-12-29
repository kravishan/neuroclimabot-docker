import React from 'react'
import { useTranslation } from 'react-i18next'
import { BookOpen } from 'lucide-react'
import { SkeletonReferences } from '@/components/ui/Loading/SkeletonLoader'
import './References.css'

const References = ({ 
  references, 
  isDataLoading, 
  fadeIn, 
  visible = true,
  mostRelevantCount, 
  totalRelevantDocuments
}) => {
  const { t } = useTranslation()

  if (!visible) return null
  if (isDataLoading) return <SkeletonReferences count={3} />
  if (references.length === 0) return null

  const relevantCount = mostRelevantCount !== undefined ? mostRelevantCount : references.length
  const totalCount = totalRelevantDocuments !== undefined ? totalRelevantDocuments : references.length

  return (
    <div className={`references-section ${fadeIn ? 'fade-in' : ''}`}>
      <div className="references-header">
        <BookOpen size={20} />
        <h4>{t('references')}</h4>
        <span className="references-count">
          {t('referencesCount', { count: relevantCount, total: totalCount })}
        </span>
      </div>

      <div className="references-grid">
        {references.map((ref, index) => (
          <ReferenceItem 
            key={index} 
            refData={ref} 
            index={index} 
            fadeIn={fadeIn}
          />
        ))}
      </div>
    </div>
  )
}

const ReferenceItem = ({ refData, index, fadeIn }) => {
  const title = refData.title || 'Unknown Document'
  const docName = refData.doc_name || refData.original_title || 'Unknown Document'
  const url = refData.url || '#'
  const similarityScore = refData.similarity_score || 0
  
  const isValidUrl = url && url !== '#' && !url.startsWith('#')
  const displayTitle = title.length > 40 ? title.substring(0, 37) + '...' : title
  
  const getDocumentInfo = () => {
    if (isValidUrl) {
      return `Source: ${docName}`
    } else {
      return `Document: ${docName}`
    }
  }

  const handleClick = () => {
    if (isValidUrl) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div
      className={`reference-box ${fadeIn ? 'scale-in' : ''} ${isValidUrl ? 'clickable' : ''}`}
      style={{ animationDelay: `${0.1 * index}s` }}
      onClick={isValidUrl ? handleClick : undefined}
      role={isValidUrl ? 'button' : 'article'}
      tabIndex={isValidUrl ? 0 : -1}
      onKeyDown={isValidUrl ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      } : undefined}
    >
      <div className="reference-header">
        <h5 aria-label={`Reference title: ${title}`}>
          {displayTitle}
        </h5>
        {similarityScore > 0 && (
          <span className="relevance-score" title={`Similarity: ${similarityScore}%`}>
            {Math.round(similarityScore)}%
          </span>
        )}
      </div>
      <p className="reference-document-info">
        {getDocumentInfo()}
      </p>
      {isValidUrl && (
        <div className="reference-click-hint">
          Click to view document
        </div>
      )}
    </div>
  )
}

export default References