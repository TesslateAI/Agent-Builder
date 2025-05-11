// builder/frontend/src/App.jsx
import React, { useCallback, useRef, useEffect, useMemo } from 'react'; // Added useEffect, useMemo
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OutputPanel from './components/OutputPanel';

import TFrameXAgentNode from './nodes/tframex/TFrameXAgentNode';
import TFrameXPatternNode from './nodes/tframex/TFrameXPatternNode';
import TFrameXToolNode from './nodes/tframex/TFrameXToolNode';

// This was missing, but your logic for dynamicNodeTypes implies it should be here.
// If you define these statically, ensure component IDs match.
const staticNodeTypes = {
  tframexAgent: TFrameXAgentNode,
  tframexPattern: TFrameXPatternNode,
  tframexTool: TFrameXToolNode,
  // Add any other static/primitive node types here if you have them
  // e.g. promptPrimitive: PromptPrimitiveNode,
};

const FlowEditor = () => {
  const reactFlowWrapper = useRef(null);
  const { project } = useReactFlow(); // Ensure useReactFlow is correctly imported and used

  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const onNodesChange = useStore((state) => state.onNodesChange);
  const onEdgesChange = useStore((state) => state.onEdgesChange);
  const onConnect = useStore((state) => state.onConnect);
  const addNode = useStore((state) => state.addNode);

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

      console.log('App.jsx onDrop: typeDataString:', typeDataString);

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

      console.log('App.jsx onDrop: Parsed componentData:', componentData);

      if (!componentData || !componentData.id) {
        console.warn('App.jsx onDrop: Invalid componentData or missing ID:', componentData);
        return;
      }

      // Calculate position relative to the ReactFlow pane
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      console.log('App.jsx onDrop: Calculated position:', position);
      addNode(componentData, position);
    },
    [project, addNode, reactFlowWrapper] // reactFlowWrapper added to dependencies
  );

  const tframexComponents = useStore(s => s.tframexComponents);

  const dynamicNodeTypes = useMemo(() => {
    const customNodes = { ...staticNodeTypes }; // Start with static/primitive types
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
    console.log('App.jsx FlowEditor: Generated dynamicNodeTypes:', JSON.stringify(Object.keys(customNodes))); // Log keys for brevity
    return customNodes;
  }, [tframexComponents]);

  useEffect(() => {
    console.log('App.jsx FlowEditor: Nodes state updated:', nodes.map(n => ({id: n.id, type: n.type, label: n.data.label})));
  }, [nodes]);

  const styledEdges = edges.map(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source);
    // const targetNode = nodes.find(n => n.id === edge.target); // If needed

    switch (edge.data?.connectionType) {
      case 'toolAttachment':
        return {
          ...edge,
          style: { ...edge.style, stroke: '#a5b4fc', strokeDasharray: '5 5', strokeWidth: 1.5 },
          animated: false,
        };
      case 'agentInstanceToPatternParam': // Agent connected to a pattern's single agent param
        return {
          ...edge,
          style: { ...edge.style, stroke: '#F59E0B', strokeWidth: 2 }, // Amber
          animated: false,
        };
      case 'agentToPatternListItem': // Agent connected to a pattern's list item slot
        return {
          ...edge,
          style: { ...edge.style, stroke: '#4CAF50', strokeWidth: 1.8 }, // Green
          animated: false,
        };
      case 'toolDataOutputToAgent': // Tool's data output connected to an agent
        return {
            ...edge,
            style: { ...edge.style, stroke: '#7c3aed', strokeWidth: 2}, // Purple
            animated: true,
        };
      default:
        // General styling for data output from a tool node if not explicitly typed above
        if (sourceNode?.data?.component_category === 'tool' && edge.sourceHandle === 'tool_output_data') {
            return {
                ...edge,
                style: { ...edge.style, stroke: '#7c3aed', strokeWidth: 2 }, // Purple
                animated: true,
            };
        }
        // Fallback to default edge style or preserve existing custom style
        return edge;
    }
  });

  return (
    <div className="flex h-screen w-screen bg-background text-foreground" ref={reactFlowWrapper}>
      <Sidebar />
      <div className="flex-grow flex flex-col h-full">
        <TopBar />
        <div className="flex-grow relative"> {/* This div will be the drop target area */}
          <ReactFlow
            nodes={nodes}
            edges={styledEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={dynamicNodeTypes} // Use the dynamically generated node types
            fitView
            className="bg-background" // Make sure this className matches if you rely on it for reactFlowBounds
            defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { strokeWidth: 2, stroke: 'var(--color-primary)' } }}
            connectionLineStyle={{ stroke: 'var(--color-primary)', strokeWidth: 2 }}
            connectionLineType="smoothstep"
          >
            <Controls className="react-flow__controls" />
            <Background variant="dots" gap={16} size={1} color="var(--color-border)" />
            <MiniMap nodeStrokeWidth={3} nodeColor={(n) => {
                if (n.type === 'tframexAgent' || tframexComponents.agents.some(a => a.id === n.type)) return 'var(--color-primary)';
                if (n.type === 'tframexPattern' || tframexComponents.patterns.some(p => p.id === n.type)) return 'var(--color-secondary)';
                if (n.type === 'tframexTool' || tframexComponents.tools.some(t => t.id === n.type)) return 'var(--color-accent)';
                return '#ddd';
            }} />
          </ReactFlow>
        </div>
      </div>
      <OutputPanel />
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