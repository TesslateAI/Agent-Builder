import React, { useCallback, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Webhook, X, Globe } from 'lucide-react';

const WebhookTriggerNode = memo(({ id, data, selected }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const deleteNode = useStore((state) => state.deleteNode);
  
  const isEnabled = data.enabled !== false;
  
  const handleChange = useCallback((evt) => {
    const { name, value, type, checked } = evt.target;
    updateNodeData(id, { [name]: type === 'checkbox' ? checked : value });
  }, [id, updateNodeData]);
  
  return (
    <Card className={`w-72 shadow-lg bg-card text-card-foreground relative border-0 node-trigger
      ${selected ? 'ring-2 ring-primary shadow-lg' : 'hover:shadow-md'}
      ${!isEnabled ? 'opacity-70' : ''}
      transition-all duration-200`}>
      
      <Handle 
        type="source" 
        position={Position.Right} 
        id="output" 
        className="w-3 h-3 border-2 bg-warning/80 border-warning"
        data-handletype="data"
        title="Trigger Output"
        style={{ top: '50%' }}
      />
      
      {/* Delete button */}
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => deleteNode(id)}
        className="absolute top-1 right-1 h-6 w-6 p-0 hover:bg-destructive/10"
        title="Delete trigger"
      >
        <X className="h-4 w-4 text-destructive" />
      </Button>
      
      <CardHeader className="p-3">
        <div className="flex items-center space-x-2">
          <Webhook className="h-5 w-5 text-warning flex-shrink-0" />
          <Input
            name="label"
            value={data.label || 'Webhook Trigger'}
            onChange={handleChange}
            className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate" 
            placeholder="Trigger Label"
          />
        </div>
        <CardDescription className="text-xs mt-1">
          HTTP endpoint that triggers flows when receiving requests
        </CardDescription>
      </CardHeader>
      
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-60 overflow-y-auto">
        <div>
          <Label className="text-xs font-medium block mb-1">Webhook URL:</Label>
          <Input
            name="url"
            value={data.url || ''}
            onChange={handleChange}
            placeholder="https://api.example.com/webhook"
            className="text-xs h-7 border-input font-mono"
          />
        </div>
        
        <div>
          <Label className="text-xs font-medium block mb-1">HTTP Method:</Label>
          <select 
            name="method"
            value={data.method || 'POST'}
            onChange={handleChange}
            className="w-full text-xs h-7 border border-input rounded-md px-2 bg-background"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </select>
        </div>
        
        <div className="flex items-center justify-between mt-2">
          <Badge 
            variant={isEnabled ? 'default' : 'secondary'}
            className={`text-xs ${isEnabled ? 'bg-warning/20 text-warning-foreground border-warning/30' : 'bg-muted text-muted-foreground'}`}
          >
            {isEnabled ? 'Active' : 'Inactive'}
          </Badge>
          
          {data.url && (
            <div className="flex items-center">
              <Globe className="h-3 w-3 mr-1 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Endpoint Ready</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});

WebhookTriggerNode.displayName = 'WebhookTriggerNode';

export default WebhookTriggerNode;