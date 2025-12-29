import React, { useMemo } from 'react'
import { Cloud } from 'lucide-react'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const TrendingKeywords = ({ topics, isLoading }) => {
  const keywordsData = useMemo(() => {
    if (!topics || topics.length === 0) return []

    // Common stop words to filter out
    const stopWords = new Set([
      'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
      'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will',
      'with', 'have', 'this', 'or', 'but', 'not', 'all', 'can', 'had', 'her', 'his',
      'they', 'their', 'what', 'which', 'who', 'been', 'would', 'could', 'should',
      'up', 'degree', 'certain'
    ])

    const wordCounts = {}

    // Extract words from all topics
    topics.forEach(item => {
      const topicText = item.topic || ''
      const itemCount = item.count || 1

      // Split into words, clean, and filter
      const words = topicText
        .toLowerCase()
        .replace(/[^\w\s]/g, ' ') // Remove punctuation
        .split(/\s+/) // Split on whitespace
        .filter(word => {
          // Filter: must be 3+ characters and not a stop word
          return word.length >= 3 && !stopWords.has(word)
        })

      // Count each word
      words.forEach(word => {
        wordCounts[word] = (wordCounts[word] || 0) + itemCount
      })
    })

    // Convert to array and sort by count
    return Object.entries(wordCounts)
      .map(([keyword, count]) => ({ keyword, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 30) // Top 30 keywords
  }, [topics])

  const renderWordCloud = () => {
    if (isLoading) {
      return (
        <div className="word-cloud-loading">
          <LoadingSpinner size="medium" />
          <span>Loading keywords...</span>
        </div>
      )
    }

    if (keywordsData.length === 0) {
      return (
        <div className="word-cloud-fallback">
          <Cloud size={48} style={{ opacity: 0.5, color: '#3a7d45' }} />
          <span>No keywords data available</span>
        </div>
      )
    }

    const maxCount = Math.max(...keywordsData.map(item => item.count))
    const minCount = Math.min(...keywordsData.map(item => item.count))
    const sizeRange = { min: 14, max: 48 }

    return (
      <div className="word-cloud">
        {keywordsData.map((item, index) => {
          const normalizedSize = maxCount > minCount ?
            (item.count - minCount) / (maxCount - minCount) : 0.5
          const fontSize = sizeRange.min + (normalizedSize * (sizeRange.max - sizeRange.min))

          const colors = ['#3a7d45', '#2e6e39', '#4a8754', '#5a9764', '#6aa774']
          const colorIndex = Math.min(Math.floor(normalizedSize * colors.length), colors.length - 1)
          const color = colors[colorIndex]

          return (
            <span
              key={index}
              className="word-cloud-item"
              style={{
                fontSize: `${fontSize}px`,
                color: color,
                animationDelay: `${index * 0.05}s`
              }}
              title={`${item.keyword}: ${item.count} occurrences`}
              onClick={() => {
                console.log(`Keyword clicked: ${item.keyword} (${item.count} occurrences)`)
              }}
            >
              {item.keyword}
            </span>
          )
        })}
      </div>
    )
  }

  return (
    <div className="chart-grid single-chart">
      <div className="chart-card">
        <div className="chart-header">
          <h3>
            <Cloud size={16} />
            Keywords Cloud
          </h3>
          <div className="chart-subtitle">
            Most frequent keywords from trending topics
          </div>
        </div>
        <div className="word-cloud-container">
          {renderWordCloud()}
        </div>
      </div>
    </div>
  )
}

export default TrendingKeywords
