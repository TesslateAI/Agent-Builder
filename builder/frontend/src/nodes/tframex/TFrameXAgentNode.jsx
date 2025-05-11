// frontend/src/nodes/tframex/TFrameXAgentNode.jsx
// builder/frontend/src/nodes/tframex/TFrameXAgentNode.jsx
import React, { useCallback, useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
// import { Textarea } from '@/components/ui/textarea'; // Not used directly, properties panel will handle
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox'; // Assuming you create this
import { Cog, Wrench, PlusCircle, Trash2, Zap, MessageSquare } from 'lucide-react';

const TFrameXAgentNode = ({ id, data, type: tframexAgentId }) => { 
  const updateNodeData = useStore((state) => state.updateNodeData);
  const allTools = useStore((state) => state.tframexComponents.tools); 
  
  const agentDefinition = useStore(state => 
    state.tframexComponents.agents.find(a => a.id === tframexAgentId)
  );

  // Local state for template vars is good for immediate UI feedback
  const [localTemplateVars, setLocalTemplateVars] = useState(data.template_vars_config || {});
   useEffect(() => { // Sync with global store if node data changes externally
        setLocalTemplateVars(data.template_vars_config || {});
    }, [data.template_vars_config]);


  const handleChange = useCallback((evt) => {
    const { name, value } = evt.target;
    updateNodeData(id, { [name]: value });
  }, [id, updateNodeData]);

  const handleToolSelectionChange = (toolName) => {
    const currentSelected = data.selected_tools || [];
    const newSelected = currentSelected.includes(toolName)
      ? currentSelected.filter(t => t !== toolName)
      : [...currentSelected, toolName];
    updateNodeData(id, { selected_tools: newSelected });
  };

  const handleTemplateVarChange = (key, value) => {
    const newVars = { ...localTemplateVars, [key]: value };
    setLocalTemplateVars(newVars);
    // Debounce or onBlur might be better for performance if typing rapidly
    updateNodeData(id, { template_vars_config: newVars });
  };
  
  const addTemplateVarField = () => {
    let newKeyBase = `var`;
    let newKey = newKeyBase;
    let i = 1;
    // Ensure unique key
    while(localTemplateVars.hasOwnProperty(newKey)) {
        newKey = `${newKeyBase}_${i}`;
        i++;
    }
    handleTemplateVarChange(newKey, ""); 
  };

  const removeTemplateVarField = (keyToRemove) => {
    const newVars = { ...localTemplateVars };
    delete newVars[keyToRemove];
    setLocalTemplateVars(newVars);
    updateNodeData(id, { template_vars_config: newVars });
  };

  if (!agentDefinition) {
    return (
        <Card className="w-64 p-2 border-destructive bg-destructive/10">
            <CardHeader className="p-2">
                <CardTitle className="text-sm text-destructive-foreground">Error: Agent Unknown</CardTitle>
            </CardHeader>
            <CardContent className="p-2 text-xs text-destructive-foreground/80">
                Definition for agent type '{tframexAgentId}' not found. Was it registered?
            </CardContent>
        </Card>
    );
  }
  
  const canUseTools = agentDefinition.config_options?.can_use_tools;
  // Use override if present, otherwise definition's default, then false
  const stripThink = data.strip_think_tags_override !== undefined 
    ? data.strip_think_tags_override 
    : (agentDefinition.config_options?.strip_think_tags !== undefined 
        ? agentDefinition.config_options.strip_think_tags 
        : false);


  return (
    <Card className="w-72 shadow-lg border-border bg-card text-card-foreground">
      <Handle 
        type="target" 
        position={Position.Left} 
        id="input_message_in" 
        style={{ background: '#3b82f6', top: '30%' }} 
        title="Input Message" 
      />
      {canUseTools && (
        <Handle
            type="target"
            position={Position.Left}
            id="tool_input_handle" 
            style={{ background: '#8b5cf6', top: '70%' }} // Purple for tool connections
            title="Connect Tool for Enabling"
        />
      )}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="output_message_out" 
        style={{ background: '#3b82f6', top: '50%' }} 
        title="Output Message" 
      />

      <CardHeader className="p-3 border-b border-border cursor-grab active:cursor-grabbing">
        <div className="flex items-center space-x-2">
            <Cog className="h-5 w-5 text-primary flex-shrink-0" />
            <Input 
                name="label" 
                value={data.label || tframexAgentId} 
                onChange={handleChange} 
                className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-autotruncate"
                placeholder="Agent Label"
            />
        </div>
        {agentDefinition.description && <CardDescription className="text-xs mt-1 line-clamp-2">{agentDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-60 overflow-y-auto">
        {/* System Prompt editing is moved to PropertiesPanel */}
        {/* Selected tools display and template vars can remain for quick view/edit */}
        
        {canUseTools && (
          <div>
            <Label className="text-xs font-medium block mb-1">Enabled Tools (via connection or panel):</Label>
            <div className="max-h-28 overflow-y-auto space-y-1 border border-input p-2 rounded-md bg-background/50">
              {(data.selected_tools && data.selected_tools.length > 0) ? data.selected_tools.map(toolId => {
                const toolDef = allTools.find(t => t.id === toolId);
                return (
                    <div key={toolId} className="flex items-center text-xs">
                        <Wrench className="h-3 w-3 mr-1.5 text-indigo-400 flex-shrink-0" />
                        <span className="truncate" title={toolDef?.name || toolId}>
                            {toolDef?.name || toolId}
                        </span>
                    </div>
                );
              }) : <p className="text-xs text-muted-foreground italic">No tools explicitly enabled on this node. Connect tools to the <Zap className="inline h-3 w-3 text-indigo-400" /> handle.</p>}
            </div>
          </div>
        )}
        
        <div>
            <Label className="text-xs font-medium block mb-1">Template Variables (for System Prompt):</Label>
            <div className="space-y-1.5">
                {Object.entries(localTemplateVars).map(([key, value]) => (
                    <div key={key} className="flex items-center space-x-1.5">
                        <Input value={key} readOnly className="text-xs h-7 w-2/5 bg-muted/50 border-input" title="Variable Name (Key)"/>
                        <Input 
                            value={value} 
                            onChange={(e) => handleTemplateVarChange(key, e.target.value)} 
                            placeholder="Value"
                            className="text-xs h-7 w-3/5 border-input"
                        />
                        <Button variant="ghost" size="icon" onClick={() => removeTemplateVarField(key)} className="h-7 w-7 p-1 hover:bg-destructive/10">
                            <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                        </Button>
                    </div>
                ))}
                 {Object.keys(localTemplateVars).length === 0 && (
                    <p className="text-xs text-muted-foreground italic">No template variables configured for this node.</p>
                )}
            </div>
            <Button variant="outline" size="sm" onClick={addTemplateVarField} className="mt-1.5 text-xs h-7">
                <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add Template Var
            </Button>
        </div>

        <Checkbox
            id={`${id}-strip_think`}
            checked={!!stripThink} 
            onCheckedChange={(checked) => updateNodeData(id, { strip_think_tags_override: checked })}
            labelClassName="text-xs"
        >
            Strip tags from output
        </Checkbox>

      </CardContent>
    </Card>
  );
};

export default TFrameXAgentNode;