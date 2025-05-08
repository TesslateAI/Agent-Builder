import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { NodeInput } from './BaseNode';

const SoftwareBuilderNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value } = evt.target;
    updateNodeData(id, { [name]: value });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-80">
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Software Builder System</div>
      <div className="nodrag p-1">
         <NodeInput
          name="userRequest"
          label="User Request:"
          type="textarea"
          value={data.userRequest || ''}
          onChange={handleChange}
          placeholder="Describe the software you want to build..."
          rows={6}
        />
      </div>
      {/* Input handle */}
      <Handle type="target" position={Position.Left} id="request_in" style={{ top: '50%', background: '#555' }} isConnectable={true} />
      {/* Output handle */}
      <Handle type="source" position={Position.Right} id="output_out" style={{ top: '50%', background: '#555' }} isConnectable={true} />
    </div>
  );
};

export default SoftwareBuilderNode;