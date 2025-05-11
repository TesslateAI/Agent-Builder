// builder/frontend/src/nodes/tframex/TFrameXPatternNode.jsx
import React, { useCallback, useRef, useEffect, useState } from 'react';
import { Handle, Position } from 'reactflow';
import { useStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Puzzle, PlusCircle, Trash2, Users, Settings2, Route, GitBranch } from 'lucide-react';

// Helper to calculate relative Y position for handles within a list
const getListItemHandleTop = (index, totalItems, itemHeightEstimate = 40, containerPadding = 8) => {
    // This is an estimate. For perfect alignment, each item would need to report its offset.
    const totalHeightEstimate = totalItems * itemHeightEstimate;
    const itemCenterY = (index + 0.5) * itemHeightEstimate;
    return `${(itemCenterY / totalHeightEstimate) * 100}%`; // Relative to the list container height
    // Or, if absolute within the node:
    // return containerPadding + itemCenterY; // in pixels
};


const PatternListItem = ({ parentNodeId, paramName, agentIdInSlot, index, totalItems, onRemove, onAgentSelect, getAgentNameById }) => {
    const itemRef = useRef(null);
    const [itemTop, setItemTop] = useState('50%'); // Default

    // This effect is an attempt to position handles more accurately after render.
    useEffect(() => {
        if (itemRef.current) {
            const nodeElement = document.querySelector(`[data-id="${parentNodeId}"]`);
            const contentElement = nodeElement?.querySelector('.pattern-params-content');
            if (itemRef.current && contentElement) {
                const itemRect = itemRef.current.getBoundingClientRect();
                const contentRect = contentElement.getBoundingClientRect();
                // Calculate the center of the item relative to the top of the contentElement
                const relativeTop = itemRect.top - contentRect.top + (itemRect.height / 2);
                setItemTop(`${relativeTop}px`);
            } else {
                // Fallback if precise calculation isn't possible (e.g., contentElement not found)
                // This could be a proportional positioning if needed, similar to getListItemHandleTop
                // For now, keep default or a simple proportional estimate if itemRef.current.offsetParent is available
                const parentHeight = itemRef.current.offsetParent?.clientHeight;
                if (parentHeight && totalItems > 0) {
                    setItemTop(`${((index + 0.5) / totalItems) * 100}%`);
                } else {
                    setItemTop('50%');
                }
            }
        }
    }, [parentNodeId, index, totalItems, agentIdInSlot]); // Re-calculate if items or parent change


    return (
        <div ref={itemRef} className="flex items-center space-x-2 p-1.5 border border-dashed border-border/50 rounded hover:border-primary/70 transition-colors relative">
            <Handle
                type="target"
                position={Position.Left}
                id={`pattern_list_item_input_${paramName}_${index}`}
                style={{ background: '#4CAF50', top: itemTop, transform: 'translateY(-50%)', left: -12, width:10, height:10 }}
                title={`Connect Agent to slot #${index + 1}`}
                isConnectable={true}
            />
            <Users className="h-4 w-4 text-green-600 flex-shrink-0" />
            <div className="flex-grow text-xs">
                {agentIdInSlot ? (
                    <span className="font-medium text-green-700">{getAgentNameById(agentIdInSlot)}</span>
                ) : (
                    <span className="text-muted-foreground italic">Slot Empty - Connect Agent</span>
                )}
            </div>
            <Button variant="ghost" size="icon" onClick={() => onRemove(paramName, index)} className="h-6 w-6 p-0.5">
                <Trash2 className="h-3.5 w-3.5 text-destructive"/>
            </Button>
        </div>
    );
};


