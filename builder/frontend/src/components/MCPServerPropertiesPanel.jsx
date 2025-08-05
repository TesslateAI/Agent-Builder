// frontend/src/components/MCPServerPropertiesPanel.jsx  
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
// Badge and Separator components - using inline replacements since they don't exist
const Badge = ({ children, variant = "default", className = "" }) => {
  const variantClasses = {
    default: "bg-primary text-primary-foreground",
    secondary: "bg-secondary text-secondary-foreground", 
    outline: "border border-input bg-background text-foreground"
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
};

const Separator = ({ className = "" }) => (
  <div className={`shrink-0 bg-border h-[1px] w-full ${className}`} />
);
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Server, 
  Play, 
  Square, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  Settings,
  Link,
  Unlink,
  X as XIcon
} from 'lucide-react';
import { useStore } from '../store';
import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/tframex';

const MCPServerPropertiesPanel = ({ nodeId, nodeData }) => {
  const updateNodeData = useStore((state) => state.updateNodeData);
  const setSelectedNodeId = useStore((state) => state.setSelectedNodeId);
  
  // Use ref to track server alias for stable reference in callbacks
  const serverAliasRef = useRef(nodeData?.server_alias || '');
  
  // Local state for form inputs
  const [localData, setLocalData] = useState({
    server_alias: nodeData?.server_alias || '',
    command: nodeData?.command || '',
    args: nodeData?.args || [],
    env: nodeData?.env || {},
    status: nodeData?.status || 'disconnected',
    available_tools: nodeData?.available_tools || [],
    available_resources: nodeData?.available_resources || [],
    available_prompts: nodeData?.available_prompts || []
  });
  
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [connectionError, setConnectionError] = useState('');

  // Sync with node data changes and update ref
  useEffect(() => {
    const newData = {
      server_alias: nodeData?.server_alias || '',
      command: nodeData?.command || '',
      args: nodeData?.args || [],
      env: nodeData?.env || {},
      status: nodeData?.status || 'disconnected',
      available_tools: nodeData?.available_tools || [],
      available_resources: nodeData?.available_resources || [],
      available_prompts: nodeData?.available_prompts || []
    };
    setLocalData(newData);
    serverAliasRef.current = newData.server_alias;
  }, [nodeData]);

  // Auto-refresh status every 30 seconds for connected servers - using stable callback
  useEffect(() => {
    let intervalId;
    if (nodeData?.status === 'connected' && serverAliasRef.current) {
      intervalId = setInterval(async () => {
        if (!serverAliasRef.current) return;

        try {
          const response = await axios.get(`${API_BASE_URL}/mcp/servers/${serverAliasRef.current}/status`);
          
          if (response.data.success) {
            const serverInfo = response.data.server_info;
            updateNodeData(nodeId, {
              ...nodeData,
              status: serverInfo.status,
              available_tools: serverInfo.tools || [],
              available_resources: serverInfo.resources || [],
              available_prompts: serverInfo.prompts || []
            });
          }
        } catch (error) {
          console.error('Failed to refresh server status:', error);
        }
      }, 30000); // 30 seconds
    }
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [nodeData, nodeId, updateNodeData]);

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setLocalData(prev => ({ ...prev, [name]: value }));
    // Update ref when server alias changes  
    if (name === 'server_alias') {
      serverAliasRef.current = value;
    }
  }, []);

  const handleTextareaChange = useCallback((name, value) => {
    if (name === 'args') {
      let parsedArgs;
      try {
        if (value.trim().startsWith('[')) {
          parsedArgs = JSON.parse(value);
        } else {
          parsedArgs = value.trim() ? value.split(/\s+/) : [];
        }
      } catch {
        parsedArgs = value.trim() ? value.split(/\s+/) : [];
      }
      setLocalData(prev => ({ ...prev, args: parsedArgs }));
    } else if (name === 'env') {
      let parsedEnv;
      try {
        parsedEnv = value.trim() ? JSON.parse(value) : {};
      } catch {
        // If JSON parsing fails, treat as key=value pairs
        parsedEnv = {};
        value.split('\n').forEach(line => {
          const [key, ...valueParts] = line.split('=');
          if (key && key.trim()) {
            parsedEnv[key.trim()] = valueParts.join('=').trim();
          }
        });
      }
      setLocalData(prev => ({ ...prev, env: parsedEnv }));
    } else {
      setLocalData(prev => ({ ...prev, [name]: value }));
    }
  }, []);

  const handleApplyChanges = useCallback(() => {
    updateNodeData(nodeId, localData);
  }, [nodeId, updateNodeData, localData]);

  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  const connectServer = async () => {
    if (!localData.server_alias || !localData.command) {
      setConnectionError('Server alias and command are required');
      return;
    }

    setIsConnecting(true);
    setConnectionError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/mcp/servers/connect`, {
        server_alias: localData.server_alias,
        command: localData.command,
        args: localData.args,
        env: localData.env
      });

      if (response.data.success) {
        const serverInfo = response.data.server_info;
        const updatedData = {
          ...localData,
          status: 'connected',
          available_tools: serverInfo.tools || [],
          available_resources: serverInfo.resources || [],
          available_prompts: serverInfo.prompts || []
        };
        setLocalData(updatedData);
        updateNodeData(nodeId, updatedData);
      } else {
        setConnectionError(response.data.message || 'Failed to connect to MCP server');
        const errorData = { ...localData, status: 'error' };
        setLocalData(errorData);
        updateNodeData(nodeId, errorData);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message || 'Network error';
      setConnectionError(errorMessage);
      const errorData = { ...localData, status: 'error' };
      setLocalData(errorData);
      updateNodeData(nodeId, errorData);
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnectServer = async () => {
    if (!localData.server_alias) return;

    setIsDisconnecting(true);
    setConnectionError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/mcp/servers/disconnect`, {
        server_alias: localData.server_alias
      });

      if (response.data.success) {
        const updatedData = {
          ...localData,
          status: 'disconnected',
          available_tools: [],
          available_resources: [],
          available_prompts: []
        };
        setLocalData(updatedData);
        updateNodeData(nodeId, updatedData);
      } else {
        setConnectionError(response.data.message || 'Failed to disconnect from MCP server');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message || 'Network error';
      setConnectionError(errorMessage);
    } finally {
      setIsDisconnecting(false);
    }
  };

  const refreshServerStatus = useCallback(async () => {
    if (!serverAliasRef.current) return;

    try {
      const response = await axios.get(`${API_BASE_URL}/mcp/servers/${serverAliasRef.current}/status`);
      
      if (response.data.success) {
        const serverInfo = response.data.server_info;
        const updatedData = {
          ...localData,
          status: serverInfo.status,
          available_tools: serverInfo.tools || [],
          available_resources: serverInfo.resources || [],
          available_prompts: serverInfo.prompts || []
        };
        setLocalData(updatedData);
        updateNodeData(nodeId, updatedData);
      }
    } catch (error) {
      console.error('Failed to refresh server status:', error);
    }
  }, [localData, nodeId, updateNodeData]);

  const getStatusColor = () => {
    switch (localData.status) {
      case 'connected': return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800';
      case 'connecting': return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800';
      case 'error': return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800';
      default: return 'text-muted-foreground bg-muted/50 border-border';
    }
  };

  const getStatusIcon = () => {
    switch (localData.status) {
      case 'connected': return <CheckCircle className="h-4 w-4" />;
      case 'connecting': return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'error': return <AlertCircle className="h-4 w-4" />;
      default: return <Server className="h-4 w-4" />;
    }
  };

  const argsText = Array.isArray(localData.args) 
    ? localData.args.join(' ')
    : (localData.args || '');

  const envText = typeof localData.env === 'object' 
    ? JSON.stringify(localData.env, null, 2)
    : (localData.env || '');

  try {
    return (
      <div className="flex flex-col h-full bg-sidebar">
        <div className="p-3 border-b border-sidebar-border flex-shrink-0 h-16 flex flex-row justify-between items-center">
          <div className="flex items-center">
            <Server className="h-5 w-5 mr-2 text-green-500" />
            <div>
              <div className="text-base font-semibold text-sidebar-foreground">MCP Server Properties</div>
              <div className="text-xs mt-0.5 truncate max-w-[250px] text-muted-foreground">
                Editing: {localData.server_alias || nodeId}
              </div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={handleClosePanel} className="text-muted-foreground hover:text-foreground">
            <XIcon className="h-5 w-5" />
            <span className="sr-only">Close Properties</span>
          </Button>
        </div>
        <div className="flex-grow p-3 overflow-hidden">
          <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-y-auto p-4 space-y-4">
          {/* Server Alias */}
          <div className="mb-3">
            <Label htmlFor="prop-server_alias" className="text-xs">Server Alias</Label>
            <Input 
              id="prop-server_alias"
              name="server_alias" 
              value={localData.server_alias || ''} 
              onChange={handleInputChange} 
              placeholder="e.g., filesystem, github, database"
              className="text-sm h-8 border-input" 
            />
          </div>

          {/* Command */}
          <div className="mb-3">
            <Label htmlFor="prop-command" className="text-xs">Command</Label>
            <Input
              id="prop-command"
              name="command"
              value={localData.command || ''}
              onChange={handleInputChange}
              placeholder="e.g., npx @modelcontextprotocol/server-filesystem"
              className="text-sm h-8 border-input"
            />
          </div>

          {/* Arguments */}
          <div className="mb-3">
            <Label htmlFor="prop-args" className="text-xs">Arguments</Label>
            <Textarea
              id="prop-args"
              value={argsText}
              onChange={(e) => handleTextareaChange('args', e.target.value)}
              placeholder='e.g., /path/to/files or ["--option", "value"]'
              className="text-sm min-h-[60px] resize-none"
              rows={2}
            />
            <div className="text-xs text-muted-foreground mt-1">
              Space-separated or JSON array format
            </div>
          </div>

          {/* Environment Variables */}
          <div className="mb-3">
            <Label htmlFor="prop-env" className="text-xs">Environment Variables (Optional)</Label>
            <Textarea
              id="prop-env"
              value={envText}
              onChange={(e) => handleTextareaChange('env', e.target.value)}
              placeholder='{"API_KEY": "value"} or KEY=value format'
              className="text-sm min-h-[60px] resize-none"
              rows={2}
            />
            <div className="text-xs text-muted-foreground mt-1">
              JSON object or KEY=value pairs (one per line)
            </div>
          </div>

          {/* Connection Status */}
          <div className="mb-3">
            <Label className="text-xs flex items-center mb-2">
              <Settings className="h-3 w-3 mr-1" />
              Connection Status
            </Label>
            <div className={`flex items-center space-x-2 px-3 py-2 rounded-md border ${getStatusColor()}`}>
              {getStatusIcon()}
              <span className="text-sm font-medium capitalize">{localData.status || 'disconnected'}</span>
            </div>
          </div>

          {/* Connection Controls */}
          <div className="mb-3">
            <div className="flex space-x-2">
              {localData.status !== 'connected' ? (
                <Button 
                  onClick={connectServer} 
                  disabled={isConnecting || !localData.server_alias || !localData.command}
                  className="flex-1"
                  size="sm"
                >
                  {isConnecting ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Link className="h-4 w-4 mr-2" />
                      Connect
                    </>
                  )}
                </Button>
              ) : (
                <Button 
                  onClick={disconnectServer} 
                  disabled={isDisconnecting}
                  variant="destructive"
                  className="flex-1"
                  size="sm"
                >
                  {isDisconnecting ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Disconnecting...
                    </>
                  ) : (
                    <>
                      <Unlink className="h-4 w-4 mr-2" />
                      Disconnect
                    </>
                  )}
                </Button>
              )}
              <Button 
                onClick={refreshServerStatus} 
                variant="outline"
                size="sm"
                disabled={!localData.server_alias}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Connection Error */}
          {connectionError && (
            <Alert variant="destructive" className="mb-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">{connectionError}</AlertDescription>
            </Alert>
          )}

          {/* Available Capabilities */}
          {localData.status === 'connected' && (
            <>
              {/* Tools */}
              <div className="mb-3">
                <Label className="text-xs font-medium mb-2 block">Tools ({localData.available_tools?.length || 0})</Label>
                <div className="flex flex-wrap gap-1">
                  {localData.available_tools && localData.available_tools.length > 0 ? (
                    localData.available_tools.map((tool, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        <Settings className="h-3 w-3 mr-1" />
                        {tool.name || tool}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No tools available</span>
                  )}
                </div>
              </div>

              {/* Resources */}
              <div className="mb-3">
                <Label className="text-xs font-medium mb-2 block">Resources ({localData.available_resources?.length || 0})</Label>
                <div className="flex flex-wrap gap-1">
                  {localData.available_resources && localData.available_resources.length > 0 ? (
                    localData.available_resources.map((resource, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {resource.name || resource}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No resources available</span>
                  )}
                </div>
              </div>

              {/* Prompts */}
              <div className="mb-3">
                <Label className="text-xs font-medium mb-2 block">Prompts ({localData.available_prompts?.length || 0})</Label>
                <div className="flex flex-wrap gap-1">
                  {localData.available_prompts && localData.available_prompts.length > 0 ? (
                    localData.available_prompts.map((prompt, index) => (
                      <Badge key={index} variant="default" className="text-xs">
                        {prompt.name || prompt}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No prompts available</span>
                  )}
                </div>
              </div>
            </>
          )}
          </div>
        </div>
        <div className="p-3 border-t border-sidebar-border flex-shrink-0">
          <Button onClick={handleApplyChanges} className="w-full" size="sm">
            Apply Changes
          </Button>
        </div>
      </div>
    );
  } catch (error) {
    console.error('Error rendering MCPServerPropertiesPanel:', error);
    return (
      <div className="flex flex-col h-full bg-sidebar">
        <div className="p-3 border-b border-sidebar-border flex-shrink-0 h-16 flex flex-row justify-between items-center">
          <div className="flex items-center">
            <Server className="h-5 w-5 mr-2 text-red-500" />
            <div>
              <div className="text-base font-semibold text-sidebar-foreground">MCP Server Properties - Error</div>
              <div className="text-xs mt-0.5 truncate max-w-[250px] text-muted-foreground">
                Error loading panel
              </div>
            </div>
          </div>
        </div>
        <div className="flex-grow p-3 overflow-hidden">
          <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-y-auto p-4 space-y-4">
            <div className="p-4 border border-red-200 rounded-md bg-red-50/30">
              <p className="text-sm font-medium text-red-800">Rendering Error</p>
              <p className="text-xs text-red-600 mt-1">{error.message}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }
};

export default MCPServerPropertiesPanel;