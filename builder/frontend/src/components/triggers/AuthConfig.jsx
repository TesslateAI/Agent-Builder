// components/triggers/AuthConfig.jsx
import React, { useState, useCallback } from 'react';
import { Shield, Key, Eye, EyeOff, Plus, Trash2, CheckCircle, XCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

const AUTH_TYPES = [
  { id: 'none', name: 'None', description: 'No authentication required' },
  { id: 'bearer', name: 'Bearer Token', description: 'Authorization: Bearer <token>' },
  { id: 'basic', name: 'Basic Auth', description: 'Username and password authentication' },
  { id: 'api_key', name: 'API Key', description: 'Custom API key header or query parameter' },
  { id: 'oauth2', name: 'OAuth 2.0', description: 'OAuth 2.0 client credentials flow' },
  { id: 'custom', name: 'Custom Headers', description: 'Custom authentication headers' }
];

const AUTH_LOCATIONS = [
  { id: 'header', name: 'Header' },
  { id: 'query', name: 'Query Parameter' },
  { id: 'body', name: 'Request Body' }
];

const AuthConfig = ({ config, onChange, triggerType }) => {
  const [showSecrets, setShowSecrets] = useState({});

  const handleConfigChange = useCallback((field, value) => {
    const newConfig = {
      ...config,
      [field]: value
    };
    onChange(newConfig);
  }, [config, onChange]);

  const handleCustomHeaderAdd = useCallback(() => {
    const headers = config.customHeaders || [];
    const newHeaders = [...headers, { name: '', value: '', secret: false }];
    handleConfigChange('customHeaders', newHeaders);
  }, [config.customHeaders, handleConfigChange]);

  const handleCustomHeaderRemove = useCallback((index) => {
    const headers = config.customHeaders || [];
    const newHeaders = headers.filter((_, i) => i !== index);
    handleConfigChange('customHeaders', newHeaders);
  }, [config.customHeaders, handleConfigChange]);

  const handleCustomHeaderChange = useCallback((index, field, value) => {
    const headers = [...(config.customHeaders || [])];
    headers[index] = { ...headers[index], [field]: value };
    handleConfigChange('customHeaders', headers);
  }, [config.customHeaders, handleConfigChange]);

  const toggleSecretVisibility = useCallback((key) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const renderSecretField = useCallback((value, onChange, placeholder, fieldKey) => (
    <div className="relative">
      <Input
        type={showSecrets[fieldKey] ? 'text' : 'password'}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="absolute right-0 top-0 h-full px-3"
        onClick={() => toggleSecretVisibility(fieldKey)}
      >
        {showSecrets[fieldKey] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </Button>
    </div>
  ), [showSecrets, toggleSecretVisibility]);

  const authType = config.authType || 'none';

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-4 w-4" />
            <span>Authentication Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Authentication Type</Label>
            <Select
              value={authType}
              onValueChange={(value) => handleConfigChange('authType', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AUTH_TYPES.map(type => (
                  <SelectItem key={type.id} value={type.id}>
                    <div>
                      <div className="font-medium">{type.name}</div>
                      <div className="text-xs text-gray-500">{type.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {authType !== 'none' && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                <strong>Security Note:</strong> Authentication credentials are encrypted and stored securely.
                They are only used for trigger execution and are not accessible in logs or API responses.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bearer Token Configuration */}
      {authType === 'bearer' && (
        <Card>
          <CardHeader>
            <CardTitle>Bearer Token</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Token</Label>
              {renderSecretField(
                config.bearerToken,
                (value) => handleConfigChange('bearerToken', value),
                'Enter bearer token',
                'bearerToken'
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Basic Auth Configuration */}
      {authType === 'basic' && (
        <Card>
          <CardHeader>
            <CardTitle>Basic Authentication</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Username</Label>
                <Input
                  value={config.basicUsername || ''}
                  onChange={(e) => handleConfigChange('basicUsername', e.target.value)}
                  placeholder="Username"
                />
              </div>
              <div className="space-y-2">
                <Label>Password</Label>
                {renderSecretField(
                  config.basicPassword,
                  (value) => handleConfigChange('basicPassword', value),
                  'Password',
                  'basicPassword'
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Key Configuration */}
      {authType === 'api_key' && (
        <Card>
          <CardHeader>
            <CardTitle>API Key</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Key Name</Label>
                <Input
                  value={config.apiKeyName || ''}
                  onChange={(e) => handleConfigChange('apiKeyName', e.target.value)}
                  placeholder="X-API-Key"
                />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Select
                  value={config.apiKeyLocation || 'header'}
                  onValueChange={(value) => handleConfigChange('apiKeyLocation', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AUTH_LOCATIONS.map(loc => (
                      <SelectItem key={loc.id} value={loc.id}>
                        {loc.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>API Key Value</Label>
              {renderSecretField(
                config.apiKeyValue,
                (value) => handleConfigChange('apiKeyValue', value),
                'Enter API key',
                'apiKeyValue'
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* OAuth 2.0 Configuration */}
      {authType === 'oauth2' && (
        <Card>
          <CardHeader>
            <CardTitle>OAuth 2.0 Client Credentials</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Token URL</Label>
              <Input
                value={config.oauth2TokenUrl || ''}
                onChange={(e) => handleConfigChange('oauth2TokenUrl', e.target.value)}
                placeholder="https://auth.example.com/oauth/token"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Client ID</Label>
                <Input
                  value={config.oauth2ClientId || ''}
                  onChange={(e) => handleConfigChange('oauth2ClientId', e.target.value)}
                  placeholder="Client ID"
                />
              </div>
              <div className="space-y-2">
                <Label>Client Secret</Label>
                {renderSecretField(
                  config.oauth2ClientSecret,
                  (value) => handleConfigChange('oauth2ClientSecret', value),
                  'Client Secret',
                  'oauth2ClientSecret'
                )}
              </div>
            </div>
            <div className="space-y-2">
              <Label>Scope (Optional)</Label>
              <Input
                value={config.oauth2Scope || ''}
                onChange={(e) => handleConfigChange('oauth2Scope', e.target.value)}
                placeholder="read write"
              />
            </div>
            <div className="space-y-2">
              <Label>Token Cache Duration (minutes)</Label>
              <Input
                type="number"
                min="1"
                max="1440"
                value={config.oauth2CacheDuration || 60}
                onChange={(e) => handleConfigChange('oauth2CacheDuration', parseInt(e.target.value) || 60)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Custom Headers Configuration */}
      {authType === 'custom' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Custom Headers</span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCustomHeaderAdd}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Header
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(!config.customHeaders || config.customHeaders.length === 0) && (
              <div className="text-center py-4 text-gray-500">
                <p>No custom headers configured</p>
                <p className="text-sm">Click "Add Header" to configure authentication headers</p>
              </div>
            )}
            {(config.customHeaders || []).map((header, index) => (
              <div key={index} className="p-3 border rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Header {index + 1}</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCustomHeaderRemove(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Header Name</Label>
                    <Input
                      value={header.name || ''}
                      onChange={(e) => handleCustomHeaderChange(index, 'name', e.target.value)}
                      placeholder="Authorization"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Header Value</Label>
                    {header.secret ? (
                      renderSecretField(
                        header.value,
                        (value) => handleCustomHeaderChange(index, 'value', value),
                        'Header value',
                        `customHeader_${index}`
                      )
                    ) : (
                      <Input
                        value={header.value || ''}
                        onChange={(e) => handleCustomHeaderChange(index, 'value', e.target.value)}
                        placeholder="Header value"
                      />
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id={`secret_${index}`}
                    checked={header.secret === true}
                    onCheckedChange={(checked) => handleCustomHeaderChange(index, 'secret', checked)}
                  />
                  <Label htmlFor={`secret_${index}`}>This header contains sensitive data</Label>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Additional Security Options */}
      {authType !== 'none' && (
        <Card>
          <CardHeader>
            <CardTitle>Security Options</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="validate_ssl"
                checked={config.validateSsl !== false}
                onCheckedChange={(checked) => handleConfigChange('validateSsl', checked)}
              />
              <Label htmlFor="validate_ssl">Validate SSL certificates</Label>
            </div>
            
            <div className="space-y-2">
              <Label>Connection Timeout (seconds)</Label>
              <Input
                type="number"
                min="1"
                max="300"
                value={config.connectionTimeout || 30}
                onChange={(e) => handleConfigChange('connectionTimeout', parseInt(e.target.value) || 30)}
              />
            </div>

            {triggerType === 'webhook' && (
              <div className="space-y-2">
                <Label>Allowed IP Ranges (Optional)</Label>
                <Textarea
                  value={config.allowedIps || ''}
                  onChange={(e) => handleConfigChange('allowedIps', e.target.value)}
                  placeholder="192.168.1.0/24&#10;10.0.0.0/8"
                  rows={3}
                />
                <p className="text-xs text-gray-500">
                  One IP address or CIDR range per line. Leave empty to allow all IPs.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Configuration Summary */}
      {authType !== 'none' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>Configuration Summary</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Authentication Type:</span>
                <Badge>{AUTH_TYPES.find(t => t.id === authType)?.name}</Badge>
              </div>
              {authType === 'api_key' && config.apiKeyName && (
                <div className="flex justify-between">
                  <span>API Key Header:</span>
                  <code className="text-xs bg-gray-100 px-2 py-1 rounded">{config.apiKeyName}</code>
                </div>
              )}
              {authType === 'custom' && config.customHeaders && (
                <div className="flex justify-between">
                  <span>Custom Headers:</span>
                  <span>{config.customHeaders.length} configured</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>SSL Validation:</span>
                <Badge variant={config.validateSsl !== false ? 'default' : 'secondary'}>
                  {config.validateSsl !== false ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span>Timeout:</span>
                <span>{config.connectionTimeout || 30}s</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AuthConfig;