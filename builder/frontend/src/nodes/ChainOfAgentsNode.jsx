import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { NodeInput } from './BaseNode';

const ChainOfAgentsNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value, type } = evt.target;
    // Ensure numbers are stored as numbers
    const val = type === 'number' ? (value === '' ? null : parseInt(value, 10)) : value;
    updateNodeData(id, { [name]: val });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-80">
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Chain of Agents System</div>
      <div className="nodrag p-1">
         <NodeInput
          name="initialPrompt"
          label="Initial Prompt:"
          type="textarea"
          value={data.initialPrompt || ''}
          onChange={handleChange}
          placeholder="Enter initial prompt for the chain"
          rows={3}
        />
         <NodeInput
          name="longText"
          label="Long Text Input:"
          type="textarea"
          value={data.longText || ''}
          onChange={handleChange}
          placeholder="Paste the long text here"
          rows={6}
        />
        <div className="grid grid-cols-2 gap-2">
          <NodeInput
            name="chunkSize"
            label="Chunk Size:"
            type="number"
            value={data.chunkSize}
            onChange={handleChange}
            placeholder="e.g., 2000"
          />
           <NodeInput
            name="chunkOverlap"
            label="Chunk Overlap:"
            type="number"
            value={data.chunkOverlap}
            onChange={handleChange}
            placeholder="e.g., 200"
          />
        </div>
        <NodeInput
          name="maxTokens"
          label="Max Tokens (Final) (Optional):"
          type="number"
          value={data.maxTokens}
          onChange={handleChange}
          placeholder="Default"
        />
      </div>
      {/* Input handles */}
      <Handle type="target" position={Position.Left} id="prompt_in" style={{ top: '30%', background: '#555' }} isConnectable={true} />
      <Handle type="target" position={Position.Left} id="text_in" style={{ top: '70%', background: '#555' }} isConnectable={true} />
      {/* Output handle */}
      <Handle type="source" position={Position.Right} id="output_out" style={{ top: '50%', background: '#555' }} isConnectable={true} />
    </div>
  );
};

export default ChainOfAgentsNode;