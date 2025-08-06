// frontend/src/components/PropertiesPanel.jsx
// NEW FILE
import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { XIcon, Cog, MessageSquare, Palette, Bot, Settings } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox'; // Assuming created
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import MCPServerPropertiesPanel from './MCPServerPropertiesPanel';


const PropertiesPanel = () => {
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const nodes = useStore((state) => state.nodes);
  const updateNodeData = useStore((state) => state.updateNodeData);
  const setSelectedNodeId = useStore((state) => state.setSelectedNodeId); // To close panel
  const tframexComponents = useStore((state) => state.tframexComponents);
  const models = useStore((state) => state.models);


  const [localData, setLocalData] = useState({});

  const selectedNode = React.useMemo(() => {
    return nodes.find((node) => node.id === selectedNodeId);
  }, [nodes, selectedNodeId]);

  useEffect(() => {
    if (selectedNode) {
      setLocalData({ ...selectedNode.data });
    } else {
      setLocalData({});
    }
  }, [selectedNode]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setLocalData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleTextareaChange = (name, value) => {
     setLocalData(prev => ({ ...prev, [name]: value }));
  };

  const handleApplyChanges = () => {
    if (selectedNodeId) {
      updateNodeData(selectedNodeId, localData);
      // Optionally, close panel or give feedback:
      // setSelectedNodeId(null);
    }
  };

  const handleClosePanel = () => {
      setSelectedNodeId(null); // This will also set isPropertiesPanelOpen to false via store logic
  };

  if (!selectedNode) {
    return null; // Or a placeholder if always visible but empty
  }

  const originalAgentDefinition = selectedNode.data.component_category === 'agent'
    ? tframexComponents.agents.find(a => a.id === selectedNode.data.tframex_component_id)
    : null;

  const originalPatternDefinition = selectedNode.data.component_category === 'pattern'
    ? tframexComponents.patterns.find(p => p.id === selectedNode.data.tframex_component_id)
    : null;

  const originalToolDefinition = selectedNode.data.component_category === 'tool'
    ? tframexComponents.tools.find(t => t.id === selectedNode.data.tframex_component_id)
    : null;


  const renderAgentProperties = () => {
    // Get current system prompt (either override or default)
    const currentSystemPrompt = localData.system_prompt_override || 
      originalAgentDefinition?.config_options?.system_prompt_template || 
      'No system prompt defined';

    const handleModelChange = (value) => {
      setLocalData(prev => ({ ...prev, model: value }));
    };

    const handleToolToggle = (toolId, checked) => {
      const currentTools = localData.selected_tools || [];
      const newTools = checked 
        ? [...currentTools, toolId]
        : currentTools.filter(t => t !== toolId);
      setLocalData(prev => ({ ...prev, selected_tools: newTools }));
    };

    return (
      <>
        <div className="mb-3">
          <Label htmlFor="prop-label" className="text-xs">Display Label</Label>
          <Input id="prop-label" name="label" value={localData.label || ''} onChange={handleInputChange} className="text-sm h-8 border-input" />
        </div>
        
        <div className="mb-3">
          <Label htmlFor="prop-model" className="text-xs flex items-center">
            <Bot className="h-3 w-3 mr-1" />
            Model
          </Label>
          <Select value={localData.model || 'default'} onValueChange={handleModelChange}>
            <SelectTrigger className="text-sm h-8">
              <SelectValue placeholder="Select a model" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default" className="text-sm">
                Default ({models.find(m => m.is_default)?.name || 'System Default'})
              </SelectItem>
              {models.filter(m => !m.is_default).map(model => (
                <SelectItem key={model.id} value={model.model_name} className="text-sm">
                  {model.name} ({model.provider})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {localData.model && localData.model !== 'default' && (
            <p className="text-xs text-muted-foreground mt-1">
              Using: {models.find(m => m.model_name === localData.model)?.model_name || localData.model}
            </p>
          )}
        </div>

        <div className="mb-3">
          <Label className="text-xs flex items-center mb-2">
            <Settings className="h-3 w-3 mr-1" />
            Available Tools
          </Label>
          <div className="space-y-2 max-h-32 overflow-y-auto border rounded-md p-2">
            {tframexComponents.tools.map(tool => (
              <div key={tool.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`tool-${tool.id}`}
                  checked={localData.selected_tools?.includes(tool.id) || false}
                  onCheckedChange={(checked) => handleToolToggle(tool.id, checked)}
                />
                <label 
                  htmlFor={`tool-${tool.id}`} 
                  className="text-xs cursor-pointer"
                >
                  {tool.name}
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-3">
          <Label htmlFor="prop-system_prompt" className="text-xs">Current System Prompt</Label>
          <Textarea
            id="prop-system_prompt"
            value={currentSystemPrompt}
            readOnly
            className="text-sm min-h-[80px] font-mono border-input bg-muted/30"
            rows={4}
          />
          <p className="text-xs text-muted-foreground mt-1">
            This shows the current system prompt. Edit below to override.
          </p>
        </div>

        <div className="mb-3">
          <Label htmlFor="prop-system_prompt_override" className="text-xs">System Prompt Override</Label>
          <Textarea
            id="prop-system_prompt_override"
            name="system_prompt_override"
            value={localData.system_prompt_override || ''}
            onChange={(e) => handleTextareaChange('system_prompt_override', e.target.value)}
            placeholder="Enter a custom system prompt to override the default..."
            className="text-sm min-h-[100px] font-mono border-input"
            rows={5}
          />
        </div>
        <div className="mb-3">
          <Checkbox
            id="prop-strip_think_tags_override"
            checked={localData.strip_think_tags_override !== undefined ? !!localData.strip_think_tags_override : (originalAgentDefinition?.config_options?.strip_think_tags || false)}
            onCheckedChange={(checked) => setLocalData(prev => ({ ...prev, strip_think_tags_override: checked }))}
          />
          <label htmlFor="prop-strip_think_tags_override" className="text-xs ml-2 cursor-pointer">
            Strip think tags from output
          </label>
        </div>
      </>
    );
  };

  const renderTextInputProperties = () => (
     <>
      <div className="mb-3">
        <Label htmlFor="prop-label" className="text-xs">Display Label</Label>
        <Input id="prop-label" name="label" value={localData.label || ''} onChange={handleInputChange} className="text-sm h-8 border-input" />
      </div>
      <div className="mb-3">
        <Label htmlFor="prop-text_content" className="text-xs">Text Content</Label>
        <Textarea
          id="prop-text_content"
          name="text_content"
          value={localData.text_content || ''}
          onChange={(e) => handleTextareaChange('text_content', e.target.value)}
          placeholder="Enter text/prompt here..."
          className="text-sm min-h-[150px] font-mono border-input"
          rows={8}
        />
      </div>
    </>
  );

  const renderPatternProperties = () => (
     <>
      <div className="mb-3">
        <Label htmlFor="prop-label" className="text-xs">Display Label</Label>
        <Input id="prop-label" name="label" value={localData.label || ''} onChange={handleInputChange} className="text-sm h-8 border-input" />
      </div>
       <p className="text-xs text-muted-foreground italic">
            Pattern-specific parameters (like agent lists, routes) are configured directly on the node itself.
            This panel is for general properties.
       </p>
       {originalPatternDefinition && (
           <div className="mt-2 p-2 border border-dashed border-input rounded-md bg-background/30">
               <p className="text-xs font-semibold text-muted-foreground">Pattern Type:</p>
               <p className="text-xs text-foreground">{originalPatternDefinition.name}</p>
               <p className="text-xs text-muted-foreground mt-1">{originalPatternDefinition.description}</p>
           </div>
       )}
    </>
  );

  const renderToolProperties = () => (
     <>
      <div className="mb-3">
        <Label htmlFor="prop-label" className="text-xs">Display Label</Label>
        <Input id="prop-label" name="label" value={localData.label || ''} onChange={handleInputChange} className="text-sm h-8 border-input" />
      </div>
       <p className="text-xs text-muted-foreground italic">
            Tools are primarily configured by connecting them to agents. Specific tool parameters for execution are usually handled by the agent calling the tool.
       </p>
        {originalToolDefinition && (
           <div className="mt-2 p-2 border border-dashed border-input rounded-md bg-background/30">
               <p className="text-xs font-semibold text-muted-foreground">Tool Type:</p>
               <p className="text-xs text-foreground">{originalToolDefinition.name}</p>
               <p className="text-xs text-muted-foreground mt-1">{originalToolDefinition.description}</p>
           </div>
       )}
    </>
  );

  let content;
  let titleIcon = <Palette className="h-5 w-5 mr-2 text-primary" />;
  let titleText = "Node Properties";
  let descriptionText = `Editing: ${localData.label || selectedNode.id}`;


  if (selectedNode.data.component_category === 'agent') {
    content = renderAgentProperties();
    titleIcon = <Cog className="h-5 w-5 mr-2 text-primary" />;
    titleText = "Agent Properties";
  } else if (selectedNode.type === 'textInput') {
    content = renderTextInputProperties();
    titleIcon = <MessageSquare className="h-5 w-5 mr-2 text-secondary" />;
    titleText = "Text Input Properties";
  } else if (selectedNode.data.component_category === 'pattern') {
    content = renderPatternProperties();
    titleIcon = <Cog className="h-5 w-5 mr-2 text-primary" />; // Example icon for patterns
    titleText = "Pattern Properties";
  } else if (selectedNode.data.component_category === 'tool') {
    content = renderToolProperties();
    titleIcon = <Cog className="h-5 w-5 mr-2 text-accent" />; // Example icon for tools
    titleText = "Tool Properties";
  } else if (selectedNode.data.component_category === 'mcp_server' || selectedNode.type === 'MCPServerNode') {
    // Use the specialized MCP Server Properties Panel
    return <MCPServerPropertiesPanel nodeId={selectedNodeId} nodeData={selectedNode.data} />;
  } else {
    content = <p className="text-sm text-muted-foreground">No editable properties for this node type.</p>;
  }

  return (
    // Updated className here with unified styling
    <div className="flex flex-col h-full bg-sidebar">
      <div className="p-3 border-b border-sidebar-border flex-shrink-0 h-16 flex flex-row justify-between items-center">
        <div className="flex items-center">
            {titleIcon}
            <div>
                <div className="text-base font-semibold text-sidebar-foreground">{titleText}</div>
                <div className="text-xs mt-0.5 truncate max-w-[250px] text-muted-foreground">{descriptionText}</div>
            </div>
        </div>
        <Button variant="ghost" size="icon" onClick={handleClosePanel} className="text-muted-foreground hover:text-foreground">
          <XIcon className="h-5 w-5" />
          <span className="sr-only">Close Properties</span>
        </Button>
      </div>
      <div className="flex-grow p-3 overflow-hidden">
        <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-y-auto p-4 space-y-4">
          {content}
        </div>
      </div>
      <div className="p-3 border-t border-sidebar-border flex-shrink-0">
        <Button onClick={handleApplyChanges} className="w-full" size="sm">
          Apply Changes
        </Button>
      </div>
    </div>
  );
};

export default PropertiesPanel;