const TFrameXPatternNode = ({ id, data, type: tframexPatternId }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const allAgents = useStore((state) => state.tframexComponents.agents);
  const allPatterns = useStore((state) => state.tframexComponents.patterns);
  const nodes = useStore((state) => state.nodes);

  const patternDefinition = useStore(state => 
    state.tframexComponents.patterns.find(p => p.id === tframexPatternId)
  );

  const getAgentNameById = (agentId) => {
    const agentNode = nodes.find(n => n.id === agentId || n.data.tframex_component_id === agentId);
    if (agentNode) return agentNode.data.label || agentNode.data.tframex_component_id;
    
    const agentDef = allAgents.find(a => a.id === agentId); // Fallback to definition name
    return agentDef?.name || agentId || "Unknown Agent";
  };
  
  const handleSimpleChange = useCallback((paramName, newValue) => {
    let val = newValue;
    const paramSchema = patternDefinition?.constructor_params_schema?.[paramName];
    if (paramSchema?.type_hint?.toLowerCase().includes('int')) {
        val = newValue === '' ? null : parseInt(newValue, 10);
        if (isNaN(val)) val = null;
    } else if (paramSchema?.type_hint?.toLowerCase().includes('bool')) {
        val = newValue; // Assuming checkbox passes boolean directly
    } else if (paramSchema?.type_hint?.toLowerCase().includes('float')) {
        val = newValue === '' ? null : parseFloat(newValue);
        if (isNaN(val)) val = null;
    }
    updateNodeData(id, { ...data, [paramName]: val });
  }, [id, updateNodeData, patternDefinition, data]);

  const handleListItemChange = useCallback((paramName, index, newAgentId) => {
    const currentList = Array.isArray(data[paramName]) ? [...data[paramName]] : [];
    currentList[index] = newAgentId;
    updateNodeData(id, { ...data, [paramName]: currentList });
  }, [id, updateNodeData, data]);

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
    if (oldKey === newKey || newKey.trim() === "" || (newKey in currentRoutes && oldKey !== newKey)) {
        if (newKey in currentRoutes && oldKey !== newKey) {
            alert(`Route key "${newKey}" already exists.`);
        }
        return; 
    }
    const value = currentRoutes[oldKey];
    delete currentRoutes[oldKey];
    currentRoutes[newKey.trim()] = value;
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);

  const handleRouteValueChange = useCallback((key, newValue) => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    currentRoutes[key] = newValue;
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);

  const addRouteItem = useCallback(() => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    let newKeyBase = `new_route`;
    let newKey = newKeyBase;
    let i = 1;
    while(currentRoutes.hasOwnProperty(newKey)) {
        newKey = `${newKeyBase}_${i}`;
        i++;
    }
    updateNodeData(id, { ...data, routes: { ...currentRoutes, [newKey]: "" } });
  }, [id, updateNodeData, data]);

  const removeRouteItem = useCallback((keyToRemove) => {
    const currentRoutes = typeof data.routes === 'object' && data.routes !== null ? { ...data.routes } : {};
    delete currentRoutes[keyToRemove];
    updateNodeData(id, { ...data, routes: currentRoutes });
  }, [id, updateNodeData, data]);


  if (!patternDefinition) {
    return <Card className="w-80 p-2 border-destructive"><CardHeader><CardTitle>Error: Pattern Unknown</CardTitle></CardHeader><CardContent>Definition for '{tframexPatternId}' not found.</CardContent></Card>;
  }

  const renderParameterInput = (paramName, paramSchema) => {
    const value = data[paramName];
    const inputId = `${id}-${paramName}`;
    const label = paramName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    const listAgentParams = ['participant_agent_names', 'tasks', 'steps'];
    if (paramSchema.type_hint?.toLowerCase().includes('list') && listAgentParams.includes(paramName)) {
      const currentList = Array.isArray(value) ? value : [];
      return (
        <div className="space-y-2 p-2 border border-border/60 rounded-md bg-background/40">
          {currentList.map((agentIdInSlot, index) => (
            <PatternListItem
                key={`${id}-${paramName}-${index}-${agentIdInSlot || 'empty'}`} // More unique key
                parentNodeId={id}
                paramName={paramName}
                agentIdInSlot={agentIdInSlot}
                index={index}
                totalItems={currentList.length}
                onRemove={removeListItem}
                onAgentSelect={(newAgentId) => handleListItemChange(paramName, index, newAgentId)} 
                getAgentNameById={getAgentNameById}
            />
          ))}
          <Button variant="outline" size="sm" onClick={() => addListItem(paramName)} className="text-xs h-7 w-full mt-1.5">
             <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add {(label.singularize && label.singularize()) || label} Slot
          </Button>
        </div>
      );
    }
    
    if (paramName === 'routes' && paramSchema.type_hint?.toLowerCase().includes('dict')) {
        return ( 
            <div className="space-y-1.5 p-1 border border-border/50 rounded-md bg-background/30">
                {Object.entries(value || {}).map(([routeKey, targetName], index) => (
                     <div key={index} className="grid grid-cols-[auto_1fr_auto] gap-1.5 items-center">
                        <Input 
                            value={routeKey} 
                            onChange={(e) => handleRouteKeyChange(routeKey, e.target.value)}
                            placeholder="Route Key"
                            className="text-xs h-8"
                        />
                        <Select value={targetName || ""} onValueChange={(val) => handleRouteValueChange(routeKey, val)}>
                            <SelectTrigger className="h-8 text-xs">
                                <SelectValue placeholder="-- Select Target Agent/Pattern --" />
                            </SelectTrigger>
                            <SelectContent>
                                <optgroup label="Agents">
                                {allAgents.map(agent => <SelectItem key={`agent-${agent.id}`} value={agent.id} className="text-xs">{agent.name} (Agent)</SelectItem>)}
                                </optgroup>
                                 <optgroup label="Patterns (Advanced)">
                                {allPatterns.map(patt => <SelectItem key={`patt-${patt.id}`} value={patt.id} className="text-xs">{patt.name} (Pattern)</SelectItem>)}
                                </optgroup>
                            </SelectContent>
                        </Select>
                        <Button variant="ghost" size="icon" onClick={() => removeRouteItem(routeKey)} className="h-7 w-7 p-1">
                            <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                        </Button>
                    </div>
                ))}
                <Button variant="outline" size="sm" onClick={addRouteItem} className="text-xs h-7 w-full mt-1">
                    <PlusCircle className="h-3.5 w-3.5 mr-1"/> Add Route
                </Button>
            </div>
        );
    }

    const singleAgentParams = ['router_agent_name', 'moderator_agent_name', 'default_route'];
    if (singleAgentParams.includes(paramName) && 
        (paramSchema.type_hint?.toLowerCase().includes('str') || paramSchema.type_hint?.toLowerCase().includes('agent'))) {
        const connectedAgentId = data[paramName];
        const placeholder = paramName === 'default_route' ? "-- Select or Connect Target --" : "-- Select or Connect Agent --";
        const options = paramName === 'default_route' ? [...allAgents, ...allPatterns] : allAgents;
        return (
            <div className="relative p-1.5 border border-dashed border-amber-500/70 rounded-md bg-background/30 hover:border-amber-500 transition-colors">
                <Handle
                    type="target"
                    position={Position.Left}
                    id={`pattern_agent_input_${paramName}`}
                    style={{ background: '#F59E0B', top: '50%', left: -12, width:10, height:10, transform: 'translateY(-50%)' }}
                    title={`Connect Agent for ${label}`}
                    isConnectable={true}
                />
                <Settings2 className="h-4 w-4 text-amber-600 absolute top-1/2 -translate-y-1/2 left-2.5" />
                <div className="pl-8">
                    {connectedAgentId ? (
                         <div className="flex items-center justify-between text-xs">
                            <span className="font-medium text-amber-700">{getAgentNameById(connectedAgentId)}</span>
                            <Button variant="ghost" size="icon" onClick={() => handleSimpleChange(paramName, null)} className="h-6 w-6 p-0.5">
                                <Trash2 className="h-3.5 w-3.5 text-destructive"/>
                            </Button>
                        </div>
                    ) : (
                        <Select value={value || ""} onValueChange={(val) => handleSimpleChange(paramName, val)}>
                            <SelectTrigger className="w-full h-8 text-xs"> <SelectValue placeholder={placeholder} /> </SelectTrigger>
                            <SelectContent>
                                {options.map(opt => (
                                    <SelectItem key={opt.id} value={opt.id} className="text-xs">
                                        {opt.name} {opt.component_category === 'pattern' ? '(Pattern)' : '(Agent)'}
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
        <div className="flex items-center">
            <input type="checkbox" id={inputId} checked={!!value} onChange={(e) => handleSimpleChange(paramName, e.target.checked)} className="form-checkbox h-4 w-4 text-primary border-border rounded mr-2"/>
            <Label htmlFor={inputId} className="text-xs font-normal cursor-pointer">{label}</Label>
        </div>
      );
    }
    if (paramSchema.type_hint?.toLowerCase().includes('int') || paramSchema.type_hint?.toLowerCase().includes('float')) {
      return (
        <Input id={inputId} type="number" value={value === null || value === undefined ? '' : String(value)} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={paramSchema.default !== "REQUIRED" ? String(paramSchema.default) : "Number"} className="text-xs h-8"/>
      );
    }
    const isTextarea = paramSchema.description?.toLowerCase().includes("long text") || 
                       paramSchema.description?.toLowerCase().includes("multiline") ||
                       paramSchema.type_hint?.toLowerCase().includes("textarea");
    if (isTextarea) {
        return <Textarea id={inputId} value={value || ''} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={paramSchema.default !== "REQUIRED" ? paramSchema.default : ""} className="text-xs min-h-[60px]" rows={3}/>;
    }
    return <Input id={inputId} type="text" value={value || ''} onChange={(e) => handleSimpleChange(paramName, e.target.value)} placeholder={paramSchema.default !== "REQUIRED" ? paramSchema.default : ""} className="text-xs h-8"/>;
  };
  
  const hasDynamicRouteOutputs = tframexPatternId === 'RouterPattern' && data.routes && Object.keys(data.routes).length > 0;

  return (
    <Card className="w-[26rem] shadow-lg border-border bg-card text-card-foreground">
      <CardHeader className="p-3 border-b border-border">
         <div className="flex items-center space-x-2">
            <Puzzle className="h-5 w-5 text-primary" />
            <CardTitle className="text-base font-semibold">{data.label || tframexPatternId}</CardTitle>
        </div>
        {patternDefinition.description && <CardDescription className="text-xs mt-1 line-clamp-3">{patternDefinition.description}</CardDescription>}
      </CardHeader>
      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-[24rem] overflow-y-auto pattern-params-content">
        <div>
          <Label htmlFor={`${id}-label`} className="text-xs">Display Label:</Label>
          <Input id={`${id}-label`} value={data.label || tframexPatternId} onChange={(e) => updateNodeData(id, { label: e.target.value })} className="text-xs h-8"/>
        </div>
        {patternDefinition.constructor_params_schema && Object.entries(patternDefinition.constructor_params_schema).map(([paramName, paramSchema]) => (
          <div key={paramName}>
            <Label htmlFor={`${id}-${paramName}`} className="text-xs font-medium block mb-1.5">
              {paramName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} 
              <span className="text-muted-foreground/80 text-xs"> ({paramSchema.type_hint || 'any'})
                {paramSchema.default === "REQUIRED" && <span className="text-destructive"> *</span>}
              </span>:
            </Label>
            {renderParameterInput(paramName, paramSchema)}
            {paramSchema.description && <p className="text-xs text-muted-foreground/70 mt-1 leading-tight">{paramSchema.description}</p>}
          </div>
        ))}
      </CardContent>

      <Handle type="target" position={Position.Left} id="input_flow_in" style={{ background: '#555', top: '50px', transform:'translateY(-50%)' }} title="Flow Input" />
      
      {hasDynamicRouteOutputs &&
        Object.keys(data.routes).map((routeKey, index, arr) => {
            const baseTop = 50; // Match input_flow_in for alignment
            // Spread dynamic handles between roughly 10px and 90px vertically
            // (baseTop - 40px) to (baseTop + 40px)
            const totalSpread = 80; // px
            const itemOffset = arr.length > 1 ? (index / (arr.length -1 )) * totalSpread : totalSpread / 2;
            const dynamicTop = baseTop - (totalSpread / 2) + itemOffset;
            
            return (
                <Handle
                    key={`route-out-${id}-${routeKey}`}
                    type="source"
                    position={Position.Right}
                    id={`output_route_${routeKey.replace(/\s+/g, '_')}`}
                    style={{ 
                        top: `${arr.length === 1 ? baseTop : dynamicTop}px`, // Center if only one, else spread
                        background: '#5DADE2', width: 10, height: 10 
                    }}
                    title={`Output for route: ${routeKey}`}
                />
            );
      })}
      
      {!hasDynamicRouteOutputs && (
        <Handle type="source" position={Position.Right} id="output_flow_out" style={{ background: '#555', top: '50px', transform:'translateY(-50%)' }} title="Flow Output" />
      )}
    </Card>
  );
};

String.prototype.singularize = function() {
    const str = this.toString().toLowerCase(); // Ensure 'this' is stringified
    if (str.endsWith('ies')) return this.slice(0, -3) + 'y';
    // Ensure 's' is not preceded by another 's' (e.g. address -> addres) and string is long enough
    if (str.endsWith('s') && !str.endsWith('ss') && str.length > 1) return this.slice(0, -1); 
    return this.toString();
};

export default TFrameXPatternNode;