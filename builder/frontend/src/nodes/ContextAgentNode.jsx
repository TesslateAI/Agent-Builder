import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { NodeInput } from './BaseNode';

const ContextAgentNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value, type } = evt.target;
    const val = type === 'number' ? parseInt(value, 10) : value;
    updateNodeData(id, { [name]: val });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-72">
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Context Agent</div>
      <div className="nodrag p-1">
        <NodeInput
          name="context"
          label="Context:"
          type="textarea"
          value={data.context || ''}
          onChange={handleChange}
          placeholder="Enter context text"
          rows={5}
        />
         <NodeInput
          name="prompt"
          label="Prompt:"
          type="textarea"
          value={data.prompt || ''}
          onChange={handleChange}
          placeholder="Enter prompt"
          rows={3}
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
      {/* Multiple input handles */}
      <Handle type="target" position={Position.Left} id="context_in" style={{ top: '30%', background: '#555' }} isConnectable={true} />
      <Handle type="target" position={Position.Left} id="prompt_in" style={{ top: '70%', background: '#555' }} isConnectable={true} />
      {/* Single output handle */}
      <Handle type="source" position={Position.Right} id="output_out" style={{ top: '50%', background: '#555' }} isConnectable={true} />
    </div>
  );
};

export default ContextAgentNode;