import React, { useCallback, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, X, Timer } from 'lucide-react';

const ScheduleTriggerNode = memo(({ id, data, selected }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const deleteNode = useStore((state) => state.deleteNode);
  
  const isEnabled = data.enabled !== false;
  
  const handleChange = useCallback((evt) => {
    const { name, value, type, checked } = evt.target;
    updateNodeData(id, { [name]: type === 'checkbox' ? checked : value });
  }, [id, updateNodeData]);
  
  const formatScheduleDisplay = () => {
    if (data.cron && data.cron.trim()) {
      return `Cron: ${data.cron}`;
    }
    if (data.interval) {
      const unit = data.intervalUnit || 'minutes';
      return `Every ${data.interval} ${unit}`;
    }
    return 'No schedule set';
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
        className="w-3 h-3 border-2 bg-success/80 border-success"
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
          <Clock className="h-5 w-5 text-success flex-shrink-0" />
          <Input
            name="label"
            value={data.label || 'Schedule Trigger'}
            onChange={handleChange}
            className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate" 
            placeholder="Trigger Label"
          />
        </div>
        <CardDescription className="text-xs mt-1">
          Time-based triggers using cron expressions or intervals
        </CardDescription>
      </CardHeader>
      
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-60 overflow-y-auto">
        <div>
          <Label className="text-xs font-medium block mb-1">Schedule Type:</Label>
          <select 
            name="scheduleType"
            value={data.scheduleType || 'interval'}
            onChange={handleChange}
            className="w-full text-xs h-7 border border-input rounded-md px-2 bg-background"
          >
            <option value="interval">Interval</option>
            <option value="cron">Cron Expression</option>
          </select>
        </div>
        
        {(data.scheduleType === 'interval' || !data.scheduleType) && (
          <div className="flex space-x-2">
            <div className="flex-1">
              <Label className="text-xs font-medium block mb-1">Every:</Label>
              <Input
                name="interval"
                type="number"
                value={data.interval || '5'}
                onChange={handleChange}
                placeholder="5"
                className="text-xs h-7 border-input"
              />
            </div>
            <div className="flex-1">
              <Label className="text-xs font-medium block mb-1">Unit:</Label>
              <select 
                name="intervalUnit"
                value={data.intervalUnit || 'minutes'}
                onChange={handleChange}
                className="w-full text-xs h-7 border border-input rounded-md px-2 bg-background"
              >
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </select>
            </div>
          </div>
        )}
        
        {data.scheduleType === 'cron' && (
          <div>
            <Label className="text-xs font-medium block mb-1">Cron Expression:</Label>
            <Input
              name="cron"
              value={data.cron || ''}
              onChange={handleChange}
              placeholder="0 */5 * * * *"
              className="text-xs h-7 border-input font-mono"
            />
            <div className="text-xs text-muted-foreground mt-1">
              Format: second minute hour day month weekday
            </div>
          </div>
        )}
        
        <div className="flex items-center justify-between mt-2">
          <Badge 
            variant={isEnabled ? 'default' : 'secondary'}
            className={`text-xs ${isEnabled ? 'bg-success/20 text-success-foreground border-success/30' : 'bg-muted text-muted-foreground'}`}
          >
            {isEnabled ? 'Scheduled' : 'Inactive'}
          </Badge>
          
          <div className="flex items-center">
            <Timer className="h-3 w-3 mr-1 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">{formatScheduleDisplay()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

ScheduleTriggerNode.displayName = 'ScheduleTriggerNode';

export default ScheduleTriggerNode;