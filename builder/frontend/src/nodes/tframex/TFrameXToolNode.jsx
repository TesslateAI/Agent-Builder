// frontend/src/nodes/tframex/TFrameXToolNode.jsx
// builder/frontend/src/nodes/tframex/TFrameXToolNode.jsx
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Wrench, Zap, X } from 'lucide-react'; 
import { useStore } from '../../store';


const TFrameXToolNode = memo(({ id, data, type: tframexToolId }) => {
  const toolDefinition = useStore(state => 
    state.tframexComponents.tools.find(t => t.id === tframexToolId)
  );
  const deleteNode = useStore((state) => state.deleteNode);

  if (!toolDefinition) {
    return (
        <Card className="w-60 p-2 border-destructive bg-destructive/10">
            <CardHeader className="p-2">
                <CardTitle className="text-sm text-destructive-foreground">Error: Tool Unknown</CardTitle>
            </CardHeader>
             <CardContent className="p-2 text-xs text-destructive-foreground/80">
                Definition for tool type '{tframexToolId}' not found.
            </CardContent>
        </Card>
    );
  }

  // Check if tool produces data. Use data.has_data_output set by store if available,
  // otherwise infer from definition.
  const canProduceData = data.has_data_output !== undefined ? data.has_data_output :
    (toolDefinition.parameters_schema && Object.keys(toolDefinition.parameters_schema).length > 0 && toolDefinition.description?.toLowerCase().includes("return"));

  return (
    <Card className="w-64 shadow-md bg-card text-card-foreground opacity-90 hover:opacity-100 transition-opacity relative border-0">
      <Handle 
        type="source"
        position={Position.Right}
        id="tool_attachment_out" 
        data-handletype="tool"
        style={{ top: canProduceData ? '35%' : '50%', width:10, height:10, zIndex: 1 }}
        title="Connect to Agent to Enable Tool"
      />
      {canProduceData && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="tool_output_data" 
          data-handletype="data"
          style={{ top: '65%', width:10, height:10, zIndex: 1 }}
          title="Tool Data Output (Connect to Agent Input)"
        />
      )}

      {/* Delete button */}
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => deleteNode(id)}
        className="absolute top-1 right-1 h-6 w-6 p-0 hover:bg-destructive/10 z-10"
        title="Delete tool"
      >
        <X className="h-4 w-4 text-destructive" />
      </Button>

      <CardHeader className="p-2.5">
         <div className="flex items-center space-x-2">
            <Wrench className="h-4 w-4 text-accent flex-shrink-0" />
            <CardTitle className="text-sm font-semibold truncate" title={data.label || tframexToolId}>{data.label || tframexToolId}</CardTitle>
        </div>
        {toolDefinition.description && <CardDescription className="text-xs mt-1 line-clamp-2">{toolDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-2.5 text-xs text-center text-muted-foreground nodrag">
        <div className="flex items-center justify-center">
            <Zap className="inline h-3 w-3 mr-1 text-accent" /> To Agent to enable.
        </div>
        {canProduceData && (
            <div className="flex items-center justify-center mt-0.5">
                 <Wrench className="inline h-3 w-3 mr-1 text-accent" /> For data output.
            </div>
        )}
      </CardContent>
    </Card>
  );
});

TFrameXToolNode.displayName = 'TFrameXToolNode';

export default TFrameXToolNode;