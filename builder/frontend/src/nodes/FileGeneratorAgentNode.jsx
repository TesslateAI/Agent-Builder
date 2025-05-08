// builder/frontend/src/nodes/FileGeneratorAgentNode.jsx
import React from 'react';
import { Handle, Position } from 'reactflow';
// No internal state updates needed via UI for this node's core function
// import { useStore } from '../store';
// import { NodeInput } from './BaseNode';

const FileGeneratorAgentNode = ({ id, data }) => {
   // No handleChange needed as data primarily flows via edges

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-72"> {/* Standard width */}
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Software: File Generator</div>
       <div className="nodrag p-1 text-xs text-center text-gray-400">
        (Generates files based on Memory & Prompts)
      </div>
      {/* Input handle for memory */}
      <Handle
        type="target"
        position={Position.Left}
        id="memory_in" // Matches agent_definitions handle_id
        style={{ top: '35%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
       {/* Input handle for file prompts JSON */}
      <Handle
        type="target"
        position={Position.Left}
        id="file_prompts_in" // Matches agent_definitions handle_id
        style={{ top: '65%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
      {/* Output handle for the summary log */}
      <Handle
        type="source"
        position={Position.Right}
        id="summary_out" // Matches agent_definitions handle_id
         style={{ top: '35%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
       {/* Output handle for the preview link */}
      <Handle
        type="source"
        position={Position.Right}
        id="preview_link_out" // Matches agent_definitions handle_id
         style={{ top: '65%', background: '#555' }} // Space handles out
        isConnectable={true}
      />
       {/* Note: run_id is an internal input from the executor, not a visual handle */}
    </div>
  );
};

export default FileGeneratorAgentNode;