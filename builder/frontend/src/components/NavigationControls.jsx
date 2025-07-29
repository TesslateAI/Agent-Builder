import React, { useCallback } from 'react';
import { useReactFlow } from 'reactflow';
import { Plus, Minus, Maximize2, Home } from 'lucide-react';

const NavigationControls = () => {
  const { zoomIn, zoomOut, fitView, setViewport, getViewport } = useReactFlow();

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
      maxZoom: 1.5,
      minZoom: 0.1
    });
  }, [fitView]);

  const handleResetView = useCallback(() => {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
  }, [setViewport]);

  const currentZoom = Math.round(getViewport().zoom * 100);

  return (
    <div className="absolute bottom-4 left-4 flex flex-col gap-2 z-10">
      {/* Zoom Controls Container */}
      <div className="bg-card border border-border rounded-lg shadow-lg overflow-hidden">
        {/* Zoom In */}
        <button
          onClick={handleZoomIn}
          className="flex items-center justify-center w-10 h-10 hover:bg-muted transition-colors"
          title="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>
        
        {/* Zoom Level Display */}
        <div className="px-3 py-2 text-xs font-medium text-muted-foreground text-center border-y border-border bg-background/50">
          {currentZoom}%
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
      <div className="bg-card border border-border rounded-lg shadow-lg overflow-hidden">
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