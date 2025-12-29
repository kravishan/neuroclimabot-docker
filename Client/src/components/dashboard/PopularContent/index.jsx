import React from 'react'
import { Search, FileText } from 'lucide-react'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const PopularContent = ({ queries, documents, isLoading }) => {
  const PopularCard = ({ title, data, type }) => (
    <div className="chart-card">
      <div className="chart-header">
        <h3>
          {type === 'queries' ? <Search size={16} /> : <FileText size={16} />}
          {title}
        </h3>
        <div className="chart-subtitle">Most {type === 'queries' ? 'searched' : 'referenced'} today</div>
      </div>
      <div className="docs-container">
        <div className="docs-list">
          {isLoading ? (
            <div className="doc-item">
              <div className="doc-rank">
                <LoadingSpinner size="small" />
              </div>
              <div className="doc-content">
                <div className="doc-title">Loading...</div>
                <div className="doc-references">--</div>
              </div>
            </div>
          ) : !data || data.length === 0 ? (
            <div className="doc-item">
              <div className="doc-rank">--</div>
              <div className="doc-content">
                <div className="doc-title">No data available</div>
                <div className="doc-references">No data</div>
              </div>
            </div>
          ) : (
            data.map((item, index) => {
              const count = item.count || item.reference_count || 0
              // For queries: use item.query, for documents: use item.document
              const title = type === 'queries'
                ? (item.query || `Query ${index + 1}`)
                : (item.document || item.title || item.doc_name || `Document ${index + 1}`)

              return (
                <div key={index} className="doc-item">
                  <div className="doc-rank">{index + 1}</div>
                  <div className="doc-content">
                    <div className="doc-title" title={title}>
                      {title}
                    </div>
                    <div className="doc-references">
                      {count.toLocaleString()} {type === 'queries' ?
                        (count === 1 ? 'search' : 'searches') :
                        (count === 1 ? 'reference' : 'references')
                      }
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="chart-grid single-chart">
      <PopularCard title="Popular Queries" data={queries} type="queries" />
      <PopularCard title="Popular Documents" data={documents} type="documents" />
    </div>
  )
}

export default PopularContent