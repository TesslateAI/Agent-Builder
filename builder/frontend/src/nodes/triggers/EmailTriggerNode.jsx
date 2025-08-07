import React, { useCallback, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Mail, X, Inbox } from 'lucide-react';

const EmailTriggerNode = memo(({ id, data, selected }) => {
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
        className="w-3 h-3 border-2 bg-info/80 border-info"
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
          <Mail className="h-5 w-5 text-info flex-shrink-0" />
          <Input
            name="label"
            value={data.label || 'Email Trigger'}
            onChange={handleChange}
            className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate" 
            placeholder="Trigger Label"
          />
        </div>
        <CardDescription className="text-xs mt-1">
          Monitor email accounts and trigger flows on new messages
        </CardDescription>
      </CardHeader>
      
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-60 overflow-y-auto">
        <div>
          <Label className="text-xs font-medium block mb-1">Email Address:</Label>
          <Input
            name="email"
            value={data.email || ''}
            onChange={handleChange}
            placeholder="user@gmail.com"
            className="text-xs h-7 border-input"
          />
        </div>
        
        <div>
          <Label className="text-xs font-medium block mb-1">IMAP Server:</Label>
          <Input
            name="host"
            value={data.host || 'imap.gmail.com'}
            onChange={handleChange}
            placeholder="imap.gmail.com"
            className="text-xs h-7 border-input"
          />
        </div>
        
        <div className="flex space-x-2">
          <div className="flex-1">
            <Label className="text-xs font-medium block mb-1">Port:</Label>
            <Input
              name="port"
              value={data.port || '993'}
              onChange={handleChange}
              placeholder="993"
              className="text-xs h-7 border-input"
            />
          </div>
          <div className="flex-1">
            <Label className="text-xs font-medium block mb-1">SSL:</Label>
            <select 
              name="ssl"
              value={data.ssl || 'true'}
              onChange={handleChange}
              className="w-full text-xs h-7 border border-input rounded-md px-2 bg-background"
            >
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-2">
          <Badge 
            variant={isEnabled ? 'default' : 'secondary'}
            className={`text-xs ${isEnabled ? 'bg-info/20 text-info-foreground border-info/30' : 'bg-muted text-muted-foreground'}`}
          >
            {isEnabled ? 'Monitoring' : 'Inactive'}
          </Badge>
          
          {data.email && (
            <div className="flex items-center">
              <Inbox className="h-3 w-3 mr-1 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">IMAP Ready</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});

EmailTriggerNode.displayName = 'EmailTriggerNode';

export default EmailTriggerNode;