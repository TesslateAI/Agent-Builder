// frontend/src/nodes/tframex/MCPServerNode.jsx
import React, { useCallback, useState, useEffect, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Server, Link, AlertCircle, CheckCircle, X, Settings } from 'lucide-react';
import { useStore } from '../../store';

const MCPServerNode = memo(({ id, data }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const deleteNode = useStore((state) => state.deleteNode);
  const setSelectedNodeId = useStore((state) => state.setSelectedNodeId);

  // Local state for configuration
  const [localConfig, setLocalConfig] = useState({
    server_alias: data.server_alias || '',
    command: data.command || '',
    args: data.args || [],
    env: data.env || {},
    status: data.status || 'disconnected'
  });

  // Sync with node data changes
  useEffect(() => {
    setLocalConfig({
      server_alias: data.server_alias || '',
      command: data.command || '',
      args: data.args || [],
      env: data.env || {},
      status: data.status || 'disconnected'
    });
  }, [data]);

  const handleChange = useCallback((field, value) => {
    const newConfig = { ...localConfig, [field]: value };
    setLocalConfig(newConfig);
    updateNodeData(id, newConfig);
  }, [id, updateNodeData, localConfig]);

  const handleArgsChange = useCallback((argsText) => {
    // Parse args as JSON array or fallback to space-separated
    let parsedArgs;
    try {
      if (argsText.trim().startsWith('[')) {
        parsedArgs = JSON.parse(argsText);
      } else {
        parsedArgs = argsText.trim() ? argsText.split(/\s+/) : [];
      }
    } catch (e) {
      parsedArgs = argsText.trim() ? argsText.split(/\s+/) : [];
    }
    handleChange('args', parsedArgs);
  }, [handleChange]);

  const getStatusColor = () => {
    switch (localConfig.status) {
      case 'connected': return 'text-green-500';
      case 'connecting': return 'text-yellow-500';
      case 'error': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = () => {
    switch (localConfig.status) {
      case 'connected': return <CheckCircle className="h-4 w-4" />;
      case 'error': return <AlertCircle className="h-4 w-4" />;
      default: return <Server className="h-4 w-4" />;
    }
  };

  const argsText = Array.isArray(localConfig.args) 
    ? localConfig.args.join(' ')
    : (localConfig.args || '');

  return (
    <Card className="w-80 shadow-lg bg-card text-card-foreground relative border-0">
      {/* Connection handle to agents */}
      <Handle 
        type="source"
        position={Position.Right}
        id="mcp_server_attachment_out" 
        style={{ 
          background: '#10b981', 
          top: '50%', 
          width: 12, 
          height: 12, 
          zIndex: 1 
        }}
        title="Connect to Agent to Enable MCP Tools"
      />

      {/* Delete button */}
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => deleteNode(id)}
        className="absolute top-1 right-1 h-6 w-6 p-0 hover:bg-destructive/10 z-10"
        title="Delete MCP server"
      >
        <X className="h-4 w-4 text-destructive" />
      </Button>

      <CardHeader className="p-3">
        <div className="flex items-center space-x-2">
          <div className={`flex items-center space-x-2 ${getStatusColor()}`}>
            {getStatusIcon()}
            <CardTitle className="text-sm font-semibold">MCP Server</CardTitle>
          </div>
        </div>
        <CardDescription className="text-xs mt-1">
          Model Context Protocol server connection
        </CardDescription>
      </CardHeader>

      <CardContent className="p-3 space-y-3 text-sm nodrag max-h-80 overflow-y-auto">
        {/* Server Alias */}
        <div>
          <Label className="text-xs font-medium block mb-1">Server Alias:</Label>
          <Input
            value={localConfig.server_alias}
            onChange={(e) => handleChange('server_alias', e.target.value)}
            placeholder="e.g., filesystem, github, database"
            className="text-xs h-8"
          />
        </div>

        {/* Command */}
        <div>
          <Label className="text-xs font-medium block mb-1">Command:</Label>
          <Input
            value={localConfig.command}
            onChange={(e) => handleChange('command', e.target.value)}
            placeholder="e.g., npx @modelcontextprotocol/server-filesystem"
            className="text-xs h-8"
          />
        </div>

        {/* Arguments */}
        <div>
          <Label className="text-xs font-medium block mb-1">Arguments:</Label>
          <Textarea
            value={argsText}
            onChange={(e) => handleArgsChange(e.target.value)}
            placeholder='e.g., /path/to/files or ["--option", "value"]'
            className="text-xs min-h-[60px] resize-none"
            rows={2}
          />
          <div className="text-xs text-muted-foreground mt-1">
            Space-separated or JSON array format
          </div>
        </div>

        {/* Connection Status */}
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium">Status:</span>
            <div className={`flex items-center space-x-1 ${getStatusColor()}`}>
              {getStatusIcon()}
              <span className="text-xs capitalize">{localConfig.status}</span>
            </div>
          </div>
          {localConfig.status === 'connected' && (
            <div className="flex items-center space-x-1 text-xs text-green-600">
              <Link className="h-3 w-3" />
              <span>Ready</span>
            </div>
          )}
        </div>

        {/* Available Tools (when connected) */}
        {localConfig.status === 'connected' && data.available_tools && data.available_tools.length > 0 && (
          <div>
            <Label className="text-xs font-medium block mb-1">Available Tools:</Label>
            <div className="max-h-20 overflow-y-auto space-y-1 border border-input p-2 rounded-md bg-background/50">
              {data.available_tools.map(toolName => (
                <div key={toolName} className="flex items-center text-xs">
                  <Settings className="h-3 w-3 mr-1.5 text-green-500 flex-shrink-0" />
                  <span className="truncate" title={toolName}>
                    {toolName}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connection Instructions */}
        <div className="text-xs text-muted-foreground italic pt-1 border-t border-border">
          Connect to agents to enable MCP tools from this server
        </div>
      </CardContent>
    </Card>
  );
});

MCPServerNode.displayName = 'MCPServerNode';

export default MCPServerNode;