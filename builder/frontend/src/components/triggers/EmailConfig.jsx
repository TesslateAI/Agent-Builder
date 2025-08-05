// components/triggers/EmailConfig.jsx
import React, { useCallback, useState } from 'react';
import { Mail, Eye, EyeOff, TestTube, CheckCircle, XCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

const COMMON_PROVIDERS = [
  { name: 'Gmail', imap: 'imap.gmail.com', imapPort: 993, pop3: 'pop.gmail.com', pop3Port: 995 },
  { name: 'Outlook/Hotmail', imap: 'outlook.office365.com', imapPort: 993, pop3: 'outlook.office365.com', pop3Port: 995 },
  { name: 'Yahoo', imap: 'imap.mail.yahoo.com', imapPort: 993, pop3: 'pop.mail.yahoo.com', pop3Port: 995 },
  { name: 'Custom', imap: '', imapPort: 993, pop3: '', pop3Port: 995 }
];

const EmailConfig = ({ config, onChange }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);

  const handleConfigChange = useCallback((field, value) => {
    const newConfig = {
      ...config,
      [field]: value
    };
    onChange(newConfig);
  }, [config, onChange]);

  const handleProviderChange = useCallback((providerName) => {
    const provider = COMMON_PROVIDERS.find(p => p.name === providerName);
    if (provider && provider.name !== 'Custom') {
      const monitorType = config.monitorType || 'imap';
      const newConfig = {
        ...config,
        provider: providerName,
        host: monitorType === 'imap' ? provider.imap : provider.pop3,
        port: monitorType === 'imap' ? provider.imapPort : provider.pop3Port
      };
      onChange(newConfig);
    } else {
      handleConfigChange('provider', providerName);
    }
  }, [config, onChange]);

  const handleMonitorTypeChange = useCallback((type) => {
    const provider = COMMON_PROVIDERS.find(p => p.name === config.provider);
    let newConfig = {
      ...config,
      monitorType: type
    };

    // Update port if using a known provider
    if (provider && provider.name !== 'Custom') {
      newConfig.host = type === 'imap' ? provider.imap : provider.pop3;
      newConfig.port = type === 'imap' ? provider.imapPort : provider.pop3Port;
    }

    onChange(newConfig);
  }, [config, onChange]);

  const testConnection = useCallback(async () => {
    setIsTestingConnection(true);
    setTestStatus(null);

    try {
      // This would normally call the backend API to test the connection
      // For now, just simulate a test
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Simulate success/failure based on whether credentials are provided
      if (config.host && config.username && config.password) {
        setTestStatus({ success: true, message: 'Connection successful!' });
      } else {
        setTestStatus({ success: false, message: 'Missing required fields' });
      }
    } catch (error) {
      setTestStatus({ success: false, message: error.message });
    } finally {
      setIsTestingConnection(false);
    }
  }, [config]);

  return (
    <div className="space-y-6">
      {/* Email Provider Selection */}
      <div className="space-y-2">
        <Label>Email Provider</Label>
        <Select
          value={config.provider || 'Gmail'}
          onValueChange={handleProviderChange}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {COMMON_PROVIDERS.map(provider => (
              <SelectItem key={provider.name} value={provider.name}>
                {provider.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Monitor Type */}
      <div className="space-y-2">
        <Label>Protocol</Label>
        <Select
          value={config.monitorType || 'imap'}
          onValueChange={handleMonitorTypeChange}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="imap">IMAP (Recommended)</SelectItem>
            <SelectItem value="pop3">POP3</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500">
          IMAP allows checking without downloading. POP3 downloads and optionally deletes messages.
        </p>
      </div>

      <Separator />

      {/* Server Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Mail className="h-4 w-4" />
            <span>Server Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2 space-y-2">
              <Label>Server Host</Label>
              <Input
                value={config.host || ''}
                onChange={(e) => handleConfigChange('host', e.target.value)}
                placeholder="imap.gmail.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Port</Label>
              <Input
                type="number"
                value={config.port || ''}
                onChange={(e) => handleConfigChange('port', parseInt(e.target.value) || '')}
                placeholder="993"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="use_ssl"
              checked={config.use_ssl !== false}
              onCheckedChange={(checked) => handleConfigChange('use_ssl', checked)}
            />
            <Label htmlFor="use_ssl">Use SSL/TLS (Recommended)</Label>
          </div>
        </CardContent>
      </Card>

      {/* Authentication */}
      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Email Address</Label>
            <Input
              type="email"
              value={config.username || ''}
              onChange={(e) => handleConfigChange('username', e.target.value)}
              placeholder="your.email@gmail.com"
            />
          </div>

          <div className="space-y-2">
            <Label>Password / App Password</Label>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={config.password || ''}
                onChange={(e) => handleConfigChange('password', e.target.value)}
                placeholder="Your password or app-specific password"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-amber-600">
              For Gmail, use an App Password. For other providers, check if 2FA requires app passwords.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={testConnection}
              disabled={isTestingConnection || !config.host || !config.username || !config.password}
            >
              <TestTube className="h-4 w-4 mr-2" />
              {isTestingConnection ? 'Testing...' : 'Test Connection'}
            </Button>
            {testStatus && (
              <Badge variant={testStatus.success ? 'default' : 'destructive'}>
                {testStatus.success ? (
                  <CheckCircle className="h-3 w-3 mr-1" />
                ) : (
                  <XCircle className="h-3 w-3 mr-1" />
                )}
                {testStatus.message}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Email Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Message Filters (Optional)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {config.monitorType === 'imap' && (
            <div className="space-y-2">
              <Label>Folder</Label>
              <Input
                value={config.folder || 'INBOX'}
                onChange={(e) => handleConfigChange('folder', e.target.value)}
                placeholder="INBOX"
              />
              <p className="text-xs text-gray-500">
                IMAP folder to monitor (e.g., INBOX, Sent, Custom Folder)
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label>From Address Filter</Label>
            <Input
              value={config.fromFilter || ''}
              onChange={(e) => handleConfigChange('fromFilter', e.target.value)}
              placeholder="sender@example.com"
            />
            <p className="text-xs text-gray-500">
              Only trigger for emails from this address (leave empty for all)
            </p>
          </div>

          <div className="space-y-2">
            <Label>Subject Filter</Label>
            <Input
              value={config.subjectFilter || ''}
              onChange={(e) => handleConfigChange('subjectFilter', e.target.value)}
              placeholder="Important"
            />
            <p className="text-xs text-gray-500">
              Only trigger for emails containing this text in subject
            </p>
          </div>

          <div className="space-y-2">
            <Label>Body Filter</Label>
            <Textarea
              value={config.bodyFilter || ''}
              onChange={(e) => handleConfigChange('bodyFilter', e.target.value)}
              placeholder="urgent"
              rows={2}
            />
            <p className="text-xs text-gray-500">
              Only trigger for emails containing this text in body
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="only_new"
              checked={config.onlyNew !== false}
              onCheckedChange={(checked) => handleConfigChange('onlyNew', checked)}
            />
            <Label htmlFor="only_new">Only process new/unread messages</Label>
          </div>
        </CardContent>
      </Card>

      {/* Monitoring Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Monitoring Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Check Interval (seconds)</Label>
            <Input
              type="number"
              min="30"
              max="3600"
              value={config.checkInterval || 60}
              onChange={(e) => handleConfigChange('checkInterval', parseInt(e.target.value) || 60)}
            />
            <p className="text-xs text-gray-500">
              How often to check for new emails (30-3600 seconds)
            </p>
          </div>

          {config.monitorType === 'pop3' && (
            <div className="flex items-center space-x-2">
              <Switch
                id="delete_after_read"
                checked={config.deleteAfterRead === true}
                onCheckedChange={(checked) => handleConfigChange('deleteAfterRead', checked)}
              />
              <Label htmlFor="delete_after_read">Delete messages after processing</Label>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default EmailConfig;