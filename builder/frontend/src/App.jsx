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
import { debounce } from 'lodash';

import { useAuth } from './contexts/AuthContext';
import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import TerminalPanel from './components/TerminalPanel';
import PropertiesPanel from './components/PropertiesPanel';
import NavigationControls from './components/NavigationControls';
import LoginPage from './components/auth/LoginPage';
import TextInputNode from './nodes/inputs/TextInputNode'; // New

import TFrameXAgentNode from './nodes/tframex/TFrameXAgentNode';
import TFrameXPatternNode from './nodes/tframex/TFrameXPatternNode';
import TFrameXToolNode from './nodes/tframex/TFrameXToolNode';
import MCPServerNode from './nodes/tframex/MCPServerNode';
import TriggerNode from './nodes/tframex/TriggerNode';


const staticNodeTypes = {
  tframexAgent: TFrameXAgentNode,     // Fallback if specific agent type not found
  tframexPattern: TFrameXPatternNode, // Fallback if specific pattern type not found
  tframexTool: TFrameXToolNode,       // Fallback if specific tool type not found
  textInput: TextInputNode,         // For the new TextInputNode
  MCPServerNode: MCPServerNode,     // For MCP server nodes
  trigger: TriggerNode,             // For trigger nodes
};

const FlowEditor = () => {
  const reactFlowWrapper = useRef(null);
  const { project, setViewport } = useReactFlow();

  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  
  // Reduced logging for ReactFlow state changes
  useEffect(() => {
    if (nodes.length > 0 || edges.length > 0) {
      console.log("🔄 ReactFlow updated - Nodes:", nodes.length, "Edges:", edges.length);
    }
  }, [nodes, edges]);
  const onNodesChange = useStore((state) => state.onNodesChange);
  const onEdgesChange = useStore((state) => state.onEdgesChange);
  const onConnect = useStore((state) => state.onConnect);
  const addNode = useStore((state) => state.addNode);
  const selectedNodeId = useStore((state) => state.selectedNodeId); // Get selectedNodeId
  const setSelectedNodeId = useStore((state) => state.setSelectedNodeId); // Keep for node deselection
  const saveCurrentProject = useStore((state) => state.saveCurrentProject);
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);

  // Debounced save to prevent interference with dragging
  const debouncedSaveProject = useMemo(
    () => debounce((viewport) => {
      saveCurrentProject(viewport);
    }, 300),
    [saveCurrentProject]
  );

  // Save viewport changes
  const onViewportChange = useCallback((viewport) => {
    if (viewport) {
      debouncedSaveProject(viewport);
    }
  }, [debouncedSaveProject]);

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
      
      // ReactFlow expects nodes to be positioned by their top-left corner
      // No adjustment needed - let ReactFlow handle the positioning
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
    if (tframexComponents?.mcp_servers) {
        tframexComponents.mcp_servers.forEach(server => {
            if (server.id) customNodes[server.id] = MCPServerNode;
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
      case 'mcpServerAttachment':
        edgeStyle = { ...edgeStyle, stroke: '#10b981', strokeDasharray: '3 7', strokeWidth: 2 };
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
      case 'triggerToNode':
        edgeStyle = { ...edgeStyle, stroke: '#f97316', strokeWidth: 3 }; // Orange for trigger connections
        animated = true;
        break;
      default:
        // Keep default style
        break;
    }
    return { ...edge, style: edgeStyle, animated };
  });

  return (
    <div className="flex h-screen w-screen bg-sidebar text-foreground">
      <Sidebar />
      <div className="flex-grow flex flex-col h-full" ref={reactFlowWrapper}>
        <TopBar />
        <div className="flex-grow relative overflow-hidden">
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
            fitViewOptions={{ padding: 0.15, minZoom: 0.1, maxZoom: 4 }}
            defaultEdgeOptions={{ type: 'smoothstep' }} // Base style in defaultEdgeOptions
            connectionLineStyle={{ stroke: 'var(--color-primary)', strokeWidth: 2 }}
            connectionLineType="smoothstep"
            proOptions={{ hideAttribution: true }} // If you have a pro license
            // Performance optimizations
            nodesDraggable={true}
            nodesConnectable={true}
            elementsSelectable={true}
            panOnDrag={true}
            zoomOnScroll={true}
            zoomOnPinch={true}
            zoomOnDoubleClick={true}
            preventScrolling={true}
            snapToGrid={false}
          >
            <Background 
              color="rgba(255, 255, 255, 0.15)" 
              gap={24} 
              size={1} 
              variant="dots" 
            />
            <NavigationControls />
            <MiniMap 
              nodeStrokeWidth={3} 
              className="!m-4 !bg-card !border-border" 
              nodeColor={(n) => {
                if (n.type === 'textInput') return '#0ea5e9'; // Cyan for text input
                if (n.type === 'trigger') return '#f97316'; // Orange for triggers
                if (n.type === 'MCPServerNode' || n.data?.component_category === 'mcp_server') return '#10b981'; // Green for MCP servers
                if (n.data?.component_category === 'agent') return 'var(--color-primary)';
                if (n.data?.component_category === 'pattern') return 'var(--color-secondary)';
                if (n.data?.component_category === 'tool') return 'var(--color-accent)';
                // Fallback for dynamic types not yet in component_category
                if (tframexComponents.agents.some(a => a.id === n.type)) return 'var(--color-primary)';
                if (tframexComponents.patterns.some(p => p.id === n.type)) return 'var(--color-secondary)';
                if (tframexComponents.tools.some(t => t.id === n.type)) return 'var(--color-accent)';
                if (tframexComponents.mcp_servers?.some(m => m.id === n.type)) return '#10b981';
                return '#ddd';
            }} />
          </ReactFlow>
          
          {/* Properties Panel - overlays on the right side when a node is selected */}
          {selectedNodeId && (
            <div className="absolute top-0 right-0 w-80 h-full bg-sidebar border-l border-sidebar-border shadow-lg z-10">
              <PropertiesPanel />
            </div>
          )}
        </div>
      </div>
      {/* Right Terminal Panel */}
      <div className="w-[500px] flex flex-col border-l border-sidebar-border h-full bg-sidebar">
        <TerminalPanel />
      </div>
    </div>
  );
};

function App() {
  const { isAuthenticated, isLoading, status } = useAuth();

  // Show loading spinner while checking authentication
  if (isLoading || status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Show main application if authenticated
  return (
    <ReactFlowProvider>
      <FlowEditor />
    </ReactFlowProvider>
  );
}

export default App;