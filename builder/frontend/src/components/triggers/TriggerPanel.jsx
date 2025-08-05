// components/triggers/TriggerPanel.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Play, Pause, Settings, Trash2, Zap, Clock, Webhook, Mail, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { useStore } from '../../store';
import TriggerConfigModal from './TriggerConfigModal';

const TRIGGER_ICONS = {
  webhook: Webhook,
  schedule: Clock,
  email: Mail,
  file: FolderOpen,
  event: Zap
};

const TriggerPanel = () => {
  const [triggers, setTriggers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState(null);
  
  const currentFlowId = useStore((state) => state.currentProjectId); // Using project ID as flow ID for now
  const addNode = useStore((state) => state.addNode);

  // Fetch triggers for current flow
  const fetchTriggers = useCallback(async () => {
    if (!currentFlowId) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/api/triggers?flow_id=${currentFlowId}`);
      const data = await response.json();
      
      if (data.success) {
        setTriggers(data.triggers);
      } else {
        console.error('Failed to fetch triggers:', data.error);
      }
    } catch (error) {
      console.error('Error fetching triggers:', error);
    } finally {
      setIsLoading(false);
    }
  }, [currentFlowId]);

  useEffect(() => {
    fetchTriggers();
  }, [fetchTriggers]);

  const handleCreateTrigger = () => {
    setEditingTrigger(null);
    setShowConfigModal(true);
  };

  const handleEditTrigger = (trigger) => {
    setEditingTrigger(trigger);
    setShowConfigModal(true);
  };

  const handleSaveTrigger = async (triggerData) => {
    try {
      const url = editingTrigger 
        ? `/api/triggers/${editingTrigger.id}`
        : '/api/triggers';
      
      const method = editingTrigger ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(triggerData)
      });

      const result = await response.json();
      
      if (result.success) {
        // Refresh triggers list
        await fetchTriggers();
        
        // If creating a new trigger, add it to the canvas
        if (!editingTrigger) {
          const triggerNode = {
            id: 'trigger',
            type: 'trigger',
            component_category: 'trigger',
            data: {
              type: triggerData.type,
              name: triggerData.name,
              description: triggerData.description,
              enabled: triggerData.enabled,
              triggerId: result.trigger.id,
              status: 'armed',
              label: triggerData.name,
              component_category: 'trigger'
            }
          };
          
          // Add to canvas at a default position
          addNode(triggerNode, { x: 100, y: 100 });
        }
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Failed to save trigger:', error);
      throw error;
    }
  };

  const handleToggleTrigger = async (triggerId, enabled) => {
    try {
      const url = enabled 
        ? `/api/triggers/${triggerId}/enable`
        : `/api/triggers/${triggerId}/disable`;
      
      const response = await fetch(url, { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        await fetchTriggers();
      } else {
        console.error('Failed to toggle trigger:', result.error);
      }
    } catch (error) {
      console.error('Error toggling trigger:', error);
    }
  };

  const handleDeleteTrigger = async (triggerId) => {
    if (!confirm('Are you sure you want to delete this trigger?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/triggers/${triggerId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        await fetchTriggers();
      } else {
        console.error('Failed to delete trigger:', result.error);
      }
    } catch (error) {
      console.error('Error deleting trigger:', error);
    }
  };

  const formatRelativeTime = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  if (!currentFlowId) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p className="text-sm">No flow selected</p>
        <p className="text-xs mt-1">Select a flow to manage triggers</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-sm">Triggers</h3>
          <Button size="sm" onClick={handleCreateTrigger}>
            <Plus className="h-4 w-4 mr-1" />
            Add
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground">Loading triggers...</p>
          </div>
        ) : triggers.length === 0 ? (
          <div className="text-center py-8">
            <Zap className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No triggers configured</p>
            <p className="text-xs text-muted-foreground mt-1">
              Add triggers to automate flow execution
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleCreateTrigger}
              className="mt-3"
            >
              <Plus className="h-4 w-4 mr-1" />
              Create First Trigger
            </Button>
          </div>
        ) : (
          triggers.map(trigger => {
            const TriggerIcon = TRIGGER_ICONS[trigger.type] || Zap;
            return (
              <Card key={trigger.id} className="hover:shadow-sm transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 min-w-0 flex-1">
                      <TriggerIcon className="h-4 w-4 text-orange-600 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <CardTitle className="text-sm truncate">{trigger.name}</CardTitle>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge variant="outline" className="text-xs capitalize">
                            {trigger.type}
                          </Badge>
                          <Badge 
                            variant={trigger.enabled ? 'default' : 'secondary'} 
                            className="text-xs"
                          >
                            {trigger.enabled ? 'Active' : 'Disabled'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Switch
                        checked={trigger.enabled}
                        onCheckedChange={(checked) => handleToggleTrigger(trigger.id, checked)}
                        size="sm"
                      />
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {trigger.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {trigger.description}
                      </p>
                    )}
                    
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        {trigger.trigger_count || 0} executions
                      </span>
                      <span>
                        {formatRelativeTime(trigger.last_triggered_at)}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-end space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditTrigger(trigger)}
                      >
                        <Settings className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteTrigger(trigger.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Configuration Modal */}
      <TriggerConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onSave={handleSaveTrigger}
        trigger={editingTrigger}
        flowId={currentFlowId}
      />
    </div>
  );
};

export default TriggerPanel;