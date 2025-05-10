// builder/frontend/src/App.jsx
import React, { useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  addEdge,
  MiniMap,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { nanoid } from 'nanoid';

import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OutputPanel from './components/OutputPanel';

// ... (your existing node imports)
import BasicAgentNode from './nodes/BasicAgentNode';
import ContextAgentNode from './nodes/ContextAgentNode';
import ChainOfAgentsNode from './nodes/ChainOfAgentsNode';
import MultiCallSystemNode from './nodes/MultiCallSystemNode';
import PlannerAgentNode from './nodes/PlannerAgentNode';
import DistributorAgentNode from './nodes/DistributorAgentNode';
import FileGeneratorAgentNode from './nodes/FileGeneratorAgentNode';
import PromptInjectorNode from './nodes/PromptInjectorNode';


const nodeTypes = {
  basicAgent: BasicAgentNode,
  contextAgent: ContextAgentNode,
  chainOfAgents: ChainOfAgentsNode,
  multiCallSystem: MultiCallSystemNode,
  plannerAgent: PlannerAgentNode,
  distributorAgent: DistributorAgentNode,
  fileGeneratorAgent: FileGeneratorAgentNode,
  promptInjectorAgent: PromptInjectorNode,
};

const FlowEditor = () => {
  const reactFlowWrapper = useRef(null);
  const { project } = useReactFlow();

  const nodes = useStore((state) => state.nodes);
  const originalEdges = useStore((state) => state.edges); // Get original edges
  const onNodesChange = useStore((state) => state.onNodesChange);
  const onEdgesChange = useStore((state) => state.onEdgesChange);
  const addNode = useStore((state) => state.addNode);
  const setEdges = useStore((state) => state.setEdges);

  const onConnect = useCallback(
    (params) => setEdges(addEdge({ ...params, type: 'smoothstep', animated: true }, originalEdges)),
    [originalEdges, setEdges],
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const currentRef = reactFlowWrapper.current;
      if (!currentRef) return;
      const reactFlowBounds = currentRef.getBoundingClientRect();
      const nodeInfoString = event.dataTransfer.getData('application/reactflow');
      if (!nodeInfoString) return;

      try {
        const { type, label } = JSON.parse(nodeInfoString);
        if (typeof type === 'undefined' || !type) return;

        const position = project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });

        let nodeSpecificData = {};
        // ... (your existing onDrop nodeSpecificData logic)
        if (type === 'basicAgent') {
            nodeSpecificData = { prompt: "", max_tokens: null };
        } else if (type === 'contextAgent') {
            const exampleContextContent = useStore.getState().projects?.example2?.nodes?.[0]?.data?.context || "Default context.";
            nodeSpecificData = { context: exampleContextContent, prompt: "", max_tokens: null };
        } else if (type === 'chainOfAgents') {
            const exampleLongTextContent = useStore.getState().projects?.example3?.nodes?.[0]?.data?.longText || "Default long text.";
            nodeSpecificData = { initialPrompt: "", longText: exampleLongTextContent, chunkSize: 2000, chunkOverlap: 200, maxTokens: null };
        } else if (type === 'multiCallSystem') {
            nodeSpecificData = { prompt: "", numCalls: 3, baseFilename: "output", maxTokens: null };
        } else if (type === 'plannerAgent') {
            nodeSpecificData = { user_request: "Build a simple todo list application." };
        } else if (type === 'promptInjectorAgent') {
            nodeSpecificData = {
                full_prompt: "<memory>\nType shared memory here...\n</memory>\n\n<prompt filename=\"example.txt\">\nType prompt for example.txt here...\n</prompt>",
            };
        }
        // ... (ensure all your node types have default data if needed)

        const newNode = {
          id: `${type}-${nanoid(6)}`,
          type,
          position,
          data: { label: label || `${type} Node`, ...nodeSpecificData },
        };
        addNode(newNode);
      } catch (e) {
        console.error("Failed to parse dropped node data:", e);
      }
    },
    [addNode, project],
  );

  // --- START SMALL CHANGE FOR YELLOW MEMORY EDGES ---
  const styledEdges = originalEdges.map(edge => {
    // Check if the edge is connected to/from a memory handle
    if (edge.sourceHandle === 'memory_out' || edge.targetHandle === 'memory_in') {
      return {
        ...edge,
        style: {
          ...edge.style, // Preserve other styles if any
          stroke: '#eab308', // A nice yellow color (Tailwind's amber-500)
          strokeWidth: 3,     // Slightly thicker
        },
        // animated: false, // Optionally make memory lines not animated
      };
    }
    return edge; // Return unchanged if not a memory edge
  });
  // --- END SMALL CHANGE FOR YELLOW MEMORY EDGES ---

  return (
    <div className="flex h-screen w-screen bg-gray-900" ref={reactFlowWrapper}>
      <Sidebar />
      <div className="flex-grow flex flex-col h-full">
        <TopBar />
        <div className="flex-grow relative">
          <ReactFlow
            nodes={nodes}
            edges={styledEdges} // Use the dynamically styled edges
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-900"
            defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { strokeWidth: 2 } }}
            connectionLineStyle={{ stroke: '#4f46e5', strokeWidth: 2 }}
            connectionLineType="smoothstep"
          >
            <Controls className="react-flow__controls" />
            <Background variant="dots" gap={16} size={1} color="#4A5568" />
            <MiniMap nodeStrokeWidth={3} nodeColor={(n) => {
                 switch (n.type) {
                     case 'basicAgent': return '#3b82f6';
                     case 'contextAgent': return '#10b981';
                     case 'chainOfAgents': return '#f97316';
                     case 'multiCallSystem': return '#a855f7';
                     case 'plannerAgent': return '#ef4444';
                     case 'distributorAgent': return '#eab308';
                     case 'fileGeneratorAgent': return '#22c55e';
                     case 'promptInjectorAgent': return '#6366f1';
                     default: return '#6b7280';
                 }
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