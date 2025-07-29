// frontend/src/App.jsx
// builder/frontend/src/App.jsx
import React, { useCallback, useRef, useEffect, useMemo } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  useReactFlow,
  useNodesInitialized
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import TerminalPanel from './components/TerminalPanel';
import PropertiesPanel from './components/PropertiesPanel';
import NavigationControls from './components/NavigationControls';
import TextInputNode from './nodes/inputs/TextInputNode'; // New

import TFrameXAgentNode from './nodes/tframex/TFrameXAgentNode';
import TFrameXPatternNode from './nodes/tframex/TFrameXPatternNode';
import TFrameXToolNode from './nodes/tframex/TFrameXToolNode';


const staticNodeTypes = {
  tframexAgent: TFrameXAgentNode,     // Fallback if specific agent type not found
  tframexPattern: TFrameXPatternNode, // Fallback if specific pattern type not found
  tframexTool: TFrameXToolNode,       // Fallback if specific tool type not found
  textInput: TextInputNode,         // For the new TextInputNode
};

const FlowEditor = () => {
  const reactFlowWrapper = useRef(null);
  const { project, getViewport, setViewport } = useReactFlow();

  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const onNodesChange = useStore((state) => state.onNodesChange);
  const onEdgesChange = useStore((state) => state.onEdgesChange);
  const onConnect = useStore((state) => state.onConnect);
  const addNode = useStore((state) => state.addNode);
  const selectedNodeId = useStore((state) => state.selectedNodeId); // Get selectedNodeId
  const setSelectedNodeId = useStore((state) => state.setSelectedNodeId); // Keep for node deselection
  const saveCurrentProject = useStore((state) => state.saveCurrentProject);
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);

  // Save viewport changes
  const onViewportChange = useCallback((viewport) => {
    if (viewport) {
      saveCurrentProject(viewport);
    }
  }, [saveCurrentProject]);

  // Restore viewport when loading project
  useEffect(() => {
    const currentProject = projects[currentProjectId];
    if (currentProject?.viewport && currentProject.viewport.x !== undefined) {
      setViewport(currentProject.viewport, { duration: 0 });
    }
  }, [currentProjectId, projects, setViewport]);

  // Fit view logic using useNodesInitialized
  const nodesInitialized = useNodesInitialized();
  useEffect(() => {
    if (nodesInitialized && nodes.length > 0) {
        const currentProject = projects[currentProjectId];
        // Only fit view if no saved viewport
        if (!currentProject?.viewport || 
            (currentProject.viewport.x === 0 && 
             currentProject.viewport.y === 0 && 
             currentProject.viewport.zoom === 1)) {
            // Auto-fit for new projects or projects without saved viewport
            setTimeout(() => {
                // This ensures fitView is called after nodes are definitely rendered
            }, 100);
        }
    }
  }, [nodesInitialized, nodes, currentProjectId, projects]);


  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      if (!reactFlowWrapper.current) {
        console.error('App.jsx onDrop: reactFlowWrapper.current is null');
        return;
      }
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const typeDataString = event.dataTransfer.getData('application/tframex_component');

      if (!typeDataString) {
        console.warn('App.jsx onDrop: No data found for application/tframex_component');
        return;
      }

      let componentData;
      try {
        componentData = JSON.parse(typeDataString);
      } catch (e) {
        console.error('App.jsx onDrop: Failed to parse componentData JSON:', e, typeDataString);
        return;
      }

      if (!componentData || !componentData.id) {
        console.warn('App.jsx onDrop: Invalid componentData or missing ID:', componentData);
        return;
      }
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });
      addNode(componentData, position);
    },
    [project, addNode]
  );

  const tframexComponents = useStore(s => s.tframexComponents);

  const dynamicNodeTypes = useMemo(() => {
    const customNodes = { ...staticNodeTypes };
    if (tframexComponents?.agents) {
        tframexComponents.agents.forEach(agent => {
            if (agent.id) customNodes[agent.id] = TFrameXAgentNode;
        });
    }
    if (tframexComponents?.patterns) {
        tframexComponents.patterns.forEach(pattern => {
            if (pattern.id) customNodes[pattern.id] = TFrameXPatternNode;
        });
    }
    if (tframexComponents?.tools) {
        tframexComponents.tools.forEach(tool => {
            if (tool.id) customNodes[tool.id] = TFrameXToolNode;
        });
    }
    // Utility components like TextInputNode are already in staticNodeTypes
    return customNodes;
  }, [tframexComponents]);


  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId(node.id);
  }, [setSelectedNodeId]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null); // Deselect node when clicking on pane
  }, [setSelectedNodeId]);


  const styledEdges = edges.map(edge => {
    let edgeStyle = { strokeWidth: 2, stroke: 'var(--color-primary)' }; // Default
    let animated = true;

    switch (edge.data?.connectionType) {
      case 'toolAttachment':
        edgeStyle = { ...edgeStyle, stroke: '#a5b4fc', strokeDasharray: '5 5', strokeWidth: 1.5 };
        animated = false;
        break;
      case 'agentInstanceToPatternParam':
        edgeStyle = { ...edgeStyle, stroke: '#F59E0B', strokeWidth: 2.5 };
        animated = false;
        break;
      case 'agentToPatternListItem':
        edgeStyle = { ...edgeStyle, stroke: '#4CAF50', strokeWidth: 2 };
        animated = false;
        break;
      case 'toolDataOutputToAgent':
        edgeStyle = { ...edgeStyle, stroke: '#7c3aed', strokeWidth: 2 };
        animated = true;
        break;
      case 'textInputToAgent':
        edgeStyle = { ...edgeStyle, stroke: '#0ea5e9', strokeWidth: 2 }; // Cyan for text input
        animated = true;
        break;
      default:
        // Keep default style
        break;
    }
    return { ...edge, style: edgeStyle, animated };
  });

  return (
    <div className="flex h-screen w-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex-grow flex flex-col h-full" ref={reactFlowWrapper}>
        <TopBar />
        <div className="flex-grow relative">
          <ReactFlow
            nodes={nodes}
            edges={styledEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={dynamicNodeTypes}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onViewportChange={onViewportChange}
            fitView // Let ReactFlow manage fitView on initial load/nodes change
            fitViewOptions={{ padding: 0.15, minZoom: 0.1, maxZoom: 4 }}
            className="bg-background"
            defaultEdgeOptions={{ type: 'smoothstep' }} // Base style in defaultEdgeOptions
            connectionLineStyle={{ stroke: 'var(--color-primary)', strokeWidth: 2 }}
            connectionLineType="smoothstep"
            proOptions={{ hideAttribution: true }} // If you have a pro license
            // Performance optimizations
            nodesDraggable={true}
            nodesConnectable={true}
            elementsSelectable={true}
            selectNodesOnDrag={false}
            panOnDrag={true}
            zoomOnScroll={true}
            zoomOnPinch={true}
            zoomOnDoubleClick={true}
            preventScrolling={true}
          >
            <NavigationControls />
            <Background variant="dots" gap={16} size={1} color="var(--color-border)" />
            <MiniMap 
              nodeStrokeWidth={3} 
              className="!m-4 !bg-card !border-border" 
              nodeColor={(n) => {
                if (n.type === 'textInput') return '#0ea5e9'; // Cyan for text input
                if (n.data?.component_category === 'agent') return 'var(--color-primary)';
                if (n.data?.component_category === 'pattern') return 'var(--color-secondary)';
                if (n.data?.component_category === 'tool') return 'var(--color-accent)';
                // Fallback for dynamic types not yet in component_category
                if (tframexComponents.agents.some(a => a.id === n.type)) return 'var(--color-primary)';
                if (tframexComponents.patterns.some(p => p.id === n.type)) return 'var(--color-secondary)';
                if (tframexComponents.tools.some(t => t.id === n.type)) return 'var(--color-accent)';
                return '#ddd';
            }} />
          </ReactFlow>
          
          {/* Properties Panel - overlays on the right side when a node is selected */}
          {selectedNodeId && (
            <div className="absolute top-0 right-0 w-80 h-full bg-card border-l border-border shadow-lg z-10">
              <PropertiesPanel />
            </div>
          )}
        </div>
      </div>
      {/* Right Terminal Panel */}
      <div className={`${selectedNodeId ? 'w-[420px]' : 'w-[500px]'} flex flex-col border-l border-border h-full bg-card transition-all duration-200`}>
        <TerminalPanel />
      </div>
    </div>
  );
};

function App() {
  return (
    <ReactFlowProvider>
      <FlowEditor />
    </ReactFlowProvider>
  );
}

export default App;