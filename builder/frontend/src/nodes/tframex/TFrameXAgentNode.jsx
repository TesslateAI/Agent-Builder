// builder/frontend/src/nodes/tframex/TFrameXAgentNode.jsx
import React, { useCallback, useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
// import { Checkbox } from '@/components/ui/checkbox'; // Assuming you have a Checkbox component
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"; // For tool selection
import { Cog, Wrench, PlusCircle, Trash2, Zap } from 'lucide-react'; // Added Zap for tool input

// Helper for Checkbox if not available (simplified)
const SimpleCheckbox = ({ id, checked, onCheckedChange, children }) => (
    <div className="flex items-center space-x-2 my-1">
        <input type="checkbox" id={id} checked={checked} onChange={(e) => onCheckedChange(e.target.checked)} className="form-checkbox h-4 w-4 text-primary border-border rounded focus:ring-primary" />
        <Label htmlFor={id} className="text-sm font-normal">{children}</Label>
    </div>
);


const TFrameXAgentNode = ({ id, data, type: tframexAgentId }) => { // type is the TFrameX agent name
  const updateNodeData = useStore((state) => state.updateNodeData);
  const allTools = useStore((state) => state.tframexComponents.tools); // For tool selection
  
  const agentDefinition = useStore(state => 
    state.tframexComponents.agents.find(a => a.id === tframexAgentId)
  );

  const [localTemplateVars, setLocalTemplateVars] = useState(data.template_vars_config || {});

  const handleChange = useCallback((evt) => {
    const { name, value, type: inputType, checked } = evt.target;
    let valToUpdate = inputType === 'checkbox' ? checked : value;
    if (inputType === 'number') valToUpdate = value === '' ? null : parseInt(value, 10);
    
    updateNodeData(id, { [name]: valToUpdate });
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
    updateNodeData(id, { template_vars_config: newVars });
  };
  
  const addTemplateVarField = () => {
    const newKey = `var_${Object.keys(localTemplateVars).length + 1}`;
    handleTemplateVarChange(newKey, ""); // Add an empty var
  };

  const removeTemplateVarField = (keyToRemove) => {
    const newVars = { ...localTemplateVars };
    delete newVars[keyToRemove];
    setLocalTemplateVars(newVars);
    updateNodeData(id, { template_vars_config: newVars });
  };

  const inputHandles = [
    { id: 'input_message_in', position: Position.Left, label: 'Input Msg', style: { top: '30%' } },
  ];
  const outputHandles = [
    { id: 'output_message_out', position: Position.Right, label: 'Output Msg', style: { top: '50%' } }
  ];

  if (!agentDefinition) {
    return <Card className="w-64 p-2 border-destructive"><CardHeader><CardTitle>Error: Agent Unknown</CardTitle></CardHeader><CardContent>Definition for '{tframexAgentId}' not found.</CardContent></Card>;
  }
  
  const canUseTools = agentDefinition.config_options?.can_use_tools;
  const stripThink = data.strip_think_tags_override !== undefined 
    ? data.strip_think_tags_override 
    : agentDefinition.config_options?.strip_think_tags;

  return (
    <Card className="w-72 shadow-lg border-border bg-card text-card-foreground">
      <CardHeader className="p-3 border-b border-border">
        <div className="flex items-center space-x-2">
            <Cog className="h-5 w-5 text-primary" />
            <CardTitle className="text-base font-semibold">{data.label || tframexAgentId}</CardTitle>
        </div>
        {agentDefinition.description && <CardDescription className="text-xs mt-1">{agentDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-3 space-y-3 text-sm nodrag">
        <div>
          <Label htmlFor={`${id}-label`} className="text-xs">Display Label:</Label>
          <Input id={`${id}-label`} name="label" value={data.label || tframexAgentId} onChange={handleChange} className="text-xs h-8" />
        </div>

        {canUseTools && (
          <div>
            <Label className="text-xs font-medium block mb-1">Enabled Tools:</Label>
            <div className="max-h-28 overflow-y-auto space-y-1 border border-border p-2 rounded-md bg-background/50">
              {allTools.length > 0 ? allTools.map(tool => (
                <SimpleCheckbox
                  key={tool.id}
                  id={`${id}-tool-${tool.id}`}
                  checked={(data.selected_tools || []).includes(tool.id)}
                  onCheckedChange={() => handleToolSelectionChange(tool.id)}
                >
                  {tool.name} <span className="text-muted-foreground text-xs ml-1 truncate" title={tool.description}>({tool.description.slice(0,20)}...)</span>
                </SimpleCheckbox>
              )) : <p className="text-xs text-muted-foreground">No tools registered.</p>}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Connect tools to the <Zap className="inline h-3 w-3 text-indigo-400" /> handle or select above.</p>
          </div>
        )}
        
        <div>
            <Label className="text-xs font-medium block mb-1">Template Variables (for System Prompt):</Label>
            <div className="space-y-1.5">
                {Object.entries(localTemplateVars).map(([key, value]) => (
                    <div key={key} className="flex items-center space-x-1.5">
                        <Input value={key} readOnly className="text-xs h-7 w-2/5 bg-muted/50" title="Variable Name (Key)"/>
                        <Input 
                            value={value} 
                            onChange={(e) => handleTemplateVarChange(key, e.target.value)} 
                            placeholder="Value for prompt"
                            className="text-xs h-7 w-3/5"
                        />
                        <Button variant="ghost" size="icon" onClick={() => removeTemplateVarField(key)} className="h-7 w-7 p-1">
                            <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                        </Button>
                    </div>
                ))}
            </div>
            <Button variant="outline" size="sm" onClick={addTemplateVarField} className="mt-1.5 text-xs h-7">
                <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add Template Var
            </Button>
        </div>

        <SimpleCheckbox
            id={`${id}-strip_think`}
            checked={!!stripThink} // Ensure boolean
            onCheckedChange={(checked) => updateNodeData(id, { strip_think_tags_override: checked })}
        >
            Strip think tags from output
        </SimpleCheckbox>

      </CardContent>
      
      {/* Message Input Handle */}
      {inputHandles.map(h => (
        <Handle key={h.id} type="target" position={h.position} id={h.id} style={{ background: '#555', ...h.style }} title={h.label} />
      ))}

      {/* Tool Attachment Input Handle (if agent can use tools) */}
      {canUseTools && (
        <Handle
            type="target"
            position={Position.Left}
            id="tool_input_handle" // Specific ID for tool attachments
            style={{ background: '#a5b4fc', top: '70%', width: 10, height: 10 }} // Indigo-ish
            title="Connect Tool for Enabling"
        />
      )}
      
      {/* Message Output Handle */}
      {outputHandles.map(h => (
        <Handle key={h.id} type="source" position={h.position} id={h.id} style={{ background: '#555', ...h.style }} title={h.label} />
      ))}
    </Card>
  );
};

export default TFrameXAgentNode;