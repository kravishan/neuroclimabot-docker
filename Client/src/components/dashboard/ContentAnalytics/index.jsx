import React from 'react'
import { Database, Globe } from 'lucide-react'
import './ContentAnalytics.css'

const ContentAnalytics = ({ data, isLoading }) => {
  // Extract source type and language data from stats
  const getSourceTypeData = () => {
    if (!data || !data.source_type) {
      return { types: [], total: 0 }
    }

    const sourceTypes = Object.entries(data.source_type)
    const total = Object.values(data.source_type).reduce((sum, count) => sum + count, 0)
    
    return { types: sourceTypes, total }
  }

  const getLanguageData = () => {
    if (!data || !data.language) {
      return { languages: [], total: 0 }
    }

    const languages = Object.entries(data.language)
    const total = Object.values(data.language).reduce((sum, count) => sum + count, 0)
    
    return { languages, total }
  }

  const sourceTypeData = getSourceTypeData()
  const languageData = getLanguageData()

  const getSourceTypeName = (type) => {
    const sourceTypeNames = {
      'rag': 'RAG Documents',
      'web': 'Web Sources'
    }
    return sourceTypeNames[type] || type
  }

  const getLanguageName = (lang) => {
    const languageNames = {
      'en': 'English',
      'it': 'Italian',
      'pt': 'Portuguese',
      'el': 'Greek'
    }
    return languageNames[lang] || lang
  }

  const SourceTypeCard = () => {
    if (isLoading) {
      return (
        <div className="stat-card compact-analytics">
          <div className="compact-metric">
            <div className="metric-header">
              <Database size={16} />
              <span>Source Types</span>
            </div>
            <div className="metric-value">Loading...</div>
          </div>
        </div>
      )
    }

    if (sourceTypeData.types.length === 0) {
      return (
        <div className="stat-card compact-analytics">
          <div className="compact-metric">
            <div className="metric-header">
              <Database size={16} />
              <span>Source Types</span>
            </div>
            <div className="metric-value">No data</div>
          </div>
        </div>
      )
    }

    const primarySource = sourceTypeData.types.reduce((max, current) => 
      current[1] > max[1] ? current : max
    )

    return (
      <div className="stat-card compact-analytics">
        <div className="compact-metric">
          <div className="metric-header">
            <Database size={16} />
            <span>Source Types</span>
          </div>
          <div className="metric-content">
            <div className="primary-source">
              <span className="primary-label">Primary:</span>
              <span className="primary-value">{getSourceTypeName(primarySource[0])}</span>
            </div>
            <div className="source-breakdown">
              {sourceTypeData.types.map(([type, count]) => {
                const percentage = sourceTypeData.total > 0 ? 
                  Math.round((count / sourceTypeData.total) * 100) : 0
                
                return (
                  <div key={type} className="source-item">
                    <span className="source-name">{getSourceTypeName(type)}</span>
                    <div className="source-bar">
                      <div 
                        className="source-fill" 
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="source-count">{count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    )
  }

  const LanguageCard = () => {
    if (isLoading) {
      return (
        <div className="stat-card compact-analytics">
          <div className="compact-metric">
            <div className="metric-header">
              <Globe size={16} />
              <span>Languages</span>
            </div>
            <div className="metric-value">Loading...</div>
          </div>
        </div>
      )
    }

    if (languageData.languages.length === 0) {
      return (
        <div className="stat-card compact-analytics">
          <div className="compact-metric">
            <div className="metric-header">
              <Globe size={16} />
              <span>Languages</span>
            </div>
            <div className="metric-value">No data</div>
          </div>
        </div>
      )
    }

    const primaryLanguage = languageData.languages.reduce((max, current) => 
      current[1] > max[1] ? current : max
    )

    return (
      <div className="stat-card compact-analytics">
        <div className="compact-metric">
          <div className="metric-header">
            <Globe size={16} />
            <span>Languages</span>
          </div>
          <div className="metric-content">
            <div className="primary-language">
              <span className="primary-label">Primary:</span>
              <span className="primary-value">{getLanguageName(primaryLanguage[0])}</span>
            </div>
            <div className="language-breakdown">
              {languageData.languages.map(([lang, count]) => {
                const percentage = languageData.total > 0 ? 
                  Math.round((count / languageData.total) * 100) : 0
                
                return (
                  <div key={lang} className="language-item">
                    <span className="language-name">{getLanguageName(lang)}</span>
                    <div className="language-bar">
                      <div 
                        className="language-fill" 
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="language-count">{count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="stats-grid content-stats">
      <SourceTypeCard />
      <LanguageCard />
    </div>
  )
}

export default ContentAnalytics