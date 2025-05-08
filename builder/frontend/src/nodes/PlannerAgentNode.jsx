// builder/frontend/src/nodes/PlannerAgentNode.jsx
import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../store';
import { NodeInput } from './BaseNode'; // Use the helper

const PlannerAgentNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  // Needed to update the user_request from the textarea
  const handleChange = useCallback((evt) => {
    const { name, value } = evt.target;
    updateNodeData(id, { [name]: value });
  }, [id, updateNodeData]);

  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-80"> {/* Wider node */}
      <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">Software: Planner</div>
      <div className="nodrag p-1">
        <NodeInput
          name="user_request" // Matches the key in node data and agent_definitions input
          label="User Request:"
          type="textarea"
          value={data.user_request || ''}
          onChange={handleChange}
          placeholder="Enter the software request..."
          rows={6} // Give it some space
        />
      </div>
      {/* Input handle for the request */}
      <Handle
        type="target"
        position={Position.Left}
        id="user_request_in" // Matches agent_definitions handle_id
        style={{ top: '50%', background: '#555' }}
        isConnectable={true}
      />
      {/* Output handle for the plan */}
      <Handle
        type="source"
        position={Position.Right}
        id="plan_out" // Matches agent_definitions handle_id
         style={{ top: '50%', background: '#555' }}
        isConnectable={true}
      />
    </div>
  );
};

export default PlannerAgentNode;