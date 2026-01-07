import React, { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  Network,
  AlertCircle,
  Database,
  Layers,
  Link,
  Users,
  FileText,
  GitBranch,
  Search,
  Download,
  Filter,
  Info,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  BookOpen,
  Zap,
  HelpCircle,
  X
} from 'lucide-react'
import { fetchTippingPointsGraphByDocName } from '@/services/api/endpoints'
import KnowledgeGraph from '@/components/common/KnowledgeGraph'
import './ExplorePage.css'

const ExplorePage = () => {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [graphData, setGraphData] = useState(null)
  const [allData, setAllData] = useState(null) // Store entities, relationships, communities, claims, text_units
  const [error, setError] = useState(null)
  const [docName, setDocName] = useState('')
  const [fallbackDocName, setFallbackDocName] = useState('')
  const [activeTab, setActiveTab] = useState('graph') // graph, entities, relationships, communities, claims, texts
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(10)
  const [expandedCommunities, setExpandedCommunities] = useState(new Set())
  const [showInfoBanner, setShowInfoBanner] = useState(true)

  const hasFetchedData = useRef(false)

  useDocumentTitle('Knowledge Graph Exploration - NeuroClima Bot')

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search)
    const docNameParam = urlParams.get('docname')
    const fallbackParam = urlParams.get('fallback')

    if (docNameParam) {
      setDocName(decodeURIComponent(docNameParam))
      console.log('Doc name extracted from URL:', decodeURIComponent(docNameParam))

      if (fallbackParam) {
        setFallbackDocName(decodeURIComponent(fallbackParam))
        console.log('Fallback doc name extracted from URL:', decodeURIComponent(fallbackParam))
      }
    } else {
      setError('No document name provided. Please navigate from a response page.')
      setLoading(false)
    }
  }, [location.search])

  useEffect(() => {
    if (hasFetchedData.current || graphData !== null || !docName) {
      return
    }

    hasFetchedData.current = true

    async function fetchGraphData() {
      try {
        setLoading(true)
        console.log("Fetching GraphRAG data for doc_name:", docName)
        console.log("Fallback doc_name available:", fallbackDocName)

        let result = await fetchTippingPointsGraphByDocName(docName)

        console.log("GraphRAG API response:", result)

        // If first attempt failed and we have a fallback doc name, try with fallback
        if ((!result.success || !result.graph) && fallbackDocName) {
          console.log("First doc failed, trying fallback doc_name:", fallbackDocName)
          setDocName(fallbackDocName)

          result = await fetchTippingPointsGraphByDocName(fallbackDocName)

          console.log("Fallback GraphRAG API response:", result)
        }

        if (result.success && result.graph) {
          const transformedGraphData = transformEnhancedGraphRAGData(result.graph)

          // Check if the transformed data has any nodes
          if (!transformedGraphData.nodes || transformedGraphData.nodes.length === 0) {
            setError('Sorry, we don\'t have the knowledge graph data for this question.')
            setLoading(false)
            return
          }

          setGraphData(transformedGraphData)

          // Store all data for displaying in tabs
          const allDataObj = {
            entities: result.entities || [],
            relationships: result.relationships || [],
            communities: result.communities || [],
            claims: result.claims || [],
            community_reports: result.community_reports || [],
            metadata: result.metadata || {}
          }
          console.log('📊 All Data received:', allDataObj)
          console.log('📊 Entities count:', allDataObj.entities?.length || 0)
          console.log('📊 Relationships count:', allDataObj.relationships?.length || 0)
          console.log('📊 Communities count:', allDataObj.communities?.length || 0)
          console.log('📊 Claims count:', allDataObj.claims?.length || 0)
          console.log('📊 Community Reports count:', allDataObj.community_reports?.length || 0)
          setAllData(allDataObj)
        } else {
          setError(result.error || 'Failed to generate enhanced graph visualization')
        }

        setLoading(false)
      } catch (err) {
        console.error('Error fetching enhanced graph data:', err)

        // Try fallback if available
        if (fallbackDocName) {
          console.log("Error occurred, trying fallback doc_name:", fallbackDocName)
          try {
            setDocName(fallbackDocName)

            const fallbackResult = await fetchTippingPointsGraphByDocName(fallbackDocName)

            if (fallbackResult.success && fallbackResult.graph) {
              const transformedGraphData = transformEnhancedGraphRAGData(fallbackResult.graph)

              if (!transformedGraphData.nodes || transformedGraphData.nodes.length === 0) {
                setError('Sorry, we don\'t have the knowledge graph data for this question.')
                setLoading(false)
                return
              }

              setGraphData(transformedGraphData)

              const fallbackAllData = {
                entities: fallbackResult.entities || [],
                relationships: fallbackResult.relationships || [],
                communities: fallbackResult.communities || [],
                claims: fallbackResult.claims || [],
                community_reports: fallbackResult.community_reports || [],
                metadata: fallbackResult.metadata || {}
              }
              setAllData(fallbackAllData)

              setLoading(false)
              return
            }
          } catch (fallbackErr) {
            console.error('Fallback also failed:', fallbackErr)
          }
        }

        setError('Failed to load knowledge graph data from GraphRAG service')
        setLoading(false)
        hasFetchedData.current = false
      }
    }

    fetchGraphData()
  }, [docName, graphData, fallbackDocName])

  const transformEnhancedGraphRAGData = (enhancedGraphRAGData) => {
    try {
      console.log("Transforming GraphRAG data:", enhancedGraphRAGData)

      if (!enhancedGraphRAGData) {
        return {
          nodes: [],
          links: [],
          communities: [],
          stats: { entities: 0, relationships: 0, communities: 0, links_generated: 0 }
        }
      }

      // Transform nodes from GraphRAG format
      const nodes = (enhancedGraphRAGData.nodes || []).map((node, index) => {
        const cleanDescription = node.description ? node.description.replace(/^["']|["']$/g, '') : ''

        return {
          id: node.id || node.entity_id || index.toString(),
          name: node.name || node.title || `Node ${index}`,
          group: node.group || 3,
          size: Math.max(8, (node.size || node.val || node.degree || 1) * 2),
          description: cleanDescription,
          nodeType: node.type || node.entityType || 'Entity',
          entityType: node.entityType || node.type,
          mentionCount: node.degree || null,
          isPrimary: node.rank > 0.8 || false,
          color: node.color || '#74b9ff',
          degree: node.degree || 0,
          rank: node.rank || 0,
          val: node.val || node.size || 10
        }
      })

      // Transform links from GraphRAG format
      const links = (enhancedGraphRAGData.links || []).map((link, index) => {
        const cleanDescription = link.description ? link.description.replace(/^["']|["']$/g, '') : ''

        return {
          source: link.source,
          target: link.target,
          value: link.strength || link.value || link.weight || 1,
          type: link.type || link.relationship_type || 'RELATED',
          label: cleanDescription || link.label || '',
          color: link.color || '#999999',
          description: cleanDescription,
          strength: link.strength || link.value || 1
        }
      })

      // Enhanced statistics
      const stats = {
        entities: nodes.length,
        relationships: links.length,
        communities: (enhancedGraphRAGData.communities || []).length,
        links_generated: enhancedGraphRAGData.stats?.links_generated || 0
      }

      console.log("Enhanced transformation complete:", {
        nodes: nodes.length,
        links: links.length,
        linksGenerated: stats.links_generated
      })

      return {
        nodes,
        links,
        communities: enhancedGraphRAGData.communities || [],
        stats
      }

    } catch (error) {
      console.error('Error transforming GraphRAG data:', error)
      return {
        nodes: [],
        links: [],
        communities: [],
        stats: { entities: 0, relationships: 0, communities: 0, links_generated: 0 }
      }
    }
  }

  const handleCloseTab = () => {
    if (window.opener) {
      window.close()
    } else {
      navigate('/', { replace: true })
    }
  }

  const handleRetry = () => {
    hasFetchedData.current = false
    setError(null)
    setGraphData(null)
    setAllData(null)
    setLoading(true)
  }

  const convertToCSV = (data, headers) => {
    if (!data || data.length === 0) return ''

    // Create CSV header
    const csvHeaders = headers.join(',')

    // Create CSV rows
    const csvRows = data.map(item => {
      return headers.map(header => {
        let value = item[header.toLowerCase().replace(/ /g, '_')] || item[header] || ''
        // Handle nested objects and arrays
        if (typeof value === 'object' && value !== null) {
          value = Array.isArray(value) ? value.join('; ') : JSON.stringify(value)
        }
        // Escape quotes and wrap in quotes if contains comma
        value = String(value).replace(/"/g, '""')
        if (value.includes(',') || value.includes('\n') || value.includes('"')) {
          value = `"${value}"`
        }
        return value
      }).join(',')
    })

    return [csvHeaders, ...csvRows].join('\n')
  }

  const exportData = (type) => {
    if (!allData) return

    let csvContent = ''
    let filename = `${docName}_${type}.csv`

    switch (type) {
      case 'entities':
        const entitiesHeaders = ['Name', 'Type', 'Description']
        const entitiesData = (allData.entities || []).map(e => ({
          Name: e.name || '',
          Type: e.type || 'Unknown',
          Description: e.description || ''
        }))
        csvContent = convertToCSV(entitiesData, entitiesHeaders)
        break

      case 'relationships':
        const relationshipsHeaders = ['Source Entity', 'Relationship', 'Target Entity', 'Strength', 'Description']
        const relationshipsData = (allData.relationships || []).map(rel => {
          const sourceEntity = allData.entities?.find(e => e.id === rel.source)
          const targetEntity = allData.entities?.find(e => e.id === rel.target)
          return {
            'Source Entity': sourceEntity?.name || rel.source || '',
            'Relationship': rel.type || '',
            'Target Entity': targetEntity?.name || rel.target || '',
            'Strength': rel.value || rel.strength || 1,
            'Description': rel.description || ''
          }
        })
        csvContent = convertToCSV(relationshipsData, relationshipsHeaders)
        break

      case 'communities':
        const communitiesHeaders = ['Title', 'Size', 'Level', 'Summary', 'Members']
        const communitiesData = (allData.communities || []).map(c => ({
          Title: c.title || `Community ${c.human_readable_id || ''}`,
          Size: c.size || 0,
          Level: c.level ?? 0,
          Summary: c.summary || '',
          Members: c.entity_names ? c.entity_names.join('; ') : (c.member_entities || []).join('; ')
        }))
        csvContent = convertToCSV(communitiesData, communitiesHeaders)
        break

      case 'claims':
        const claimsHeaders = ['Description', 'Status', 'Type', 'Source Text']
        const claimsData = (allData.claims || []).map(c => ({
          Description: c.description || '',
          Status: c.status || 'Unknown',
          Type: c.type || 'CLAIM',
          'Source Text': c.source_text || ''
        }))
        csvContent = convertToCSV(claimsData, claimsHeaders)
        break

      case 'texts':
        const hasTextUnits = allData.text_units && allData.text_units.length > 0
        if (hasTextUnits) {
          const textsHeaders = ['Text', 'Tokens', 'Chunk ID']
          const textsData = (allData.text_units || []).map(t => ({
            Text: t.text || '',
            Tokens: t.n_tokens || 0,
            'Chunk ID': t.chunk_id || ''
          }))
          csvContent = convertToCSV(textsData, textsHeaders)
        } else {
          const reportsHeaders = ['Title', 'Summary', 'Rating']
          const reportsData = (allData.community_reports || []).map(r => ({
            Title: r.title || '',
            Summary: r.summary || r.full_content || r.text || '',
            Rating: r.rating || ''
          }))
          csvContent = convertToCSV(reportsData, reportsHeaders)
        }
        break

      case 'all':
        // Create a comprehensive report in text format
        filename = `${docName}_complete_report.txt`
        csvContent = `KNOWLEDGE GRAPH REPORT FOR: ${docName}\n`
        csvContent += `Generated on: ${new Date().toLocaleString()}\n`
        csvContent += `${'='.repeat(80)}\n\n`

        csvContent += `SUMMARY STATISTICS\n`
        csvContent += `${'='.repeat(80)}\n`
        csvContent += `Total Entities: ${allData.entities?.length || 0}\n`
        csvContent += `Total Relationships: ${allData.relationships?.length || 0}\n`
        csvContent += `Total Communities: ${allData.communities?.length || 0}\n`
        csvContent += `Total Claims: ${allData.claims?.length || 0}\n\n`

        // Add entities section
        if (allData.entities && allData.entities.length > 0) {
          csvContent += `\nENTITIES (${allData.entities.length})\n`
          csvContent += `${'='.repeat(80)}\n`
          allData.entities.forEach((entity, i) => {
            csvContent += `\n${i + 1}. ${entity.name}\n`
            csvContent += `   Type: ${entity.type || 'Unknown'}\n`
            if (entity.description) {
              csvContent += `   Description: ${entity.description}\n`
            }
          })
        }

        // Add relationships section
        if (allData.relationships && allData.relationships.length > 0) {
          csvContent += `\n\nRELATIONSHIPS (${allData.relationships.length})\n`
          csvContent += `${'='.repeat(80)}\n`
          allData.relationships.slice(0, 50).forEach((rel, i) => {
            const sourceEntity = allData.entities?.find(e => e.id === rel.source)
            const targetEntity = allData.entities?.find(e => e.id === rel.target)
            csvContent += `\n${i + 1}. ${sourceEntity?.name || rel.source} → ${targetEntity?.name || rel.target}\n`
            csvContent += `   Relationship: ${rel.description || rel.type || 'Related'}\n`
            csvContent += `   Strength: ${rel.value || rel.strength || 1}\n`
          })
          if (allData.relationships.length > 50) {
            csvContent += `\n... and ${allData.relationships.length - 50} more relationships\n`
          }
        }

        // Add communities section
        if (allData.communities && allData.communities.length > 0) {
          csvContent += `\n\nCOMMUNITIES (${allData.communities.length})\n`
          csvContent += `${'='.repeat(80)}\n`
          allData.communities.forEach((community, i) => {
            csvContent += `\n${i + 1}. ${community.title || `Community ${community.human_readable_id || i + 1}`}\n`
            csvContent += `   Size: ${community.size || 0} | Level: ${community.level ?? 0}\n`
            if (community.summary) {
              csvContent += `   Summary: ${community.summary}\n`
            }
            if (community.entity_names && community.entity_names.length > 0) {
              csvContent += `   Members: ${community.entity_names.slice(0, 10).join(', ')}`
              if (community.entity_names.length > 10) {
                csvContent += ` ... and ${community.entity_names.length - 10} more`
              }
              csvContent += `\n`
            }
          })
        }

        break
      default:
        return
    }

    // Create and download the file
    const blob = new Blob([csvContent], { type: type === 'all' ? 'text/plain;charset=utf-8' : 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const filterItems = (items, searchKey = 'name') => {
    if (!items) return []

    let filtered = items

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(item => {
        const searchValue = item[searchKey] || item.description || item.subject || item.text || ''
        return searchValue.toLowerCase().includes(searchTerm.toLowerCase())
      })
    }

    // Apply type filter for entities
    if (filterType !== 'all' && searchKey === 'name' && activeTab === 'entities') {
      filtered = filtered.filter(item => item.type === filterType)
    }

    return filtered
  }

  const paginateItems = (items) => {
    const startIndex = (currentPage - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    return items.slice(startIndex, endIndex)
  }

  const getTotalPages = (totalItems) => {
    return Math.ceil(totalItems / itemsPerPage)
  }

  const renderPagination = (totalItems) => {
    const totalPages = getTotalPages(totalItems)
    if (totalPages <= 1) return null

    return (
      <div className="pagination-container">
        <div className="pagination-info">
          Showing {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} items
        </div>
        <div className="pagination-controls">
          <button
            className="pagination-btn"
            onClick={() => setCurrentPage(1)}
            disabled={currentPage === 1}
          >
            First
          </button>
          <button
            className="pagination-btn"
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <div className="pagination-pages">
            {[...Array(totalPages)].map((_, idx) => {
              const pageNum = idx + 1
              // Show first, last, current, and adjacent pages
              if (
                pageNum === 1 ||
                pageNum === totalPages ||
                (pageNum >= currentPage - 1 && pageNum <= currentPage + 1)
              ) {
                return (
                  <button
                    key={pageNum}
                    className={`pagination-page ${currentPage === pageNum ? 'active' : ''}`}
                    onClick={() => setCurrentPage(pageNum)}
                  >
                    {pageNum}
                  </button>
                )
              } else if (pageNum === currentPage - 2 || pageNum === currentPage + 2) {
                return <span key={pageNum} className="pagination-ellipsis">...</span>
              }
              return null
            })}
          </div>
          <button
            className="pagination-btn"
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
          <button
            className="pagination-btn"
            onClick={() => setCurrentPage(totalPages)}
            disabled={currentPage === totalPages}
          >
            Last
          </button>
        </div>
        <div className="items-per-page">
          <label>Items per page:</label>
          <select
            value={itemsPerPage}
            onChange={(e) => {
              setItemsPerPage(Number(e.target.value))
              setCurrentPage(1)
            }}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>
    )
  }

  const getUniqueTypes = (entities) => {
    if (!entities) return []
    const types = [...new Set(entities.map(e => e.type).filter(Boolean))]
    return types
  }

  const toggleCommunityExpansion = (communityId) => {
    setExpandedCommunities(prev => {
      const newSet = new Set(prev)
      if (newSet.has(communityId)) {
        newSet.delete(communityId)
      } else {
        newSet.add(communityId)
      }
      return newSet
    })
  }

  const renderInfoBanner = () => {
    if (!showInfoBanner) return null

    return (
      <div className="info-banner">
        <div className="info-banner-header">
          <div className="info-banner-title">
            <HelpCircle size={24} className="info-icon" />
            <h3>Understanding Knowledge Graphs</h3>
          </div>
          <button
            className="info-banner-close"
            onClick={() => setShowInfoBanner(false)}
            aria-label="Close information banner"
          >
            <X size={20} />
          </button>
        </div>

        <div className="info-banner-content">
          <div className="info-section">
            <div className="info-section-header">
              <BookOpen size={18} className="section-icon" />
              <h4>What is a Knowledge Graph?</h4>
            </div>
            <p>
              A knowledge graph is a visual representation of information that shows how different concepts,
              entities, and ideas are connected. Think of it as a network map where nodes (circles) represent
              important entities like organizations, locations, or concepts, and links (lines) show the
              relationships between them.
            </p>
          </div>

          <div className="info-section">
            <div className="info-section-header">
              <Zap size={18} className="section-icon" />
              <h4>How Was This Data Extracted?</h4>
            </div>
            <p>
              This knowledge graph was automatically generated using <strong>GraphRAG</strong> (Graph Retrieval-Augmented Generation),
              an advanced AI technology that analyzes documents to identify key entities, their relationships,
              and community structures. The system intelligently extracts factual claims and organizes them
              into a structured, interconnected network of knowledge.
            </p>
          </div>

          <div className="info-section">
            <div className="info-section-header">
              <Lightbulb size={18} className="section-icon" />
              <h4>How to Use This Page</h4>
            </div>
            <div className="info-list">
              <div className="info-item">
                <Network size={16} />
                <span><strong>Graph Tab:</strong> Explore the interactive 3D visualization. Click and drag nodes, zoom in/out, and click on nodes to see details.</span>
              </div>
              <div className="info-item">
                <Layers size={16} />
                <span><strong>Entities Tab:</strong> Browse all extracted entities (people, places, concepts) with descriptions and types.</span>
              </div>
              <div className="info-item">
                <GitBranch size={16} />
                <span><strong>Relationships Tab:</strong> See how entities are connected and the strength of their relationships.</span>
              </div>
              <div className="info-item">
                <Users size={16} />
                <span><strong>Communities Tab:</strong> Discover groups of closely related entities that form thematic clusters.</span>
              </div>
              <div className="info-item">
                <FileText size={16} />
                <span><strong>Claims Tab:</strong> Review specific factual statements extracted from the source document.</span>
              </div>
              <div className="info-item">
                <Download size={16} />
                <span><strong>Export Data:</strong> Download any view as JSON for further analysis or integration with other tools.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const renderTabContent = () => {
    if (!allData) return null

    switch (activeTab) {
      case 'graph':
        return (
          <div className="graph-visualization-container">
            <KnowledgeGraph data={graphData} />
          </div>
        )

      case 'entities':
        const entities = filterItems(allData.entities || [], 'name')
        const paginatedEntities = paginateItems(entities)
        const entityTypes = getUniqueTypes(allData.entities || [])

        return (
          <div className="data-view-container">
            <div className="data-view-header">
              <div className="header-left">
                <h3><Layers size={20} /> Entities ({entities.length})</h3>
                <p className="subtitle">Knowledge graph entities extracted from the document</p>
              </div>
              <div className="header-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder="Search entities..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  />
                </div>
                <select
                  className="filter-select"
                  value={filterType}
                  onChange={(e) => { setFilterType(e.target.value); setCurrentPage(1); }}
                >
                  <option value="all">All Types</option>
                  {entityTypes.map(type => (
                    <option key={type} value={type}>{type || 'Unknown'}</option>
                  ))}
                </select>
                <button onClick={() => exportData('entities')} className="export-btn">
                  <Download size={16} /> Export
                </button>
              </div>
            </div>

            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedEntities.map((entity, idx) => (
                    <tr key={entity.id || entity.entity_id || idx}>
                      <td className="entity-name">{entity.name}</td>
                      <td>
                        <span className={`type-badge type-${(entity.type || 'unknown').toLowerCase()}`}>
                          {entity.type || 'Unknown'}
                        </span>
                      </td>
                      <td className="description-cell">{entity.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {renderPagination(entities.length)}
          </div>
        )

      case 'relationships':
        const relationships = filterItems(allData.relationships || [], 'description')
        const paginatedRelationships = paginateItems(relationships)

        return (
          <div className="data-view-container">
            <div className="data-view-header">
              <div className="header-left">
                <h3><GitBranch size={20} /> Relationships ({relationships.length})</h3>
                <p className="subtitle">Connections between entities in the knowledge graph</p>
              </div>
              <div className="header-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder="Search relationships..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  />
                </div>
                <button onClick={() => exportData('relationships')} className="export-btn">
                  <Download size={16} /> Export
                </button>
              </div>
            </div>

            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Source Entity</th>
                    <th>Relationship</th>
                    <th>Target Entity</th>
                    <th>Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRelationships.map((rel, idx) => {
                    // Look up source and target entity names from entities array
                    const sourceEntity = allData.entities?.find(e => e.id === rel.source)
                    const targetEntity = allData.entities?.find(e => e.id === rel.target)
                    const sourceName = sourceEntity?.name || rel.source
                    const targetName = targetEntity?.name || rel.target
                    const strength = rel.value || rel.strength || 1

                    return (
                      <tr key={rel.id || idx}>
                        <td className="entity-name">{sourceName}</td>
                        <td className="relationship-cell">
                          <Link size={14} className="link-icon" />
                          {rel.description || rel.type}
                        </td>
                        <td className="entity-name">{targetName}</td>
                        <td className="numeric-cell">
                          <div className="strength-bar">
                            <div
                              className="strength-fill"
                              style={{ width: `${Math.min(strength * 10, 100)}%` }}
                            />
                            <span>{strength}</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {renderPagination(relationships.length)}
          </div>
        )

      case 'communities':
        console.log('🔍 Rendering communities tab')
        console.log('🔍 allData:', allData)
        console.log('🔍 allData.communities:', allData?.communities)
        const communities = filterItems(allData.communities || [], 'title')
        console.log('🔍 Filtered communities:', communities)
        const paginatedCommunities = paginateItems(communities)
        console.log('🔍 Paginated communities:', paginatedCommunities)

        return (
          <div className="data-view-container">
            <div className="data-view-header">
              <div className="header-left">
                <h3><Users size={20} /> Communities ({communities.length})</h3>
                <p className="subtitle">Clustered groups of related entities</p>
              </div>
              <div className="header-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder="Search communities..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  />
                </div>
                <button onClick={() => exportData('communities')} className="export-btn">
                  <Download size={16} /> Export
                </button>
              </div>
            </div>

            {paginatedCommunities.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'rgba(255,255,255,0.6)' }}>
                <Users size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
                <p>No communities found.</p>
                <p style={{ fontSize: '12px', marginTop: '8px' }}>
                  Available communities in data: {allData?.communities?.length || 0}
                </p>
              </div>
            ) : (
              <div className="communities-grid">
                {paginatedCommunities.map((community, idx) => (
                <div key={community.id || community.community_id || idx} className="community-card">
                  <div className="community-header">
                    <h4>{community.title || `Community ${community.human_readable_id ?? idx}`}</h4>
                    <div className="community-meta">
                      <span className="rating">Size: {community.size || 0}</span>
                      <span className="level">Level: {community.level ?? 0}</span>
                    </div>
                  </div>

                  {community.summary && <p className="community-summary">{community.summary}</p>}

                  {/* Entity Names */}
                  {community.entity_names && community.entity_names.length > 0 && (
                    <div className="community-members">
                      <strong>Entities ({community.entity_names.length}):</strong>
                      <div className="members-list">
                        {(expandedCommunities.has(community.id || community.community_id || idx)
                          ? community.entity_names
                          : community.entity_names.slice(0, 5)
                        ).map((entityName, i) => (
                          <span key={i} className="member-tag">
                            {entityName}
                          </span>
                        ))}
                        {community.entity_names.length > 5 && (
                          <span
                            className="more-members clickable"
                            onClick={() => toggleCommunityExpansion(community.id || community.community_id || idx)}
                            style={{ cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            {expandedCommunities.has(community.id || community.community_id || idx)
                              ? 'Show less'
                              : `+${community.entity_names.length - 5} more`
                            }
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Legacy format support - member_entities */}
                  {!community.entity_names && community.member_entities && (
                    <div className="community-members">
                      <strong>Members ({community.member_count || community.member_entities.length}):</strong>
                      <div className="members-list">
                        {(expandedCommunities.has(community.id || community.community_id || idx)
                          ? community.member_entities
                          : community.member_entities.slice(0, 5)
                        ).map((entityId, i) => {
                          const entity = allData.entities?.find(e => e.entity_id === entityId)
                          return (
                            <span key={i} className="member-tag">
                              {entity?.name || entityId.substring(0, 8)}
                            </span>
                          )
                        })}
                        {community.member_entities.length > 5 && (
                          <span
                            className="more-members clickable"
                            onClick={() => toggleCommunityExpansion(community.id || community.community_id || idx)}
                            style={{ cursor: 'pointer', textDecoration: 'underline' }}
                          >
                            {expandedCommunities.has(community.id || community.community_id || idx)
                              ? 'Show less'
                              : `+${community.member_entities.length - 5} more`
                            }
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Relationship Details */}
                  {community.relationship_details && community.relationship_details.length > 0 && (
                    <div className="community-relationships" style={{ marginTop: '12px' }}>
                      <strong>Key Relationships ({community.relationship_details.length}):</strong>
                      <div style={{ fontSize: '11px', marginTop: '6px', color: 'rgba(0, 0, 0, 0.8)' }}>
                        {community.relationship_details.slice(0, 2).map((rel, i) => (
                          <div key={i} style={{ padding: '4px 0', borderLeft: '2px solid #4ecdc4', paddingLeft: '8px', marginBottom: '4px' }}>
                            <strong>{rel.source}</strong> → <strong>{rel.target}</strong>
                            <div style={{ fontSize: '10px', color: 'rgba(0, 0, 0, 0.6)', marginTop: '2px' }}>
                              {rel.description}
                            </div>
                          </div>
                        ))}
                        {community.relationship_details.length > 2 && (
                          <div style={{ fontSize: '10px', color: 'rgba(0, 0, 0, 0.6)' }}>
                            +{community.relationship_details.length - 2} more relationships
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Text Units Preview */}
                  {community.text_unit_texts && community.text_unit_texts.length > 0 && (
                    <div style={{ marginTop: '12px', fontSize: '11px' }}>
                      <strong>Source Context:</strong>
                      <div style={{
                        marginTop: '6px',
                        padding: '8px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '4px',
                        color: 'rgba(0, 0, 0, 0.7)',
                        fontSize: '10px',
                        fontStyle: 'italic'
                      }}>
                        "{community.text_unit_texts[0].substring(0, 120)}..."
                      </div>
                    </div>
                  )}

                  {/* Period */}
                  {community.period && (
                    <div style={{ marginTop: '12px', fontSize: '11px', color: 'rgba(0, 0, 0, 0.6)' }}>
                      Period: {community.period}
                    </div>
                  )}
                </div>
              ))}
              </div>
            )}

            {communities.length > 0 && renderPagination(communities.length)}
          </div>
        )

      case 'claims':
        const claims = filterItems(allData.claims || [], 'description')
        const paginatedClaims = paginateItems(claims)

        return (
          <div className="data-view-container">
            <div className="data-view-header">
              <div className="header-left">
                <h3><FileText size={20} /> Claims ({claims.length})</h3>
                <p className="subtitle">Factual claims extracted from the document</p>
              </div>
              <div className="header-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder="Search claims..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  />
                </div>
                <button onClick={() => exportData('claims')} className="export-btn">
                  <Download size={16} /> Export
                </button>
              </div>
            </div>

            <div className="claims-list">
              {paginatedClaims.map((claim, idx) => (
                <div key={claim.id || claim.claim_id || idx} className="claim-card">
                  <div className="claim-header">
                    <div className="claim-badges">
                      <span className={`status-badge status-${(claim.status || 'unknown').toLowerCase()}`}>
                        {claim.status || 'Unknown'}
                      </span>
                      <span className="type-badge">{claim.type || 'CLAIM'}</span>
                    </div>
                  </div>
                  <p className="claim-description">{claim.description}</p>
                  {claim.source_text && (
                    <div className="claim-source">
                      <FileText size={14} />
                      <em>"{claim.source_text}"</em>
                    </div>
                  )}
                  {claim.start_date && claim.end_date && (
                    <div className="claim-dates">
                      <span>Period: {new Date(claim.start_date).toLocaleDateString()} - {new Date(claim.end_date).toLocaleDateString()}</span>
                    </div>
                  )}
                  {claim.covariate_type && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>
                      Type: {claim.covariate_type}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {renderPagination(claims.length)}
          </div>
        )

      case 'texts':
        // Support both text_units (old format) and community_reports (new format)
        const hasTextUnits = allData.text_units && allData.text_units.length > 0
        const hasCommunityReports = allData.community_reports && allData.community_reports.length > 0
        const textData = hasTextUnits ? allData.text_units : (hasCommunityReports ? allData.community_reports : [])
        const textUnits = filterItems(textData, 'text')
        const paginatedTextUnits = paginateItems(textUnits)
        const dataType = hasTextUnits ? 'Text Units' : 'Community Reports'

        return (
          <div className="data-view-container">
            <div className="data-view-header">
              <div className="header-left">
                <h3><FileText size={20} /> {dataType} ({textUnits.length})</h3>
                <p className="subtitle">
                  {hasTextUnits ? 'Source text chunks from the document' : 'Community-level analysis reports'}
                </p>
              </div>
              <div className="header-actions">
                <div className="search-box">
                  <Search size={16} />
                  <input
                    type="text"
                    placeholder={`Search ${dataType.toLowerCase()}...`}
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  />
                </div>
                <button onClick={() => exportData('texts')} className="export-btn">
                  <Download size={16} /> Export
                </button>
              </div>
            </div>

            {hasTextUnits ? (
              <div className="text-units-list">
                {paginatedTextUnits.map((unit, idx) => (
                  <div key={unit.text_unit_id || idx} className="text-unit-card">
                    <div className="text-unit-header">
                      <span className="token-count">{unit.n_tokens} tokens</span>
                      {unit.chunk_id && <span className="chunk-id">Chunk: {unit.chunk_id}</span>}
                    </div>
                    <p className="text-content">{unit.text}</p>
                  </div>
                ))}
              </div>
            ) : hasCommunityReports ? (
              <div className="text-units-list">
                {paginatedTextUnits.map((report, idx) => (
                  <div key={report.id || report.community || idx} className="text-unit-card" style={{ marginBottom: '20px' }}>
                    <div className="text-unit-header">
                      <span className="token-count">Report #{idx + 1}</span>
                      {(report.community_id || report.community !== undefined) && (
                        <span className="chunk-id">Community: {report.community_id || report.community}</span>
                      )}
                    </div>
                    {report.title && (
                      <h4 style={{ marginTop: '12px', marginBottom: '12px', color: '#4ecdc4', fontSize: '16px', fontWeight: '600' }}>
                        {report.title}
                      </h4>
                    )}
                    {/* Display summary or full_content if available */}
                    {(report.summary || report.full_content || report.text) && (
                      <p className="text-content" style={{ marginBottom: '12px', color: 'rgba(0,0,0,0.85)' }}>
                        {report.summary || report.full_content || report.text}
                      </p>
                    )}
                    {/* Display findings if available */}
                    {report.findings && report.findings.length > 0 && (
                      <div style={{ marginTop: '12px' }}>
                        <strong style={{ fontSize: '13px', color: 'rgba(0,0,0,0.9)' }}>Key Findings:</strong>
                        <div style={{ marginTop: '8px' }}>
                          {report.findings.map((finding, findingIdx) => (
                            <div key={findingIdx} style={{
                              marginBottom: '12px',
                              paddingLeft: '12px',
                              borderLeft: '3px solid #4ecdc4',
                              fontSize: '12px'
                            }}>
                              <div style={{ fontWeight: '600', marginBottom: '4px', color: 'rgba(0,0,0,0.9)' }}>
                                {finding.summary}
                              </div>
                              <div style={{ color: 'rgba(0,0,0,0.75)', lineHeight: '1.5' }}>
                                {finding.explanation}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {report.rating && (
                      <div style={{ marginTop: '12px', fontSize: '11px', color: 'rgba(0,0,0,0.6)' }}>
                        Rating: {report.rating}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '40px', textAlign: 'center', color: 'rgba(255,255,255,0.6)' }}>
                <FileText size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
                <p>No text units or community reports available for this document.</p>
              </div>
            )}

            {textUnits.length > 0 && renderPagination(textUnits.length)}
          </div>
        )

      default:
        return null
    }
  }

  if (loading) {
    return (
      <div className="exploration-page">
        <div className="exploration-content">
          <div className="loading-container">
            <div className="loading-spinner">
              <div className="spinner"></div>
              <div className="loading-text">
                <h3>Generating Enhanced Knowledge Graph</h3>
                <p>Analyzing document relationships and extracting key concepts via GraphRAG...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="exploration-page error-state">
        <div className="exploration-content error-state">
          <div className="error-container">
            <AlertCircle size={48} />
            <h3>Unable to Generate Graph</h3>
            <p>{error}</p>
            <div className="error-actions">
              <button onClick={handleRetry} className="explore-retry-button">
                Try Again
              </button>
              <button onClick={handleCloseTab} className="explore-close-button">
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="exploration-page">
      <div className="graph-title-header">
        <div className="header-left-section">
          <Network size={18} />
          <span className="header-title">Knowledge Graph Exploration</span>
        </div>
        {docName && (
          <div className="doc-name-centered">
            <Database size={16} />
            {docName}
          </div>
        )}
        <div className="header-actions-group">
          <button
            onClick={() => setShowInfoBanner(!showInfoBanner)}
            className="help-btn"
            title="Show/Hide Knowledge Graph Guide"
          >
            <HelpCircle size={16} /> Help
          </button>
          <button onClick={() => exportData('all')} className="export-all-btn">
            <Download size={16} /> Export All Data
          </button>
        </div>
      </div>

      {renderInfoBanner()}

      <div className="tabs-container">
        <div className="tabs-header">
          <button
            className={`tab-button ${activeTab === 'graph' ? 'active' : ''}`}
            onClick={() => { setActiveTab('graph'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <Network size={16} />
            Graph
            <span className="tab-count">{graphData?.nodes?.length || 0}</span>
          </button>
          <button
            className={`tab-button ${activeTab === 'entities' ? 'active' : ''}`}
            onClick={() => { setActiveTab('entities'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <Layers size={16} />
            Entities
            <span className="tab-count">{allData?.entities?.length || 0}</span>
          </button>
          <button
            className={`tab-button ${activeTab === 'relationships' ? 'active' : ''}`}
            onClick={() => { setActiveTab('relationships'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <GitBranch size={16} />
            Relationships
            <span className="tab-count">{allData?.relationships?.length || 0}</span>
          </button>
          <button
            className={`tab-button ${activeTab === 'communities' ? 'active' : ''}`}
            onClick={() => { setActiveTab('communities'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <Users size={16} />
            Communities
            <span className="tab-count">{allData?.communities?.length || 0}</span>
          </button>
          <button
            className={`tab-button ${activeTab === 'claims' ? 'active' : ''}`}
            onClick={() => { setActiveTab('claims'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <FileText size={16} />
            Claims
            <span className="tab-count">{allData?.claims?.length || 0}</span>
          </button>
          <button
            className={`tab-button ${activeTab === 'texts' ? 'active' : ''}`}
            onClick={() => { setActiveTab('texts'); setSearchTerm(''); setFilterType('all'); setCurrentPage(1); }}
          >
            <FileText size={16} />
            {allData?.text_units?.length > 0 ? 'Text Units' : 'Reports'}
            <span className="tab-count">
              {(allData?.text_units?.length || allData?.community_reports?.length || 0)}
            </span>
          </button>
        </div>

        <div className="tab-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  )
}

export default ExplorePage
