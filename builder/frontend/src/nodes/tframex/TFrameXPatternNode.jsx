// frontend/src/nodes/tframex/TFrameXPatternNode.jsx
// builder/frontend/src/nodes/tframex/TFrameXPatternNode.jsx
import React, { useCallback, useRef, useEffect, useState, useMemo } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Puzzle, PlusCircle, Trash2, Users, Settings2, Route, GitBranch, Link2 } from 'lucide-react';

const PatternListItem = ({ parentNodeId, paramName, agentIdInSlot, index, onRemove, getAgentNameById }) => {
    const itemRef = useRef(null);
    const [handleTop, setHandleTop] = useState('50%');

    useEffect(() => {
        if (itemRef.current) {
            // Calculate position relative to the node for the handle
            const nodeElement = document.querySelector(`[data-id="${parentNodeId}"] .react-flow__renderer`); // Be more specific if needed
            if (nodeElement) {
                const nodeRect = nodeElement.getBoundingClientRect();
                const itemRect = itemRef.current.getBoundingClientRect();
                const relativeTop = itemRect.top - nodeRect.top + (itemRect.height / 2);
                setHandleTop(`${relativeTop}px`);
            } else { // Fallback using offsetParent if direct node not found
                 const parentEl = itemRef.current.offsetParent;
                 if (parentEl) {
                    const offsetTop = itemRef.current.offsetTop + (itemRef.current.offsetHeight / 2);
                    setHandleTop(`${offsetTop}px`);
                 }
            }
        }
    }, [parentNodeId, agentIdInSlot]); // Recalc if agentIdInSlot changes (e.g. item re-renders)

    return (
        <div ref={itemRef} className="flex items-center space-x-2 p-1.5 border border-dashed border-input rounded hover:border-primary/70 transition-colors relative my-1 bg-background/30">
            <Handle
                type="target"
                position={Position.Left}
                id={`pattern_list_item_input_${paramName}_${index}`}
                style={{ background: '#4CAF50', top: handleTop, left: -12, width:10, height:10, zIndex:1 }}
                title={`Connect Agent to ${paramName} slot #${index + 1}`}
                isConnectable={true}
            />
            <Users className="h-4 w-4 text-green-600 flex-shrink-0 ml-1" />
            <div className="flex-grow text-xs truncate">
                {agentIdInSlot ? (
                    <span className="font-medium text-green-700" title={getAgentNameById(agentIdInSlot)}>{getAgentNameById(agentIdInSlot)}</span>
                ) : (
                    <span className="text-muted-foreground italic">Slot Empty - Connect Agent</span>
                )}
            </div>
            <Button variant="ghost" size="icon" onClick={() => onRemove(paramName, index)} className="h-6 w-6 p-0.5 hover:bg-destructive/10">
                <Trash2 className="h-3.5 w-3.5 text-destructive"/>
            </Button>
        </div>
    );
};


