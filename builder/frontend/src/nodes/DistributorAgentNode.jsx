// builder/frontend/src/nodes/DistributorAgentNode.jsx
import React from 'react';
import { Handle, Position } from 'reactflow';
// No internal state updates needed via UI for this node's core function
// import { useStore } from '../store';
// import { NodeInput } from './BaseNode';

const DistributorAgentNode = ({ id, data }) => {
  // No handleChange needed as data primarily flows via edges

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-72"> {/* Standard width */}
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Software: Distributor</div>
      <div className="nodrag p-1 text-xs text-center text-gray-400">
        (Takes Plan In, Outputs Memory & File Prompts)
      </div>
      {/* Input handle for the plan */}
      <Handle
        type="target"
        position={Position.Left}
        id="plan_in" // Matches agent_definitions handle_id
        style={{ top: '50%', background: '#555' }}
        isConnectable={true}
      />
      {/* Output handle for memory */}
      <Handle
        type="source"
        position={Position.Right}
        id="memory_out" // Matches agent_definitions handle_id
         style={{ top: '35%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
      {/* Output handle for file prompts JSON */}
      <Handle
        type="source"
        position={Position.Right}
        id="file_prompts_out" // Matches agent_definitions handle_id
         style={{ top: '65%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
    </div>
  );
};

export default DistributorAgentNode;