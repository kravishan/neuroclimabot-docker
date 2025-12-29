import React, { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import ForceGraph2D from 'react-force-graph-2d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'
import {
  ZoomIn, ZoomOut, RotateCcw, Maximize2, Eye, EyeOff,
  Minimize2, Info, Activity, Database,
  BarChart3, Layers
} from 'lucide-react'
import './KnowledgeGraph.css'

const KnowledgeGraph = ({ data }) => {
  const fgRef = useRef()
  const containerRef = useRef()
  const [selectedNode, setSelectedNode] = useState(null)
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [highlightLinks, setHighlightLinks] = useState(new Set())
  const [hoverNode, setHoverNode] = useState(null)
  const [showLabels, setShowLabels] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [showInfoPanel, setShowInfoPanel] = useState(true)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [renderKey, setRenderKey] = useState(0)
  const [is3D, setIs3D] = useState(false)
  const [buttonTooltip, setButtonTooltip] = useState({ show: false, text: '', x: 0, y: 0 })
  
  // GraphRAG optimized configuration
  const [graphConfig, setGraphConfig] = useState({
    showParticles: true,
    enablePhysics: true,
    nodeSize: 1.0,
    linkWidth: 1.0,
    linkDistance: 250,
    particleSpeed: 0.001,
    colorByType: true,
    showCommunities: true
  })

  const [initialPositions, setInitialPositions] = useState(new Map())
  const [hasInitialized, setHasInitialized] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)

  // GraphRAG specific color mapping
  const getNodeColor = useCallback((node) => {
    if (node.color && graphConfig.colorByType) return node.color
    
    if (node.entityType) {
      const typeStr = node.entityType.toLowerCase()
      if (typeStr.includes('person')) return '#FF6B6B'
      if (typeStr.includes('organization')) return '#4ECDC4'
      if (typeStr.includes('location') || typeStr.includes('geo')) return '#45B7D1'
      if (typeStr.includes('concept') || typeStr.includes('method')) return '#9b59b6'
      if (typeStr.includes('technology')) return '#FF9F43'
      if (typeStr.includes('research')) return '#F7DC6F'
      if (typeStr.includes('system')) return '#6C5CE7'
      if (typeStr.includes('event')) return '#1abc9c'
    }
    
    // Also check the 'type' field
    if (node.type) {
      const typeStr = node.type.toLowerCase()
      if (typeStr.includes('person')) return '#FF6B6B'
      if (typeStr.includes('organization')) return '#4ECDC4'
      if (typeStr.includes('geo')) return '#45B7D1'
      if (typeStr.includes('event')) return '#1abc9c'
      if (typeStr.includes('research')) return '#F7DC6F'
    }
    
    const colorMap = {
      1: '#FF9F43', 2: '#FF6B6B', 3: '#74b9ff', 4: '#4ECDC4', 
      5: '#45B7D1', 6: '#9b59b6', 7: '#F7DC6F', 8: '#6C5CE7'
    }
    return colorMap[node.group] || '#BDC3C7' // Default gray
  }, [graphConfig.colorByType])

  // Helper function to get color for entity type (for legend)
  const getColorForEntityType = useCallback((entityType) => {
    const typeStr = (entityType || '').toLowerCase()
    if (typeStr.includes('person')) return '#FF6B6B'
    if (typeStr.includes('organization')) return '#4ECDC4'
    if (typeStr.includes('geo') || typeStr.includes('location')) return '#45B7D1'
    if (typeStr.includes('event')) return '#1abc9c'
    if (typeStr.includes('research')) return '#F7DC6F'
    if (typeStr.includes('technology')) return '#FF9F43'
    if (typeStr.includes('system')) return '#6C5CE7'
    if (typeStr === 'none' || typeStr === '') return '#BDC3C7'
    return '#74b9ff' // Default for other types
  }, [])

  const getLinkColor = useCallback((link) => {
    const type = (link.type || '').toUpperCase()
    if (type.includes('RELATED')) return '#74b7ff'
    if (type.includes('PART_OF')) return '#27ae60'
    if (type.includes('LOCATED_IN')) return '#f39c12'
    if (type.includes('WORKS_FOR')) return '#3498db'
    if (type.includes('MENTIONS')) return '#e74c3c'
    if (type.includes('SEMANTIC')) return '#95A5A6'
    if (type.includes('CONNECTED')) return '#BDC3C7'
    return link.color || '#ddd'
  }, [])

  // Process GraphRAG data
  const processedData = React.useMemo(() => {
    if (!data || !data.nodes || !data.links) {
      return { nodes: [], links: [] }
    }

    console.log('Processing GraphRAG data:', data)

    const nodes = data.nodes.map(node => {
      const savedPosition = initialPositions.get(node.id)
      
      // Clean description by removing quotes
      const cleanDescription = node.description ? node.description.replace(/^["']|["']$/g, '') : ''
      
      return {
        ...node,
        size: Math.max(5, (node.size || node.val || node.degree || 10) * graphConfig.nodeSize),
        color: getNodeColor(node),
        opacity: 0.9,
        x: savedPosition?.x,
        y: savedPosition?.y,
        z: is3D ? (savedPosition?.z || 0) : undefined,
        fx: undefined, fy: undefined, fz: undefined,
        label: node.name,
        val: node.val || node.size || node.degree || 10,
        description: cleanDescription, // Use cleaned description
        // GraphRAG fields
        degree: node.degree || 0,
        rank: node.rank || 0
      }
    })

    const links = data.links.map(link => {
      // Clean link description by removing quotes
      const cleanDescription = link.description ? link.description.replace(/^["']|["']$/g, '') : ''
      
      return {
        ...link,
        width: Math.max(0.5, (link.value || link.strength || 1) * graphConfig.linkWidth),
        particles: graphConfig.showParticles ? Math.max(1, (link.value || 1) * 2) : 0,
        particleSpeed: graphConfig.particleSpeed,
        color: getLinkColor(link),
        opacity: 0.6,
        description: cleanDescription // Use cleaned description
      }
    })

    return { nodes, links }
  }, [data, graphConfig, getNodeColor, getLinkColor, is3D, initialPositions])

  // Calculate enhanced statistics with entity type breakdown
  const graphStats = React.useMemo(() => {
    if (!data || !processedData.nodes.length) return null

    // Calculate entity types from nodes
    const nodeEntityTypes = {}
    processedData.nodes.forEach(node => {
      const type = node.type || node.entityType || 'Unknown'
      nodeEntityTypes[type] = (nodeEntityTypes[type] || 0) + 1
    })

    const relationshipTypes = {}
    processedData.links.forEach(link => {
      const type = link.type || 'RELATED'
      relationshipTypes[type] = (relationshipTypes[type] || 0) + 1
    })

    const avgDegree = processedData.nodes.reduce((sum, node) => sum + (node.degree || 0), 0) / processedData.nodes.length
    const maxRank = Math.max(...processedData.nodes.map(node => node.rank || 0))
    const minRank = Math.min(...processedData.nodes.map(node => node.rank || 0))

    return {
      totalNodes: processedData.nodes.length,
      totalLinks: processedData.links.length,
      totalCommunities: data.communities?.length || 0,
      entityTypes: nodeEntityTypes,
      relationshipTypes,
      avgDegree: avgDegree.toFixed(2),
      rankRange: { min: minRank.toFixed(3), max: maxRank.toFixed(3) },
      density: (2 * processedData.links.length / (processedData.nodes.length * (processedData.nodes.length - 1))).toFixed(4),
      // Enhanced processing stats
      linksGenerated: data.stats?.links_generated || 0,
      originalNodes: data.stats?.original_nodes || processedData.nodes.length,
      originalLinks: data.stats?.original_links || 0,
      enhancementApplied: data.stats?.processing_info?.enhancement_applied || false,
      metadata: data.metadata || {}
    }
  }, [data, processedData])

  // Force update function
  const updateForces = useCallback(() => {
    if (fgRef.current && processedData.nodes.length > 0) {
      const fg = fgRef.current
      
      try {
        const linkForce = fg.d3Force('link')
        if (linkForce) {
          linkForce.distance(graphConfig.linkDistance)
        }
        
        const chargeForce = fg.d3Force('charge')
        if (chargeForce) {
          chargeForce
            .strength(-200)
            .distanceMax(Math.max(400, graphConfig.linkDistance * 2))
        }
        
        const simulation = fg.d3Force('simulation')
        if (simulation) {
          simulation.alpha(0.6).alphaDecay(0.015).restart()
        }
        
      } catch (error) {
        console.error('Error updating forces:', error)
      }
    }
  }, [graphConfig.linkDistance, processedData.nodes.length])

  // Button tooltip handlers
  const showTooltip = useCallback((e, text) => {
    const rect = e.target.getBoundingClientRect()
    setButtonTooltip({
      show: true, text,
      x: rect.left + rect.width / 2,
      y: rect.top - 10
    })
  }, [])

  const hideTooltip = useCallback(() => {
    setButtonTooltip({ show: false, text: '', x: 0, y: 0 })
  }, [])

  // Update forces when configuration changes
  useEffect(() => {
    if (fgRef.current && processedData.nodes.length > 0 && !isInitialLoad) {
      const timer = setTimeout(updateForces, 300)
      return () => clearTimeout(timer)
    }
  }, [updateForces, isInitialLoad])

  // Handle physics toggle
  useEffect(() => {
    if (fgRef.current && processedData.nodes.length > 0) {
      const fg = fgRef.current
      
      try {
        const simulation = fg.d3Force('simulation')
        if (simulation) {
          if (graphConfig.enablePhysics) {
            simulation.alpha(0.3).alphaDecay(0.02).restart()
          } else {
            simulation.alpha(0).stop()
          }
        }
      } catch (error) {
        console.error('Error toggling physics:', error)
      }
    }
  }, [graphConfig.enablePhysics, processedData.nodes.length])

  // Capture initial positions
  useEffect(() => {
    if (!hasInitialized && fgRef.current && processedData.nodes.length > 0 && !is3D) {
      const timer = setTimeout(() => {
        const positions = new Map()
        processedData.nodes.forEach(node => {
          if (node.x !== undefined && node.y !== undefined) {
            positions.set(node.id, { x: node.x, y: node.y, z: 0 })
          }
        })
        setInitialPositions(positions)
        setHasInitialized(true)
        
        setTimeout(() => {
          setIsInitialLoad(false)
        }, 1000)
      }, 500)
      
      return () => clearTimeout(timer)
    }
  }, [hasInitialized, processedData.nodes, is3D])

  // Handle mode switch physics restart
  useEffect(() => {
    if (fgRef.current && hasInitialized && processedData.nodes.length > 0 && !isInitialLoad) {
      const timer = setTimeout(() => {
        const fg = fgRef.current
        try {
          const simulation = fg.d3Force('simulation')
          if (simulation) {
            simulation.alpha(0.5).alphaDecay(0.02).restart()
          }
        } catch (error) {
          console.error('Error restarting physics:', error)
        }
      }, 100)
      
      return () => clearTimeout(timer)
    }
  }, [is3D, hasInitialized, processedData.nodes.length, isInitialLoad])

  // Re-render on mode switch
  useEffect(() => {
    setRenderKey(prev => prev + 1)
    setSelectedNode(null)
    setHighlightNodes(new Set())
    setHighlightLinks(new Set())
  }, [is3D])

  // Handle window resize and fullscreen
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({
          width: isFullscreen ? window.innerWidth : rect.width,
          height: isFullscreen ? window.innerHeight : rect.height || 700
        })
      }
    }

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    document.addEventListener('fullscreenchange', handleFullscreenChange)

    return () => {
      window.removeEventListener('resize', updateDimensions)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
  }, [isFullscreen])

  // 3D node rendering with GraphRAG support
  const nodeThreeObject = useCallback((node) => {
    const group = new THREE.Group()
    
    const sphereGeometry = new THREE.SphereGeometry(node.size * 0.5, 16, 16)
    const sphereMaterial = new THREE.MeshPhongMaterial({
      color: node.color,
      transparent: true,
      opacity: node.opacity || 0.9,
      shininess: 30
    })
    const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial)
    group.add(sphere)

    // Enhanced highlighting for high-rank entities
    if (node.isPrimary || node.rank > 0.8) {
      const glowGeometry = new THREE.SphereGeometry(node.size * 0.7, 16, 16)
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: node.color,
        transparent: true,
        opacity: 0.3,
        side: THREE.BackSide
      })
      const glow = new THREE.Mesh(glowGeometry, glowMaterial)
      group.add(glow)
    }

    if (showLabels) {
      const sprite = new SpriteText(node.name || node.label)
      sprite.material.depthWrite = false
      sprite.color = '#ffffff'
      sprite.textHeight = Math.max(4, node.size * 0.3)
      sprite.backgroundColor = 'rgba(0,0,0,0.8)'
      sprite.padding = 2
      sprite.borderRadius = 4
      sprite.position.y = node.size * 0.8
      group.add(sprite)
    }

    return group
  }, [showLabels])

  // 2D node rendering with GraphRAG support
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const label = node.name || node.label
    const fontSize = 12/globalScale
    ctx.font = `${fontSize}px Inter, sans-serif`
    const textWidth = ctx.measureText(label).width
    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4)

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, node.size * 0.5, 0, 2 * Math.PI, false)
    ctx.fillStyle = node.color
    ctx.globalAlpha = node.opacity || 0.9
    ctx.fill()
    ctx.globalAlpha = 1

    // Enhanced highlighting for high-rank entities
    if (node.isPrimary || node.rank > 0.8) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.size * 0.7, 0, 2 * Math.PI, false)
      ctx.fillStyle = node.color + '40'
      ctx.fill()
    }

    // Always show labels in 2D mode when enabled
    if (showLabels && !is3D) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
      ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2 + node.size * 0.8, ...bckgDimensions)

      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, node.x, node.y + node.size * 0.8)
    } else if (showLabels && is3D && globalScale > 1) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
      ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2 + node.size * 0.8, ...bckgDimensions)

      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, node.x, node.y + node.size * 0.8)
    }
  }, [showLabels, is3D])

  // Enhanced node interaction for GraphRAG
  const handleNodeClick = useCallback((node, event) => {
    console.log('Node clicked:', node)
    setSelectedNode(node)
    
    const connectedNodeIds = new Set()
    const connectedLinkIds = new Set()
    
    processedData.links.forEach(link => {
      if (link.source.id === node.id || link.target.id === node.id) {
        connectedLinkIds.add(link)
        connectedNodeIds.add(link.source.id === node.id ? link.target.id : link.source.id)
      }
    })
    
    setHighlightNodes(connectedNodeIds)
    setHighlightLinks(connectedLinkIds)

    if (fgRef.current) {
      if (is3D) {
        fgRef.current.cameraPosition(
          { x: node.x * 3, y: node.y * 3, z: node.z * 3 },
          { x: node.x, y: node.y, z: node.z },
          1500
        )
      } else {
        fgRef.current.centerAt(node.x, node.y, 1500)
        fgRef.current.zoom(3, 1500)
      }
    }
  }, [processedData.links, is3D])

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node)
  }, [])

  // Control functions
  const handleZoomIn = () => {
    if (fgRef.current) {
      if (is3D) {
        const currentPos = fgRef.current.cameraPosition()
        const distance = Math.sqrt(currentPos.x ** 2 + currentPos.y ** 2 + currentPos.z ** 2)
        const newDistance = distance * 0.7
        const ratio = newDistance / distance
        
        fgRef.current.cameraPosition({
          x: currentPos.x * ratio,
          y: currentPos.y * ratio,
          z: currentPos.z * ratio
        }, undefined, 500)
      } else {
        fgRef.current.zoom(fgRef.current.zoom() * 1.5, 500)
      }
    }
  }

  const handleZoomOut = () => {
    if (fgRef.current) {
      if (is3D) {
        const currentPos = fgRef.current.cameraPosition()
        const distance = Math.sqrt(currentPos.x ** 2 + currentPos.y ** 2 + currentPos.z ** 2)
        const newDistance = distance * 1.4
        const ratio = newDistance / distance
        
        fgRef.current.cameraPosition({
          x: currentPos.x * ratio,
          y: currentPos.y * ratio,
          z: currentPos.z * ratio
        }, undefined, 500)
      } else {
        fgRef.current.zoom(fgRef.current.zoom() * 0.7, 500)
      }
    }
  }

  const handleReset = useCallback(() => {
    if (fgRef.current) {
      if (is3D) {
        const cameraDistance = Math.max(800, graphConfig.linkDistance * 3) // Increased distance for 3D
        fgRef.current.cameraPosition(
          { x: 0, y: 0, z: cameraDistance }, 
          { x: 0, y: 0, z: 0 }, 
          1500
        )
      } else {
        fgRef.current.zoom(1, 1500)
        fgRef.current.centerAt(0, 0, 1500)
      }
      
      setSelectedNode(null)
      setHighlightNodes(new Set())
      setHighlightLinks(new Set())
      
      if (!isInitialLoad) {
        setTimeout(updateForces, 100)
      }
    }
  }, [is3D, graphConfig.linkDistance, updateForces, isInitialLoad])

  const handleRestartPhysics = useCallback(() => {
    console.log('Manually restarting physics...')
    updateForces()
  }, [updateForces])

  const handleFullscreen = async () => {
    if (!document.fullscreenElement) {
      try {
        await containerRef.current.requestFullscreen()
      } catch (err) {
        console.error('Error attempting to enable fullscreen:', err)
      }
    } else {
      document.exitFullscreen()
    }
  }

  const handle2D3DToggle = () => {
    const wasIn3D = is3D
    setIs3D(!is3D)

    // Reset view after toggling between 2D and 3D
    if (!isInitialLoad) {
      setTimeout(() => {
        console.log(`Auto-resetting view after ${wasIn3D ? '3D to 2D' : '2D to 3D'} switch`)
        handleReset()
      }, 500)
    }
  }

  // Initialize 3D scene
  useEffect(() => {
    if (is3D && fgRef.current && processedData.nodes.length > 0) {
      const scene = fgRef.current.scene()
      
      const existingLights = scene.children.filter(child => child.isLight)
      existingLights.forEach(light => scene.remove(light))
      
      const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
      scene.add(ambientLight)
      
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
      directionalLight.position.set(100, 100, 100)
      directionalLight.castShadow = true
      scene.add(directionalLight)
      
      const pointLight1 = new THREE.PointLight(0x4ecdc4, 0.3, 200)
      pointLight1.position.set(-100, -100, -100)
      scene.add(pointLight1)
      
      const pointLight2 = new THREE.PointLight(0xff6b6b, 0.3, 200)
      pointLight2.position.set(100, -100, 100)
      scene.add(pointLight2)

      scene.background = new THREE.Color(0x000511)
      scene.fog = new THREE.Fog(0x000511, 400, 2000)
    }
  }, [is3D, processedData])

  // Auto-hide controls in fullscreen
  useEffect(() => {
    let timeout
    if (isFullscreen) {
      const handleMouseMove = () => {
        setShowControls(true)
        clearTimeout(timeout)
        timeout = setTimeout(() => setShowControls(false), 3000)
      }

      document.addEventListener('mousemove', handleMouseMove)
      timeout = setTimeout(() => setShowControls(false), 3000)

      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        clearTimeout(timeout)
      }
    } else {
      setShowControls(true)
    }
  }, [isFullscreen])

  // Common graph props optimized for GraphRAG
  const commonProps = {
    ref: fgRef,
    graphData: processedData,
    width: dimensions.width,
    height: dimensions.height,
    backgroundColor: is3D ? "rgba(0,5,17,1)" : "#000511",
    
    nodeColor: node => node.color,
    nodeOpacity: node => node.opacity || 0.9,
    nodeVal: node => node.size,
    nodeLabel: node => `${node.name}: ${node.description || 'GraphRAG Entity'}`,
    
    linkColor: link => link.color,
    linkOpacity: 0.4,
    linkWidth: link => link.width || 1,
    linkDirectionalParticles: link => graphConfig.showParticles ? link.particles : 0,
    linkDirectionalParticleSpeed: graphConfig.particleSpeed,
    linkDirectionalParticleWidth: 2,
    linkDirectionalParticleColor: () => '#ffffff',
    
    d3AlphaDecay: graphConfig.enablePhysics ? 0.015 : 0,
    d3VelocityDecay: 0.3,
    d3Force: {
      charge: { 
        strength: is3D ? -800 : -300, // Increased repulsion for 3D mode
        distanceMin: is3D ? 100 : 50,
        distanceMax: Math.max(is3D ? 1200 : 600, graphConfig.linkDistance * (is3D ? 3 : 2))
      },
      link: { 
        distance: is3D ? graphConfig.linkDistance * 1.8 : graphConfig.linkDistance, // Increased link distance for 3D
        strength: is3D ? 0.1 : 0.2, // Reduced link strength for 3D to allow more spreading
        iterations: 2
      },
      collision: { 
        radius: node => (node.size || 10) + (is3D ? 40 : 20), // Increased collision radius for 3D
        strength: 1.2,
        iterations: 2
      },
      center: { x: 0, y: 0, z: is3D ? 0 : undefined, strength: 0.03 } // Weaker center force for 3D
    },
    
    onNodeClick: handleNodeClick,
    onNodeHover: handleNodeHover,
    onLinkHover: setHoverNode,
    
    enableNavigationControls: true,
    cooldownTicks: is3D ? 500 : 300, // More time for 3D to settle
    cooldownTime: 30000
  }

  return (
    <div 
      ref={containerRef}
      className={`knowledge-graph-container ${isFullscreen ? 'fullscreen-mode' : ''}`}
      style={{
        width: isFullscreen ? '100vw' : '100%',
        height: isFullscreen ? '100vh' : '700px',
        position: isFullscreen ? 'fixed' : 'relative',
        top: isFullscreen ? 0 : 'auto',
        left: isFullscreen ? 0 : 'auto',
        zIndex: isFullscreen ? 9999 : 'auto'
      }}
    >
      {/* Enhanced Controls */}
      <div className={`graph-controls-3d ${isFullscreen && !showControls ? 'hidden' : ''}`}>
        {/* Main Controls */}
        <div className="control-group">
          <button 
            className="control-button" 
            onClick={handleZoomIn} 
            onMouseEnter={(e) => showTooltip(e, 'Zoom In')}
            onMouseLeave={hideTooltip}
          >
            <ZoomIn size={18} />
          </button>
          <button 
            className="control-button" 
            onClick={handleZoomOut} 
            onMouseEnter={(e) => showTooltip(e, 'Zoom Out')}
            onMouseLeave={hideTooltip}
          >
            <ZoomOut size={18} />
          </button>
          <button 
            className="control-button" 
            onClick={handleReset} 
            onMouseEnter={(e) => showTooltip(e, 'Reset View')}
            onMouseLeave={hideTooltip}
          >
            <RotateCcw size={18} />
          </button>
          <button 
            className="control-button" 
            onClick={handleFullscreen} 
            onMouseEnter={(e) => showTooltip(e, isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen')}
            onMouseLeave={hideTooltip}
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
        
        {/* View Controls */}
        <div className="control-group">
          <button 
            className={`control-button ${showLabels ? 'active' : ''}`}
            onClick={() => setShowLabels(!showLabels)}
            onMouseEnter={(e) => showTooltip(e, showLabels ? 'Hide Labels' : 'Show Labels')}
            onMouseLeave={hideTooltip}
          >
            {showLabels ? <Eye size={18} /> : <EyeOff size={18} />}
          </button>
          
          <button 
            className={`control-button ${is3D ? 'active' : ''}`}
            onClick={handle2D3DToggle}
            onMouseEnter={(e) => showTooltip(e, `Switch to ${is3D ? '2D' : '3D'}`)}
            onMouseLeave={hideTooltip}
            style={{ fontSize: '12px', fontWeight: '700', minWidth: '45px', fontFamily: 'monospace' }}
          >
            {is3D ? '3D' : '2D'}
          </button>

          <button
            className={`control-button ${showInfoPanel ? 'active' : ''}`}
            onClick={() => setShowInfoPanel(!showInfoPanel)}
            onMouseEnter={(e) => showTooltip(e, 'Toggle Info Panel')}
            onMouseLeave={hideTooltip}
          >
            <Info size={18} />
          </button>
        </div>
      </div>

      {/* Enhanced Info Panel */}
      {showInfoPanel && !isFullscreen && (
        <div className="graph-legend-3d" style={{ top: '20px', right: '20px', minWidth: '300px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h4 className="legend-title">Graph Information</h4>
            <button 
              className="close-button"
              onClick={() => setShowInfoPanel(false)}
              style={{ background: 'none', border: 'none', color: '#ffffff', fontSize: '18px' }}
            >
              ×
            </button>
          </div>
          
          {/* Entity Types Breakdown */}
          {graphStats?.entityTypes && Object.keys(graphStats.entityTypes).length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                fontSize: '13px', 
                fontWeight: '600', 
                color: '#ffffff', 
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center'
              }}>
                <Database size={14} style={{ marginRight: '6px' }} />
                Entity Types ({Object.keys(graphStats.entityTypes).length})
              </div>
              <div style={{ fontSize: '12px', lineHeight: '1.6' }}>
                {Object.entries(graphStats.entityTypes)
                  .sort(([,a], [,b]) => b - a) // Sort by count descending
                  .map(([type, count]) => (
                  <div key={type} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '4px 0',
                    color: 'rgba(255,255,255,0.9)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* Color indicator */}
                      <div style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: getColorForEntityType(type),
                        border: '1px solid rgba(255,255,255,0.3)',
                        flexShrink: 0
                      }} />
                      <span style={{ 
                        color: type === 'Unknown' ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.9)',
                        textTransform: 'capitalize',
                        fontSize: '12px'
                      }}>
                        {type === 'Unknown' ? 'Unclassified' : type.toLowerCase()}
                      </span>
                    </div>
                    <span style={{ 
                      fontWeight: '600', 
                      color: '#4ecdc4',
                      fontFamily: 'monospace',
                      fontSize: '12px'
                    }}>
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Network Stats */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ 
              fontSize: '13px', 
              fontWeight: '600', 
              color: '#ffffff', 
              marginBottom: '8px',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Activity size={14} style={{ marginRight: '6px' }} />
              Network Overview
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
              <div style={{ color: 'rgba(255,255,255,0.8)' }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>Total:</span>
                <span style={{ color: '#4ecdc4', fontWeight: '600', marginLeft: '6px' }}>
                  {processedData.nodes.length}N
                </span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.8)' }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>Links:</span>
                <span style={{ color: '#4ecdc4', fontWeight: '600', marginLeft: '6px' }}>
                  {processedData.links.length}
                </span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.8)' }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>Communities:</span>
                <span style={{ color: '#4ecdc4', fontWeight: '600', marginLeft: '6px' }}>
                  {data?.communities?.length || 0}
                </span>
              </div>
              <div style={{ color: 'rgba(255,255,255,0.8)' }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>Mode:</span>
                <span style={{ color: '#4ecdc4', fontWeight: '600', marginLeft: '6px' }}>
                  {is3D ? '3D' : '2D'}
                </span>
              </div>
            </div>
          </div>

          {/* Enhanced Processing Information */}
          {graphStats?.linksGenerated > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ 
                fontSize: '13px', 
                fontWeight: '600', 
                color: '#ffffff', 
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center'
              }}>
                <Layers size={14} style={{ marginRight: '6px' }} />
                Enhancement Applied
              </div>
              <div style={{ fontSize: '12px', lineHeight: '1.6' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '4px 0',
                  color: 'rgba(255,255,255,0.9)'
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.6)' }}>Original Links:</span>
                  <span style={{ color: '#4ecdc4', fontWeight: '600' }}>
                    {graphStats.originalLinks}
                  </span>
                </div>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '4px 0',
                  color: 'rgba(255,255,255,0.9)'
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.6)' }}>Generated:</span>
                  <span style={{ color: '#FF9F43', fontWeight: '600' }}>
                    +{graphStats.linksGenerated}
                  </span>
                </div>
                <div style={{ 
                  fontSize: '11px', 
                  color: 'rgba(255,255,255,0.6)', 
                  marginTop: '8px',
                  padding: '6px 8px',
                  background: 'rgba(255,159,67,0.1)',
                  borderRadius: '4px',
                  border: '1px solid rgba(255,159,67,0.2)'
                }}>
                  Intelligent link generation applied for better connectivity
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Button Tooltip */}
      {buttonTooltip.show && (
        <div
          className="hover-tooltip-3d"
          style={{
            position: 'fixed',
            left: buttonTooltip.x,
            top: buttonTooltip.y,
            transform: 'translateX(-50%) translateY(-100%)',
            zIndex: 10001,
            maxWidth: '200px',
            fontSize: '12px',
            whiteSpace: 'nowrap',
            pointerEvents: 'none'
          }}
        >
          <div className="tooltip-content">
            <span>{buttonTooltip.text}</span>
          </div>
        </div>
      )}

      {/* Graph Rendering */}
      {is3D ? (
        <ForceGraph3D
          key={`3d-${renderKey}`}
          {...commonProps}
          nodeThreeObject={nodeThreeObject}
          nodeResolution={16}
          cameraPosition={{ 
            x: 0, 
            y: 0, 
            z: Math.max(800, graphConfig.linkDistance * 3) // Increased initial camera distance for 3D
          }}
          controlType="orbit"
          rendererConfig={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance"
          }}
        />
      ) : (
        <ForceGraph2D
          key={`2d-${renderKey}`}
          {...commonProps}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => 'after'}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          zoom={0.8}
          minZoom={0.1}
          maxZoom={20}
          cooldownTicks={300}
          cooldownTime={30000}
        />
      )}

      {/* Enhanced Node Details Panel */}
      {selectedNode && !isFullscreen && (
        <div className="node-details-3d" style={{ maxWidth: '380px' }}>
          <div className="node-header">
            <div 
              className="node-indicator"
              style={{ backgroundColor: selectedNode.color }}
            />
            <h3>{selectedNode.name}</h3>
            <button className="close-button" onClick={() => setSelectedNode(null)}>×</button>
          </div>
          
          {selectedNode.description && (
            <p className="node-description">{selectedNode.description}</p>
          )}
          
          <div className="node-metadata">
            <div className="metadata-item">
              <span className="label">Type:</span>
              <span className="value">{selectedNode.entityType || 'Entity'}</span>
            </div>
            
            {selectedNode.degree > 0 && (
              <div className="metadata-item">
                <span className="label">Connections:</span>
                <span className="value">{selectedNode.degree}</span>
              </div>
            )}
            
            {selectedNode.rank > 0 && (
              <div className="metadata-item">
                <span className="label">Rank:</span>
                <span className="value">{selectedNode.rank.toFixed(3)}</span>
              </div>
            )}

            <div className="metadata-item">
              <span className="label">View Mode:</span>
              <span className="value">{is3D ? '3D' : '2D'}</span>
            </div>
          </div>

          {/* Connected Entities Preview */}
          {highlightNodes.size > 0 && (
            <div style={{ marginTop: '12px', fontSize: '12px' }}>
              <strong>Connected to {highlightNodes.size} entities</strong>
              <div style={{ maxHeight: '60px', overflowY: 'auto', marginTop: '4px' }}>
                {Array.from(highlightNodes).slice(0, 5).map(nodeId => {
                  const connectedNode = processedData.nodes.find(n => n.id === nodeId)
                  return connectedNode ? (
                    <div key={nodeId} style={{ 
                      padding: '2px 0', 
                      color: 'rgba(255,255,255,0.8)',
                      fontSize: '11px'
                    }}>
                      • {connectedNode.name}
                    </div>
                  ) : null
                })}
                {highlightNodes.size > 5 && (
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '11px' }}>
                    +{highlightNodes.size - 5} more...
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Enhanced Hover Tooltip */}
      {hoverNode && (
        <div 
          className="hover-tooltip-3d"
          style={{
            position: 'absolute',
            bottom: '80px',
            left: '20px',
            zIndex: 10000,
            maxWidth: '320px',
            minWidth: '280px'
          }}
        >
          <div className="tooltip-content">
            <strong>{hoverNode.name}</strong>
            {hoverNode.description && (
              <p style={{ fontSize: '12px', marginTop: '4px' }}>{hoverNode.description.slice(0, 100)}...</p>
            )}
            <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255,255,255,0.8)' }}>
              <div>Type: {hoverNode.entityType || 'Unknown'}</div>
              {hoverNode.degree > 0 && <div>Connections: {hoverNode.degree}</div>}
              {hoverNode.rank > 0 && <div>Rank: {hoverNode.rank.toFixed(3)}</div>}
            </div>
            <small>GraphRAG Entity • {is3D ? '3D' : '2D'} Mode</small>
          </div>
        </div>
      )}
    </div>
  )
}

export default KnowledgeGraph