const TFrameXPatternNode = ({ id, data, type: tframexPatternId }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const allAgents = useStore((state) => state.tframexComponents.agents);
  const allPatternsFromStore = useStore((state) => state.tframexComponents.patterns); // Renamed to avoid conflict
  const nodes = useStore((state) => state.nodes); // For resolving agent names from canvas

  const patternDefinition = useStore(state => 
    state.tframexComponents.patterns.find(p => p.id === tframexPatternId)
  );

  // Memoize options for select dropdowns to prevent re-computation on every render
  const agentOptions = useMemo(() => allAgents.map(agent => ({ value: agent.id, label: `${agent.name} (Agent)` })), [allAgents]);
  const patternOptions = useMemo(() => allPatternsFromStore.map(p => ({ value: p.id, label: `${p.name} (Pattern)` })), [allPatternsFromStore]);
  const defaultRouteOptions = useMemo(() => [...agentOptions, ...patternOptions], [agentOptions, patternOptions]);


  const getAgentNameById = useCallback((targetId) => {
    if (!targetId) return "Unassigned";
    // Check nodes on canvas first for their current label
    const canvasNode = nodes.find(n => n.id === targetId || n.data.tframex_component_id === targetId);
    if (canvasNode) return canvasNode.data.label || canvasNode.data.tframex_component_id || targetId;
    
    // Fallback to definitions from store
    const agentDef = allAgents.find(a => a.id === targetId);
    if (agentDef) return agentDef.name;
    const patternDef = allPatternsFromStore.find(p => p.id === targetId);
    if (patternDef) return patternDef.name;
    
    return targetId; // Return ID if no name found
  }, [nodes, allAgents, allPatternsFromStore]);
  
  const handleSimpleChange = useCallback((paramName, newValue) => {
    let val = newValue;
    const paramSchema = patternDefinition?.constructor_params_schema?.[paramName];
    if (paramSchema?.type_hint?.toLowerCase().includes('int')) {
        val = newValue === '' ? null : parseInt(newValue, 10);
        if (isNaN(val)) val = null; // Or some default like 0 or keep as is for validation
    } else if (paramSchema?.type_hint?.toLowerCase().includes('bool')) {
        val = newValue; 
    } else if (paramSchema?.type_hint?.toLowerCase().includes('float')) {
        val = newValue === '' ? null : parseFloat(newValue);
        if (isNaN(val)) val = null;
    }
    updateNodeData(id, { ...data, [paramName]: val });
  }, [id, updateNodeData, patternDefinition, data]);

  const addListItem = useCallback((paramName) => {
    const currentList = Array.isArray(data[paramName]) ? [...data[paramName]] : [];
    updateNodeData(id, { ...data, [paramName]: [...currentList, null] }); 
  }, [id, updateNodeData, data]);

  const removeListItem = useCallback((paramName, index) => {
    const currentList = Array.isArray(data[paramName]) ? [...data[paramName]] : [];
    const newList = currentList.filter((_, i) => i !== index);
    updateNodeData(id, { ...data, [paramName]: newList });
  }, [id, updateNodeData, data]);

  const handleRouteKeyChange = useCallback((oldKey, newKey) => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    if (oldKey === newKey || newKey.trim() === "") return;
    if (newKey in currentRoutes && oldKey !== newKey) {
        alert(`Route key "${newKey}" already exists.`);
        return; 
    }
    const value = currentRoutes[oldKey];
    delete currentRoutes[oldKey];
    currentRoutes[newKey.trim()] = value;
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);

  const handleRouteValueChange = useCallback((key, newValue) => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    currentRoutes[key] = newValue || null; // Store null if empty selection
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);

  const addRouteItem = useCallback(() => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    let newKeyBase = `route_key`;
    let newKey = newKeyBase;
    let i = 1;
    while(currentRoutes.hasOwnProperty(newKey)) {
        newKey = `${newKeyBase}_${i}`;
        i++;
    }
    updateNodeData(id, { ...data, routes: { ...currentRoutes, [newKey]: null } }); // Initialize value with null
  }, [id, updateNodeData, data]);

  const removeRouteItem = useCallback((keyToRemove) => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    delete currentRoutes[keyToRemove];
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);


  if (!patternDefinition) {
    return <Card className="w-80 p-2 border-destructive bg-destructive/10"><CardHeader><CardTitle className="text-destructive-foreground">Error: Pattern Unknown</CardTitle></CardHeader><CardContent className="text-destructive-foreground/80">Definition for '{tframexPatternId}' not found.</CardContent></Card>;
  }

  const renderParameterInput = (paramName, paramSchema) => {
    const value = data[paramName];
    const inputId = `${id}-${paramName}`;
    const label = paramName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const placeholder = paramSchema.default !== "REQUIRED" && paramSchema.default !== undefined ? String(paramSchema.default) : "";

    const listAgentParams = ['participant_agent_names', 'tasks', 'steps']; // From TFrameXPatternNode definition
    if (paramSchema.type_hint?.toLowerCase().includes('list') && listAgentParams.includes(paramName)) {
      const currentList = Array.isArray(value) ? value : [];
      return (
        <div className="space-y-1 p-1.5 border border-input rounded-md bg-background/40">
          {currentList.length === 0 && <p className="text-xs text-muted-foreground italic p-1">No slots. Add one below.</p>}
          {currentList.map((agentIdInSlot, index) => (
            <PatternListItem
                key={`${id}-${paramName}-${index}-${agentIdInSlot || 'empty'}`} 
                parentNodeId={id}
                paramName={paramName}
                agentIdInSlot={agentIdInSlot}
                index={index}
                onRemove={removeListItem}
                getAgentNameById={getAgentNameById}
            />
          ))}
          <Button variant="outline" size="sm" onClick={() => addListItem(paramName)} className="text-xs h-7 w-full mt-1">
             <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add Slot
          </Button>
        </div>
      );
    }
    
    if (paramName === 'routes' && paramSchema.type_hint?.toLowerCase().includes('dict')) {
        return ( 
            <div className="space-y-1.5 p-1.5 border border-input rounded-md bg-background/30">
                {Object.entries(value || {}).map(([routeKey, targetName], index) => (
                     <div key={index} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_auto] gap-1.5 items-center">
                        <Input 
                            value={routeKey} 
                            onChange={(e) => handleRouteKeyChange(routeKey, e.target.value)}
                            placeholder="Route Key"
                            className="text-xs h-8 border-input"
                        />
                        <Select value={targetName || ""} onValueChange={(val) => handleRouteValueChange(routeKey, val)}>
                            <SelectTrigger className="h-8 text-xs border-input w-full">
                                <SelectValue placeholder="-- Select Target --" />
                            </SelectTrigger>
                            <SelectContent>
                                {defaultRouteOptions.map(opt => <SelectItem key={opt.value} value={opt.value} className="text-xs">{opt.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        <Button variant="ghost" size="icon" onClick={() => removeRouteItem(routeKey)} className="h-7 w-7 p-1 hover:bg-destructive/10">
                            <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                        </Button>
                    </div>
                ))}
                {Object.keys(value || {}).length === 0 && <p className="text-xs text-muted-foreground italic p-1">No routes defined.</p>}
                <Button variant="outline" size="sm" onClick={addRouteItem} className="text-xs h-7 w-full mt-1">
                    <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add Route
                </Button>
            </div>
        );
    }

    const singleAgentParams = ['router_agent_name', 'moderator_agent_name', 'default_route'];
    if (singleAgentParams.includes(paramName)) {
        const connectedAgentId = data[paramName]; // This should be an ID
        const placeholderText = paramName === 'default_route' ? "-- Select Target --" : "-- Select Agent --";
        const optionsForSelect = paramName === 'default_route' ? defaultRouteOptions : agentOptions;
        return (
            <div className="relative p-1.5 border border-dashed border-amber-500/50 rounded-md bg-background/30 hover:border-amber-500 transition-colors">
                <Handle
                    type="target"
                    position={Position.Left}
                    id={`pattern_agent_input_${paramName}`} // Unique handle ID
                    style={{ background: '#F59E0B', top: '50%', left: -12, width:10, height:10, transform: 'translateY(-50%)', zIndex: 1 }}
                    title={`Connect Agent/Pattern for ${label}`}
                    isConnectable={true}
                />
                <Link2 className="h-4 w-4 text-amber-600 absolute top-1/2 -translate-y-1/2 left-2.5" />
                <div className="pl-8">
                    {connectedAgentId ? (
                         <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-amber-700 truncate" title={getAgentNameById(connectedAgentId)}>{getAgentNameById(connectedAgentId)}</span>
                            <Button variant="ghost" size="icon" onClick={() => handleSimpleChange(paramName, null)} className="h-6 w-6 p-0.5 hover:bg-destructive/10">
                                <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                            </Button>
                        </div>
                    ) : (
                        <Select value={value || ""} onValueChange={(val) => handleSimpleChange(paramName, val)}>
                            <SelectTrigger className="w-full h-8 text-xs border-input"> <SelectValue placeholder={placeholderText} /> </SelectTrigger>
                            <SelectContent>
                                {optionsForSelect.map(opt => (
                                    <SelectItem key={opt.value} value={opt.value} className="text-xs">
                                        {opt.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                </div>
            </div>
        );
    }

    if (paramSchema.type_hint?.toLowerCase().includes('bool')) {
      return (
         <Checkbox
            id={inputId}
            checked={!!value}
            onCheckedChange={(checked) => handleSimpleChange(paramName, checked)}
            labelClassName="text-xs"
          >
            {label}
          </Checkbox>
      );
    }
    if (paramSchema.type_hint?.toLowerCase().includes('int') || paramSchema.type_hint?.toLowerCase().includes('float')) {
      return (
        <Input id={inputId} type="number" value={value === null || value === undefined ? '' : String(value)} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={placeholder} className="text-xs h-8 border-input"/>
      );
    }
    const isTextarea = paramSchema.description?.toLowerCase().includes("long text") || 
                       paramSchema.description?.toLowerCase().includes("multiline") ||
                       paramSchema.type_hint?.toLowerCase().includes("textarea");
    if (isTextarea) {
        return <Textarea id={inputId} value={value || ''} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={placeholder} className="text-xs min-h-[60px] border-input" rows={3}/>;
    }
    return <Input id={inputId} type="text" value={value || ''} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={placeholder} className="text-xs h-8 border-input"/>;
  };
  
  const hasDynamicRouteOutputs = tframexPatternId === 'RouterPattern' && data.routes && Object.keys(data.routes).length > 0;
  const outputHandleTop = '50px'; // Consistent vertical position for main flow handles


  // Calculate dynamic output handle positions for RouterPattern
  const routeOutputHandles = useMemo(() => {
    if (!hasDynamicRouteOutputs) return [];
    
    const routeKeys = Object.keys(data.routes);
    const numHandles = routeKeys.length;
    // Define vertical spread range, e.g., from 25% to 75% of node height.
    // This is an approximation. A more precise calculation would need node height.
    const startPercent = 25;
    const endPercent = 75;
    const totalSpreadPercent = endPercent - startPercent;

    return routeKeys.map((routeKey, index) => {
        let topPercent = 50; // Default if only one handle
        if (numHandles > 1) {
            topPercent = startPercent + (index / (numHandles - 1)) * totalSpreadPercent;
        }
        return {
            key: `route-out-${id}-${routeKey}`,
            id: `output_route_${routeKey.replace(/[\s.:;()]/g, '_')}`, // Sanitize ID
            top: `${topPercent}%`,
            title: `Output for route: ${routeKey}`
        };
    });
  }, [hasDynamicRouteOutputs, data.routes, id]);


  return (
    <Card className="w-[26rem] shadow-lg border-border bg-card text-card-foreground">
      <Handle type="target" position={Position.Left} id="input_flow_in" style={{ background: '#60a5fa', top: outputHandleTop, zIndex: 1 }} title="Flow Input" />
      
      {routeOutputHandles.map(handleProps => (
          <Handle
              key={handleProps.key}
              type="source"
              position={Position.Right}
              id={handleProps.id}
              style={{ top: handleProps.top, background: '#818cf8', width: 10, height: 10, zIndex: 1 }}
              title={handleProps.title}
          />
      ))}
      
      {!hasDynamicRouteOutputs && (
        <Handle type="source" position={Position.Right} id="output_flow_out" style={{ background: '#60a5fa', top: outputHandleTop, zIndex: 1 }} title="Flow Output" />
      )}

      <CardHeader className="p-3 border-b border-border cursor-grab active:cursor-grabbing">
         <div className="flex items-center space-x-2">
            <Puzzle className="h-5 w-5 text-primary flex-shrink-0" />
             <Input 
                value={data.label || tframexPatternId} 
                onChange={(e) => updateNodeData(id, { label: e.target.value })} 
                className="text-base font-semibold !p-0 !border-0 !bg-transparent focus:!ring-0 h-auto truncate"
                placeholder="Pattern Label"
            />
        </div>
        {patternDefinition.description && <CardDescription className="text-xs mt-1 line-clamp-3">{patternDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-[24rem] overflow-y-auto pattern-params-content">
        {patternDefinition.constructor_params_schema && Object.entries(patternDefinition.constructor_params_schema).map(([paramName, paramSchema]) => (
          <div key={paramName}>
            <Label htmlFor={`${id}-${paramName}`} className="text-xs font-medium block mb-1.5">
              {paramName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} 
              <span className="text-muted-foreground/80 text-xs"> ({paramSchema.type_hint || 'any'})
                {paramSchema.default === "REQUIRED" && <span className="text-destructive"> *</span>}
              </span>:
            </Label>
            {renderParameterInput(paramName, paramSchema)}
            {paramSchema.description && <p className="text-xs text-muted-foreground/70 mt-0.5 leading-tight">{paramSchema.description}</p>}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default TFrameXPatternNode;