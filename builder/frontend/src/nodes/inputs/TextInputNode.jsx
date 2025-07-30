// frontend/src/nodes/inputs/TextInputNode.jsx
// NEW FILE
import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input'; // For label editing
import { MessageSquare } from 'lucide-react';

const TextInputNode = ({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);

  const handleChange = useCallback((evt) => {
    const { name, value } = evt.target;
    updateNodeData(id, { ...data, [name]: value });
  }, [id, updateNodeData, data]);

  const handleTextContentChange = useCallback((value) => {
    updateNodeData(id, { ...data, text_content: value });
  },[id, updateNodeData, data]);

  return (
    <Card className="w-64 shadow-md bg-card text-card-foreground border-0">
      <Handle 
        type="source" 
        position={Position.Right} 
        id="text_output" 
        style={{ background: '#0ea5e9', top: '50%' }}  // Cyan color
        title="Text Output"
      />
      <CardHeader className="p-2 cursor-grab active:cursor-grabbing">
        <div className="flex items-center space-x-1.5">
          <MessageSquare className="h-4 w-4 text-cyan-500 flex-shrink-0" />
          <Input 
                name="label" 
                value={data.label || "Text Input"} 
                onChange={handleChange} 
                className="text-sm font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate"
                placeholder="Node Label"
            />
        </div>
      </CardHeader>
      <CardContent className="p-2 pt-0 nodrag">
        <Label htmlFor={`${id}-text_content`} className="text-xs sr-only">Text Content</Label>
        <Textarea
          id={`${id}-text_content`}
          name="text_content"
          value={data.text_content || ''}
          onChange={(e) => handleTextContentChange(e.target.value)}
          placeholder="Enter your prompt or text here..."
          className="text-xs font-mono border-input nodrag nowheel resize-none" // nowheel to prevent zoom interference
          rows={3}
          style={{ minHeight: 'auto' }}
        />
      </CardContent>
    </Card>
  );
};

export default TextInputNode;