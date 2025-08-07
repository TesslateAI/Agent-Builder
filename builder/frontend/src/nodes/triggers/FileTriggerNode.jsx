import React, { useCallback, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { FolderOpen, X, Eye } from 'lucide-react';

const FileTriggerNode = memo(({ id, data, selected }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const deleteNode = useStore((state) => state.deleteNode);
  
  const isEnabled = data.enabled !== false;
  
  const handleChange = useCallback((evt) => {
    const { name, value, type, checked } = evt.target;
    updateNodeData(id, { [name]: type === 'checkbox' ? checked : value });
  }, [id, updateNodeData]);
  
  const handleEventChange = useCallback((event, checked) => {
    const currentEvents = data.events || [];
    const newEvents = checked 
      ? [...currentEvents, event]
      : currentEvents.filter(e => e !== event);
    updateNodeData(id, { events: newEvents });
  }, [id, updateNodeData, data.events]);
  
  const formatWatchPath = () => {
    if (data.path) {
      const pattern = data.pattern || '*';
      return `${data.path}/${pattern}`;
    }
    return 'No path configured';
  };
  
  return (
    <Card className={`w-72 shadow-lg bg-card text-card-foreground relative border-0 node-trigger
      ${selected ? 'ring-2 ring-primary shadow-lg' : 'hover:shadow-md'}
      ${!isEnabled ? 'opacity-70' : ''}
      transition-all duration-200`}>
      
      <Handle 
        type="source" 
        position={Position.Right} 
        id="output" 
        className="w-3 h-3 border-2 bg-accent/80 border-accent"
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
          <FolderOpen className="h-5 w-5 text-accent-foreground flex-shrink-0" />
          <Input
            name="label"
            value={data.label || 'File Trigger'}
            onChange={handleChange}
            className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate" 
            placeholder="Trigger Label"
          />
        </div>
        <CardDescription className="text-xs mt-1">
          Watch file systems for changes and trigger flows
        </CardDescription>
      </CardHeader>
      
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-60 overflow-y-auto">
        <div>
          <Label className="text-xs font-medium block mb-1">Watch Path:</Label>
          <Input
            name="path"
            value={data.path || ''}
            onChange={handleChange}
            placeholder="/path/to/watch"
            className="text-xs h-7 border-input font-mono"
          />
        </div>
        
        <div>
          <Label className="text-xs font-medium block mb-1">File Pattern:</Label>
          <Input
            name="pattern"
            value={data.pattern || '*'}
            onChange={handleChange}
            placeholder="*.txt"
            className="text-xs h-7 border-input font-mono"
          />
        </div>
        
        <div>
          <Label className="text-xs font-medium block mb-2">Watch Events:</Label>
          <div className="space-y-2">
            {['created', 'modified', 'deleted', 'moved'].map(event => (
              <div key={event} className="flex items-center space-x-2">
                <Checkbox 
                  id={`event-${event}`}
                  checked={(data.events || []).includes(event)}
                  onCheckedChange={(checked) => handleEventChange(event, checked)}
                  className="h-3 w-3"
                />
                <Label htmlFor={`event-${event}`} className="text-xs capitalize">
                  {event}
                </Label>
              </div>
            ))}
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-2">
          <Badge 
            variant={isEnabled ? 'default' : 'secondary'}
            className={`text-xs ${isEnabled ? 'bg-accent/20 text-accent-foreground border-accent/30' : 'bg-muted text-muted-foreground'}`}
          >
            {isEnabled ? 'Watching' : 'Inactive'}
          </Badge>
          
          {data.path && (
            <div className="flex items-center">
              <Eye className="h-3 w-3 mr-1 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">FS Ready</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});

FileTriggerNode.displayName = 'FileTriggerNode';

export default FileTriggerNode;