// builder/frontend/src/nodes/PromptInjectorNode.jsx
import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

const PromptInjectorNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value } = evt.target;
    updateNodeData(id, { [name]: value });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-96">
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Prompt Injector</div>
      <div className="nodrag p-1 space-y-2">
        <div>
            <Label htmlFor={`${id}-full_prompt`} className="node-label block">
                Paste Full Prompt (Memory & File Prompts):
            </Label>
            <Textarea
                id={`${id}-full_prompt`}
                name="full_prompt" // Key for data.full_prompt
                value={data.full_prompt || ''}
                onChange={handleChange}
                placeholder=" "
                className="node-textarea w-full min-h-[200px] max-h-[400px] resize-y bg-gray-700 border-gray-600 text-gray-200"
                rows={10}
            />
        </div>
        {/* Optional: A small descriptive text if needed */}
        {/* <p className="text-xs text-gray-400 text-center mt-1">
            Outputs: Memory (top-right), File Prompts JSON (bottom-right)
        </p> */}
      </div>
      {/* NO INPUT HANDLES */}

      {/* Output handle for memory */}
      <Handle
        type="source"
        position={Position.Right}
        id="memory_out" // Matches agent_definitions output handle_id
        style={{ top: '35%', background: '#555' }}
        isConnectable={true}
        title="Memory Output"
      />
      {/* Output handle for file prompts JSON */}
      <Handle
        type="source"
        position={Position.Right}
        id="file_prompts_out" // Matches agent_definitions output handle_id
        style={{ top: '65%', background: '#555' }}
        isConnectable={true}
        title="File Prompts JSON Output"
      />
    </div>
  );
};

export default PromptInjectorNode;