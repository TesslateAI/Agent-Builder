// components/triggers/TriggerConfigModal.jsx
import React, { useState, useCallback } from 'react';
import { X, Clock, Webhook, Mail, FolderOpen, Zap, Save, TestTube } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import WebhookConfig from './WebhookConfig';
import ScheduleConfig from './ScheduleConfig';
import EmailConfig from './EmailConfig';
import FileConfig from './FileConfig';
import AuthConfig from './AuthConfig';

const TRIGGER_TYPES = [
  { id: 'webhook', name: 'Webhook', icon: Webhook, description: 'HTTP endpoint that triggers on incoming requests' },
  { id: 'schedule', name: 'Schedule', icon: Clock, description: 'Time-based triggers using cron or intervals' },
  { id: 'email', name: 'Email', icon: Mail, description: 'Monitor email accounts for new messages' },
  { id: 'file', name: 'File Watch', icon: FolderOpen, description: 'Watch file systems for changes' },
  { id: 'event', name: 'Event', icon: Zap, description: 'Listen to external event sources' }
];

const TriggerConfigModal = ({ 
  isOpen, 
  onClose, 
  onSave, 
  trigger = null, // null for new trigger, object for editing
  flowId 
}) => {
  const [formData, setFormData] = useState(() => ({
    type: trigger?.type || 'webhook',
    name: trigger?.name || '',
    description: trigger?.description || '',
    enabled: trigger?.enabled !== undefined ? trigger.enabled : true,
    config: trigger?.config || {}
  }));

  const [activeTab, setActiveTab] = useState('basic');
  const [isLoading, setIsLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const handleInputChange = useCallback((field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  }, []);

  const handleConfigChange = useCallback((configData) => {
    setFormData(prev => ({
      ...prev,
      config: configData
    }));
  }, []);

  const handleSave = async () => {
    if (!formData.name.trim()) {
      alert('Please enter a trigger name');
      return;
    }

    setIsLoading(true);
    try {
      const triggerData = {
        ...formData,
        flow_id: flowId
      };

      await onSave(triggerData);
      onClose();
    } catch (error) {
      console.error('Failed to save trigger:', error);
      alert('Failed to save trigger: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTest = async () => {
    if (!trigger?.id) {
      alert('Please save the trigger first before testing');
      return;
    }

    setIsLoading(true);
    setTestResult(null);

    try {
      const response = await fetch(`/api/triggers/${trigger.id}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          payload: { test: true, timestamp: new Date().toISOString() }
        })
      });

      const result = await response.json();
      setTestResult(result);
      
      if (result.success) {
        alert('Test trigger fired successfully!');
      } else {
        alert('Test failed: ' + result.error);
      }
    } catch (error) {
      console.error('Test failed:', error);
      setTestResult({ success: false, error: error.message });
      alert('Test failed: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedTriggerType = TRIGGER_TYPES.find(t => t.id === formData.type);
  const Icon = selectedTriggerType?.icon || Zap;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
        <DialogHeader className="pb-4">
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Icon className="h-4 w-4" />
            <span>{trigger ? 'Edit Trigger' : 'Create New Trigger'}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto max-h-[calc(80vh-120px)]">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="basic">Basic Settings</TabsTrigger>
              <TabsTrigger value="config">Configuration</TabsTrigger>
              <TabsTrigger value="auth">Authentication</TabsTrigger>
              <TabsTrigger value="advanced">Advanced</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4">
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="space-y-3">
                  <label className="text-sm font-medium">Basic Information</label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="trigger-name">Trigger Name *</Label>
                    <Input
                      id="trigger-name"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      placeholder="Enter trigger name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="trigger-type">Trigger Type *</Label>
                    <Select
                      value={formData.type}
                      onValueChange={(value) => handleInputChange('type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TRIGGER_TYPES.map(type => {
                          const TypeIcon = type.icon;
                          return (
                            <SelectItem key={type.id} value={type.id}>
                              <div className="flex items-center space-x-2">
                                <TypeIcon className="h-4 w-4" />
                                <span>{type.name}</span>
                              </div>
                            </SelectItem>
                          );
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="trigger-description">Description</Label>
                  <Textarea
                    id="trigger-description"
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    placeholder="Describe what this trigger does"
                    rows={3}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="trigger-enabled"
                    checked={formData.enabled}
                    onCheckedChange={(checked) => handleInputChange('enabled', checked)}
                  />
                  <Label htmlFor="trigger-enabled">Enable trigger immediately</Label>
                </div>

                  {selectedTriggerType && (
                    <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20 text-blue-400">
                      <p className="text-sm">{selectedTriggerType.description}</p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="config" className="space-y-4">
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="space-y-3">
                  <label className="text-sm font-medium">Trigger Configuration</label>
                {formData.type === 'webhook' && (
                  <WebhookConfig
                    config={formData.config}
                    onChange={handleConfigChange}
                  />
                )}
                {formData.type === 'schedule' && (
                  <ScheduleConfig
                    config={formData.config}
                    onChange={handleConfigChange}
                  />
                )}
                {formData.type === 'email' && (
                  <EmailConfig
                    config={formData.config}
                    onChange={handleConfigChange}
                  />
                )}
                {formData.type === 'file' && (
                  <FileConfig
                    config={formData.config}
                    onChange={handleConfigChange}
                  />
                )}
                  {!['webhook', 'schedule', 'email', 'file'].includes(formData.type) && (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>Configuration for {formData.type} triggers is not yet implemented.</p>
                      <p className="text-sm mt-2">Coming soon!</p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="auth" className="space-y-4">
              <AuthConfig
                config={formData.config.auth || {}}
                onChange={(authConfig) => handleConfigChange({ ...formData.config, auth: authConfig })}
                triggerType={formData.type}
              />
            </TabsContent>

            <TabsContent value="advanced" className="space-y-4">
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="space-y-3">
                  <label className="text-sm font-medium">Advanced Settings</label>
                  <div className="text-sm text-muted-foreground">
                  <p>Advanced configuration options will be available in future versions:</p>
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    <li>Rate limiting and throttling</li>
                    <li>Retry policies</li>
                    <li>Error handling strategies</li>
                    <li>Conditional execution rules</li>
                    <li>Custom payload transformations</li>
                  </ul>
                </div>

                {trigger?.id && (
                  <div className="border-t pt-4">
                    <h4 className="font-medium mb-2">Testing</h4>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleTest}
                        disabled={isLoading}
                      >
                        <TestTube className="h-4 w-4 mr-2" />
                        Test Trigger
                      </Button>
                      {testResult && (
                        <Badge variant={testResult.success ? 'default' : 'destructive'}>
                          {testResult.success ? 'Success' : 'Failed'}
                        </Badge>
                      )}
                    </div>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex justify-end space-x-2 pt-4">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
            <Button onClick={handleSave} disabled={isLoading}>
              <Save className="h-4 w-4 mr-2" />
              {isLoading ? 'Saving...' : (trigger ? 'Update Trigger' : 'Create Trigger')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TriggerConfigModal;