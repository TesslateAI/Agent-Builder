import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { NodeInput } from './BaseNode';

const MultiCallSystemNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

 const handleChange = useCallback((evt) => {
    const { name, value, type } = evt.target;
    const val = type === 'number' ? (value === '' ? null : parseInt(value, 10)) : value;
    updateNodeData(id, { [name]: val });
  }, [id, updateNodeData]);


  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-72">
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Multi Call System</div>
      <div className="nodrag p-1">
         <NodeInput
          name="prompt"
          label="Prompt (for each call):"
          type="textarea"
          value={data.prompt || ''}
          onChange={handleChange}
          placeholder="Enter the prompt"
          rows={4}
        />
        <div className="grid grid-cols-2 gap-2">
            <NodeInput
                name="numCalls"
                label="# Calls:"
                type="number"
                value={data.numCalls}
                onChange={handleChange}
                placeholder="e.g., 5"
            />
             <NodeInput
                name="maxTokens"
                label="Max Tokens (per call):"
                type="number"
                value={data.maxTokens}
                onChange={handleChange}
                placeholder="e.g., 1000"
            />
        </div>
        <NodeInput
          name="baseFilename"
          label="Base Filename:"
          type="text"
          value={data.baseFilename || ''}
          onChange={handleChange}
          placeholder="e.g., output_call"
        />
        <NodeInput
          name="outputDir"
          label="Output Directory (Backend):"
          type="text"
          value={data.outputDir || ''}
          onChange={handleChange}
          placeholder="Default: example_outputs/..."
        />

      </div>
      {/* Input handle */}
      <Handle type="target" position={Position.Left} id="prompt_in" style={{ top: '50%', background: '#555' }} isConnectable={true} />
      {/* Output handle */}
      <Handle type="source" position={Position.Right} id="output_out" style={{ top: '50%', background: '#555' }} isConnectable={true} />
    </div>
  );
};

export default MultiCallSystemNode;