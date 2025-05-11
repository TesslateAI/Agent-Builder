// builder/frontend/src/nodes/tframex/TFrameXToolNode.jsx
import React from 'react';
import { Handle, Position } from 'reactflow';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Wrench, DatabaseZap, Zap } from 'lucide-react'; // Zap for attachment
import { useStore } from '../../store';


const TFrameXToolNode = ({ id, data, type: tframexToolId }) => {
  const toolDefinition = useStore(state => 
    state.tframexComponents.tools.find(t => t.id === tframexToolId)
  );

  if (!toolDefinition) {
    return <Card className="w-60 p-2 border-destructive"><CardHeader><CardTitle>Error: Tool Unknown</CardTitle></CardHeader></Card>;
  }

  const canProduceData = data.has_data_output || (toolDefinition.parameters_schema && Object.keys(toolDefinition.parameters_schema).length > 0 && toolDefinition.description?.toLowerCase().includes("return"));

  return (
    <Card className="w-64 shadow-md border-border bg-card text-card-foreground opacity-90 hover:opacity-100 transition-opacity">
      <CardHeader className="p-2.5 border-b border-border">
         <div className="flex items-center space-x-2">
            <Wrench className="h-4 w-4 text-indigo-400" />
            <CardTitle className="text-sm font-semibold">{data.label || tframexToolId}</CardTitle>
        </div>
        {toolDefinition.description && <CardDescription className="text-xs mt-1 line-clamp-2">{toolDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-2 text-xs text-center text-muted-foreground nodrag">
        Drag <Zap className="inline h-3 w-3 text-indigo-400"/> to Agent to enable.
        {canProduceData && " Drag purple handle for data."}
      </CardContent>
      
      {/* Dedicated handle for general "attachment" to an agent */}
      <Handle 
        type="source"
        position={Position.Right}
        id="tool_attachment_out" // Specific ID for enablement
        style={{ background: '#a5b4fc', top: '30%', width:10, height:10 }} // Indigo-ish
        title="Enable this Tool on an Agent"
      />

      {/* Dedicated handle if the tool can produce data output directly */}
      {canProduceData && (
        <Handle 
          type="source" 
          position={Position.Right} 
          id="tool_output_data" // Specific ID for data output
          style={{ background: '#7c3aed', top: '70%', width:10, height:10 }} // Purple for data
          title="Tool Data Output"
        />
      )}
    </Card>
  );
};

export default TFrameXToolNode;