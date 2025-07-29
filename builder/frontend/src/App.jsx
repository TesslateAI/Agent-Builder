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

  // Fit view logic using useNodesInitialized
  const nodesInitialized = useNodesInitialized();
  useEffect(() => {
    if (nodesInitialized && nodes.length > 0) {
        // Check if viewport is default (likely first load or project switch)
        const currentViewport = getViewport();
        if (currentViewport.x === 0 && currentViewport.y === 0 && currentViewport.zoom === 1) {
            // project() should ideally call fitView, but sometimes direct fitView is needed
            // This is a bit of a workaround; React Flow's fitView on load can be tricky
            setTimeout(() => {
                // This ensures fitView is called after nodes are definitely rendered
                // No direct 'fitView' from useReactFlow, rely on ReactFlow's prop or manual calc
            }, 100);
        }
    }
  }, [nodesInitialized, nodes, getViewport, project]);


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
            fitView // Let ReactFlow manage fitView on initial load/nodes change
            fitViewOptions={{ padding: 0.15, minZoom: 0.2, maxZoom: 2 }}
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
            preventScrolling={false}
          >
            <Controls className="react-flow__controls" />
            <Background variant="dots" gap={16} size={1} color="var(--color-border)" />
            <MiniMap nodeStrokeWidth={3} nodeColor={(n) => {
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