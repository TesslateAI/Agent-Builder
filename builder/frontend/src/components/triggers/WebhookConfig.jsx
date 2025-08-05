// components/triggers/WebhookConfig.jsx
import React, { useCallback } from 'react';
import { Copy, Eye, EyeOff, Globe, Shield, Key } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

const WebhookConfig = ({ config, onChange }) => {
  const [showSecret, setShowSecret] = React.useState(false);

  const handleConfigChange = useCallback((field, value) => {
    const newConfig = {
      ...config,
      [field]: value
    };
    onChange(newConfig);
  }, [config, onChange]);

  const handleAuthConfigChange = useCallback((field, value) => {
    const newAuthConfig = {
      ...config.authConfig,
      [field]: value
    };
    handleConfigChange('authConfig', newAuthConfig);
  }, [config.authConfig, handleConfigChange]);

  const copyWebhookUrl = () => {
    const url = config.endpoint || '/api/webhook/[trigger-id]';
    const fullUrl = window.location.origin + url;
    navigator.clipboard.writeText(fullUrl);
    // You could add a toast notification here
  };

  return (
    <div className="space-y-6">
      {/* Webhook URL */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Globe className="h-4 w-4" />
            <span>Webhook URL</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label>Webhook Endpoint</Label>
            <div className="flex items-center space-x-2">
              <Input
                value={config.endpoint || '/api/webhook/[auto-generated]'}
                readOnly
                className="bg-gray-50"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={copyWebhookUrl}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              The webhook URL will be auto-generated when the trigger is created
            </p>
          </div>
        </CardContent>
      </Card>

      {/* HTTP Method */}
      <div className="space-y-2">
        <Label>HTTP Method</Label>
        <Select
          value={config.method || 'POST'}
          onValueChange={(value) => handleConfigChange('method', value)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GET">GET</SelectItem>
            <SelectItem value="POST">POST</SelectItem>
            <SelectItem value="PUT">PUT</SelectItem>
            <SelectItem value="DELETE">DELETE</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Separator />

      {/* Authentication */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-4 w-4" />
            <span>Authentication</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Authentication Type</Label>
            <Select
              value={config.authType || 'none'}
              onValueChange={(value) => handleConfigChange('authType', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None (Public endpoint)</SelectItem>
                <SelectItem value="token">Bearer Token</SelectItem>
                <SelectItem value="hmac">HMAC Signature</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {config.authType === 'token' && (
            <div className="space-y-2">
              <Label>Bearer Token</Label>
              <div className="relative">
                <Input
                  type={showSecret ? 'text' : 'password'}
                  value={config.authConfig?.token || ''}
                  onChange={(e) => handleAuthConfigChange('token', e.target.value)}
                  placeholder="Enter authentication token"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-gray-500">
                Include this token in the Authorization header: Bearer [token]
              </p>
            </div>
          )}

          {config.authType === 'hmac' && (
            <div className="space-y-2">
              <Label>HMAC Secret</Label>
              <div className="relative">
                <Input
                  type={showSecret ? 'text' : 'password'}
                  value={config.authConfig?.secret || ''}
                  onChange={(e) => handleAuthConfigChange('secret', e.target.value)}
                  placeholder="Enter HMAC secret"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-gray-500">
                Requests must include X-Hub-Signature-256 header with HMAC-SHA256 signature
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Custom Headers */}
      <div className="space-y-2">
        <Label>Custom Headers (Optional)</Label>
        <Textarea
          value={config.headers ? JSON.stringify(config.headers, null, 2) : '{}'}
          onChange={(e) => {
            try {
              const headers = JSON.parse(e.target.value);
              handleConfigChange('headers', headers);
            } catch {
              // Invalid JSON, don't update
            }
          }}
          placeholder='{\n  "X-Custom-Header": "value"\n}'
          rows={4}
          className="font-mono text-sm"
        />
        <p className="text-xs text-gray-500">
          JSON object of custom headers to validate in incoming requests
        </p>
      </div>

      {/* Payload Schema */}
      <div className="space-y-2">
        <Label>Payload Schema (Optional)</Label>
        <Textarea
          value={config.bodySchema ? JSON.stringify(config.bodySchema, null, 2) : ''}
          onChange={(e) => {
            try {
              if (e.target.value.trim() === '') {
                handleConfigChange('bodySchema', null);
              } else {
                const schema = JSON.parse(e.target.value);
                handleConfigChange('bodySchema', schema);
              }
            } catch {
              // Invalid JSON, don't update
            }
          }}
          placeholder='{\n  "type": "object",\n  "properties": {\n    "message": {"type": "string"}\n  },\n  "required": ["message"]\n}'
          rows={8}
          className="font-mono text-sm"
        />
        <p className="text-xs text-gray-500">
          JSON Schema to validate incoming request payloads (leave empty to accept any payload)
        </p>
      </div>

      {/* Usage Examples */}
      <Card>
        <CardHeader>
          <CardTitle>Usage Examples</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <h4 className="font-medium">cURL Example</h4>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
{`curl -X ${config.method || 'POST'} \\
  ${window.location.origin}/api/webhook/[trigger-id] \\${config.authType === 'token' ? `
  -H "Authorization: Bearer ${config.authConfig?.token || '[your-token]'}" \\` : ''}
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello from webhook"}'`}
            </pre>
          </div>

          {config.authType === 'hmac' && (
            <div className="space-y-2">
              <h4 className="font-medium">HMAC Signature (Node.js)</h4>
              <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
{`const crypto = require('crypto');
const payload = JSON.stringify({message: "Hello"});
const signature = crypto
  .createHmac('sha256', '${config.authConfig?.secret || '[your-secret]'}')
  .update(payload)
  .digest('hex');
// Include as X-Hub-Signature-256: sha256=\${signature}`}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default WebhookConfig;