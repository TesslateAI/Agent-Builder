import React, { useCallback, useState, useEffect } from 'react';
import { useReactFlow } from 'reactflow';
import { Plus, Minus, Maximize2, Home, Shuffle } from 'lucide-react';
import { useStore } from '../store';
import { getLayoutedElements, LAYOUT_DIRECTIONS } from '../utils/autoLayout';

const NavigationControls = () => {
  const { zoomIn, zoomOut, fitView, setViewport, getViewport } = useReactFlow();
  const [currentZoom, setCurrentZoom] = useState(100);
  
  // Store functions for auto-layout
  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const setNodes = useStore((state) => state.setNodes);
  const setEdges = useStore((state) => state.setEdges);

  // Update zoom percentage when viewport changes (reduced polling frequency)
  useEffect(() => {
    const updateZoom = () => {
      const viewport = getViewport();
      setCurrentZoom(Math.round(viewport.zoom * 100));
    };

    // Initial update
    updateZoom();

    // Reduced polling frequency from 100ms to 500ms to minimize console spam
    const interval = setInterval(updateZoom, 500);
    return () => clearInterval(interval);
  }, [getViewport]);

  const handleZoomIn = useCallback(() => {
    zoomIn({ duration: 200 });
  }, [zoomIn]);

  const handleZoomOut = useCallback(() => {
    zoomOut({ duration: 200 });
  }, [zoomOut]);

  const handleFitView = useCallback(() => {
    fitView({ 
      duration: 300, 
      padding: 0.15,
      maxZoom: 1.0,
      minZoom: 0.1
    });
  }, [fitView]);

  const handleResetView = useCallback(() => {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
  }, [setViewport]);

  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;
    
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes, 
      edges, 
      LAYOUT_DIRECTIONS.LEFT_TO_RIGHT
    );
    
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    
    // Fit view after layout
    setTimeout(() => {
      fitView({ 
        duration: 300, 
        padding: 0.15,
        maxZoom: 1.0,
        minZoom: 0.1
      });
    }, 100);
  }, [nodes, edges, setNodes, setEdges, fitView]);

  return (
    <div className="absolute bottom-4 left-4 flex flex-col gap-2 z-10">
      {/* Zoom Controls Container */}
      <div className="bg-card border border-border rounded-lg shadow-lg overflow-hidden w-fit">
        {/* Zoom In */}
        <button
          onClick={handleZoomIn}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors"
          title="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>
        
        {/* Zoom Level Display */}
        <div className="px-1 py-2 text-xs font-medium text-muted-foreground text-center border-y border-border bg-background/50 w-10">
          <span className="block">{currentZoom}%</span>
        </div>
        
        {/* Zoom Out */}
        <button
          onClick={handleZoomOut}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors"
          title="Zoom Out"
        >
          <Minus className="w-4 h-4" />
        </button>
      </div>

      {/* Additional Controls */}
      <div className="bg-card border border-border rounded-lg shadow-lg overflow-hidden w-fit">
        {/* Auto Layout */}
        <button
          onClick={handleAutoLayout}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors border-b border-border"
          title="Auto Layout"
          disabled={nodes.length === 0}
        >
          <Shuffle className="w-4 h-4" />
        </button>
        
        {/* Fit to Screen */}
        <button
          onClick={handleFitView}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors border-b border-border"
          title="Fit to Screen"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        
        {/* Reset View */}
        <button
          onClick={handleResetView}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors"
          title="Reset View"
        >
          <Home className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default NavigationControls;