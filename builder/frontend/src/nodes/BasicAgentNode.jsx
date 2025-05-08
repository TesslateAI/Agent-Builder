import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store'; // Assuming store.js is in src/
import { NodeInput } from './BaseNode'; // Use the helper

const BasicAgentNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value, type } = evt.target;
    const val = type === 'number' ? parseInt(value, 10) : value;
    updateNodeData(id, { [name]: val });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-64"> {/* Fixed width example */}
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Basic Agent</div>
      <div className="nodrag p-1">
        <NodeInput
          name="prompt"
          label="Prompt:"
          type="textarea"
          value={data.prompt || ''}
          onChange={handleChange}
          placeholder="Enter agent prompt"
          rows={4}
        />
         <NodeInput
          name="maxTokens"
          label="Max Tokens (Optional):"
          type="number"
          value={data.maxTokens}
          onChange={handleChange}
          placeholder="Default"
        />
      </div>
      {/* Single input handle (can have multiple if needed) */}
      <Handle
        type="target"
        position={Position.Left}
        id="prompt_in"
        style={{ top: '50%', background: '#555' }}
        isConnectable={true} // Control connectability later if needed
      />
      {/* Single output handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output_out"
         style={{ top: '50%', background: '#555' }}
        isConnectable={true}
      />
    </div>
  );
};

export default BasicAgentNode;