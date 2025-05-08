import React, { useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Controls,
  Background,
  addEdge,
  MiniMap,
  useReactFlow, // Import useReactFlow for projecting coordinates
} from 'reactflow';
import 'reactflow/dist/style.css';
import { nanoid } from 'nanoid';

import { useStore } from './store';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OutputPanel from './components/OutputPanel';

// Import Custom Nodes (still needed for rendering)
import BasicAgentNode from './nodes/BasicAgentNode';
import ContextAgentNode from './nodes/ContextAgentNode';
import ChainOfAgentsNode from './nodes/ChainOfAgentsNode';
import MultiCallSystemNode from './nodes/MultiCallSystemNode';
// SoftwareBuilderNode is removed
import PlannerAgentNode from './nodes/PlannerAgentNode'; // Create this file
import DistributorAgentNode from './nodes/DistributorAgentNode'; // Create this file
import FileGeneratorAgentNode from './nodes/FileGeneratorAgentNode'; // Create this file

const nodeTypes = {
  basicAgent: BasicAgentNode,
  contextAgent: ContextAgentNode,
  chainOfAgents: ChainOfAgentsNode,
  multiCallSystem: MultiCallSystemNode,
  // Add new software builder nodes
  plannerAgent: PlannerAgentNode,
  distributorAgent: DistributorAgentNode,
  fileGeneratorAgent: FileGeneratorAgentNode,
};
// ----------------------------------------------------

const FlowEditor = () => {
  const reactFlowWrapper = useRef(null);
  const { project } = useReactFlow(); // Get project function

  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const onNodesChange = useStore((state) => state.onNodesChange);
  const onEdgesChange = useStore((state) => state.onEdgesChange);
  const addNode = useStore((state) => state.addNode);
  const setEdges = useStore((state) => state.setEdges);

  const onConnect = useCallback(
    (params) => setEdges(addEdge({ ...params, type: 'smoothstep', animated: true }, edges)), // Example: Add edge type
    [edges, setEdges],
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const currentRef = reactFlowWrapper.current;
       if (!currentRef) {
          console.error("React Flow wrapper ref not available");
          return;
      }

      const reactFlowBounds = currentRef.getBoundingClientRect();
      const nodeInfoString = event.dataTransfer.getData('application/reactflow');

       if (!nodeInfoString) {
           console.warn("No node info found in dataTransfer");
           return;
       }

      try {
          // type is the agent_id from the backend, label is the name
          const {type, label} = JSON.parse(nodeInfoString);

          if (typeof type === 'undefined' || !type) {
            return;
          }

          // Correctly project screen coordinates to flow coordinates
          const position = project({
             x: event.clientX - reactFlowBounds.left,
             y: event.clientY - reactFlowBounds.top,
          });

          // Create initial data. Specific nodes might initialize more fields
          // based on their internal logic or props. The backend definition
          // dictates the *required* inputs for execution via edges.
          const initialNodeData = {
            label: label || `${type} Node`,
            // Add default values for inputs shown in the node UI if applicable
            // e.g., for basicAgent:
            prompt: "",
            max_tokens: null,
            // e.g., for contextAgent:
            context: "",
            // e.g., for chainOfAgents:
            initialPrompt: "",
            longText: "",
            chunkSize: 2000, // Default config shown in UI
            chunkOverlap: 200, // Default config shown in UI
            // e.g., for multiCallSystem:
            numCalls: 3,
            baseFilename: "output",
            // ... other defaults based on what your node component expects ...
          };

          const newNode = {
            id: `${type}-${nanoid(6)}`,
            type, // This MUST match the ID from agent_definitions.py
            position,
            data: initialNodeData,
          };

          console.log("Adding node:", newNode);
          addNode(newNode);
      } catch (e) {
          console.error("Failed to parse dropped node data:", e);
      }

    },
    [addNode, project], // Add project dependency
  );

  return (
    <div className="flex h-screen w-screen bg-gray-900" ref={reactFlowWrapper}>
      <Sidebar />
      <div className="flex-grow flex flex-col h-full">
        <TopBar />
        <div className="flex-grow relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes} // Use the constant defined outside
            fitView
            className="bg-gray-900"
            // Default edge options (example)
            defaultEdgeOptions={{ type: 'smoothstep', animated: true, style: { strokeWidth: 2 } }}
            connectionLineStyle={{ stroke: '#4f46e5', strokeWidth: 2 }} // Indigo color
            connectionLineType="smoothstep"
          >
            <Controls className="react-flow__controls" />
            <Background variant="dots" gap={16} size={1} color="#4A5568" />
             <MiniMap nodeStrokeWidth={3} nodeColor={(n) => {
                 switch (n.type) { // n.type now matches agent_id
                     case 'basicAgent': return '#3b82f6';
                     case 'contextAgent': return '#10b981';
                     case 'chainOfAgents': return '#f97316';
                     case 'multiCallSystem': return '#a855f7';
                    // Add other types if needed
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

// Wrap with ReactFlowProvider
function App() {
  return (
    <ReactFlowProvider>
      <FlowEditor />
    </ReactFlowProvider>
  );
}

export default App;