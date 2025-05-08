import React from 'react';
import { Handle, Position } from 'reactflow';

// A simple wrapper for consistent styling if needed, but can apply directly
const BaseNode = ({ children, title }) => {
  return (
    <div className="p-3 rounded-lg shadow-lg bg-gray-800 border border-gray-600 text-gray-200 w-full">
      {title && <div className="text-center font-bold mb-2 border-b border-gray-600 pb-1">{title}</div>}
      <div className="nodrag"> {/* Prevent dragging from content area */}
        {children}
      </div>
    </div>
  );
};

export default BaseNode;

// Helper for creating text inputs/areas easily within nodes
export const NodeInput = ({ label, type = 'text', value, onChange, placeholder, rows, name }) => (
    <div className="mb-2">
        <label htmlFor={name} className="node-label">{label}</label>
        {type === 'textarea' ? (
             <textarea
                 id={name}
                 name={name}
                 rows={rows || 3}
                 className="node-textarea"
                 value={value}
                 onChange={onChange}
                 placeholder={placeholder}
             />
        ) : (
            <input
                id={name}
                name={name}
                type={type}
                className="node-input"
                value={value || ''} // Ensure value is never null/undefined for input
                onChange={onChange}
                placeholder={placeholder}
             />
        )}
    </div>
);