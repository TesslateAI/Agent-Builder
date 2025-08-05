// components/triggers/FileConfig.jsx
import React, { useCallback, useState } from 'react';
import { FolderOpen, File, Eye, CheckCircle, XCircle, TestTube, HardDrive } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';

const WATCH_EVENTS = [
  { id: 'created', label: 'File Created', description: 'Trigger when new files are created' },
  { id: 'modified', label: 'File Modified', description: 'Trigger when files are changed' },
  { id: 'deleted', label: 'File Deleted', description: 'Trigger when files are removed' },
  { id: 'moved', label: 'File Moved/Renamed', description: 'Trigger when files are moved or renamed' }
];

const COMMON_EXTENSIONS = [
  '.txt', '.log', '.csv', '.json', '.xml', '.pdf', '.doc', '.docx', 
  '.xls', '.xlsx', '.jpg', '.png', '.gif', '.mp4', '.zip', '.tar.gz'
];

const FileConfig = ({ config, onChange }) => {
  const [testStatus, setTestStatus] = useState(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleConfigChange = useCallback((field, value) => {
    const newConfig = {
      ...config,
      [field]: value
    };
    onChange(newConfig);
  }, [config, onChange]);

  const handleWatchEventChange = useCallback((eventId, checked) => {
    const currentEvents = config.watchEvents || ['created'];
    let newEvents;
    
    if (checked) {
      newEvents = [...currentEvents, eventId];
    } else {
      newEvents = currentEvents.filter(e => e !== eventId);
    }
    
    // Ensure at least one event is selected
    if (newEvents.length === 0) {
      newEvents = ['created'];
    }
    
    handleConfigChange('watchEvents', newEvents);
  }, [config.watchEvents, handleConfigChange]);

  const handleExtensionAdd = useCallback((extension) => {
    const currentExtensions = config.fileExtensions || [];
    if (!currentExtensions.includes(extension)) {
      handleConfigChange('fileExtensions', [...currentExtensions, extension]);
    }
  }, [config.fileExtensions, handleConfigChange]);

  const handleExtensionRemove = useCallback((extension) => {
    const currentExtensions = config.fileExtensions || [];
    handleConfigChange('fileExtensions', currentExtensions.filter(ext => ext !== extension));
  }, [config.fileExtensions, handleConfigChange]);

  const testPath = useCallback(async () => {
    setIsTesting(true);
    setTestStatus(null);

    try {
      // This would normally call the backend API to test the path
      // For now, just simulate a test
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simulate success/failure based on whether path is provided
      if (config.watchPath) {
        setTestStatus({ 
          success: true, 
          message: 'Path accessible',
          details: {
            exists: true,
            readable: true,
            writable: false,
            type: 'directory'
          }
        });
      } else {
        setTestStatus({ success: false, message: 'Path is required' });
      }
    } catch (error) {
      setTestStatus({ success: false, message: error.message });
    } finally {
      setIsTesting(false);
    }
  }, [config.watchPath]);

  const formatBytes = useCallback((bytes) => {
    if (!bytes) return '';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  return (
    <div className="space-y-6">
      {/* Watch Path */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FolderOpen className="h-4 w-4" />
            <span>Watch Path</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>File or Directory Path</Label>
            <div className="flex space-x-2">
              <Input
                value={config.watchPath || ''}
                onChange={(e) => handleConfigChange('watchPath', e.target.value)}
                placeholder="/path/to/watch or C:\\path\\to\\watch"
                className="flex-1"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={testPath}
                disabled={isTesting || !config.watchPath}
              >
                <TestTube className="h-4 w-4 mr-2" />
                {isTesting ? 'Testing...' : 'Test'}
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Absolute path to file or directory to monitor for changes
            </p>
            
            {testStatus && (
              <div className={`p-3 rounded-lg ${testStatus.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center space-x-2 mb-2">
                  {testStatus.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <span className={`text-sm font-medium ${testStatus.success ? 'text-green-800' : 'text-red-800'}`}>
                    {testStatus.message}
                  </span>
                </div>
                {testStatus.details && (
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>Type: {testStatus.details.type}</div>
                    <div>Readable: {testStatus.details.readable ? 'Yes' : 'No'}</div>
                    <div>Writable: {testStatus.details.writable ? 'Yes' : 'No'}</div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="recursive"
              checked={config.recursive === true}
              onCheckedChange={(checked) => handleConfigChange('recursive', checked)}
            />
            <Label htmlFor="recursive">Monitor subdirectories recursively</Label>
          </div>
        </CardContent>
      </Card>

      {/* Watch Events */}
      <Card>
        <CardHeader>
          <CardTitle>Events to Monitor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {WATCH_EVENTS.map(event => (
            <div key={event.id} className="flex items-start space-x-3">
              <Checkbox
                id={event.id}
                checked={(config.watchEvents || ['created']).includes(event.id)}
                onCheckedChange={(checked) => handleWatchEventChange(event.id, checked)}
              />
              <div className="space-y-1">
                <Label htmlFor={event.id} className="text-sm font-medium">
                  {event.label}
                </Label>
                <p className="text-xs text-gray-500">
                  {event.description}
                </p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* File Filters */}
      <Card>
        <CardHeader>
          <CardTitle>File Filters (Optional)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>File Name Pattern</Label>
            <Input
              value={config.filePattern || ''}
              onChange={(e) => handleConfigChange('filePattern', e.target.value)}
              placeholder="*.log or report_*.csv"
            />
            <p className="text-xs text-gray-500">
              Wildcard pattern to match file names (* for any characters, ? for single character)
            </p>
          </div>

          <div className="space-y-2">
            <Label>File Extensions</Label>
            <div className="flex flex-wrap gap-2 mb-2">
              {(config.fileExtensions || []).map(ext => (
                <Badge 
                  key={ext} 
                  variant="secondary" 
                  className="cursor-pointer hover:bg-red-100"
                  onClick={() => handleExtensionRemove(ext)}
                >
                  {ext}
                  <XCircle className="h-3 w-3 ml-1" />
                </Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-1">
              {COMMON_EXTENSIONS.filter(ext => !(config.fileExtensions || []).includes(ext)).map(ext => (
                <Button
                  key={ext}
                  variant="outline"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => handleExtensionAdd(ext)}
                >
                  {ext}
                </Button>
              ))}
            </div>
            <p className="text-xs text-gray-500">
              Click extensions to add/remove. Leave empty to monitor all file types.
            </p>
          </div>

          <Separator />

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Minimum File Size</Label>
              <div className="flex space-x-2">
                <Input
                  type="number"
                  min="0"
                  value={config.minSize || ''}
                  onChange={(e) => handleConfigChange('minSize', e.target.value ? parseInt(e.target.value) : '')}
                  placeholder="0"
                />
                <Badge variant="outline" className="shrink-0">
                  {formatBytes(config.minSize) || 'bytes'}
                </Badge>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Maximum File Size</Label>
              <div className="flex space-x-2">
                <Input
                  type="number"
                  min="0"
                  value={config.maxSize || ''}
                  onChange={(e) => handleConfigChange('maxSize', e.target.value ? parseInt(e.target.value) : '')}
                  placeholder="unlimited"
                />
                <Badge variant="outline" className="shrink-0">
                  {formatBytes(config.maxSize) || 'unlimited'}
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="include_hash"
              checked={config.includeHash === true}
              onCheckedChange={(checked) => handleConfigChange('includeHash', checked)}
            />
            <Label htmlFor="include_hash">Include file content hash (for files &lt; 10MB)</Label>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      {config.watchPath && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Eye className="h-4 w-4" />
              <span>Configuration Preview</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <div><strong>Path:</strong> {config.watchPath}</div>
            <div><strong>Recursive:</strong> {config.recursive ? 'Yes' : 'No'}</div>
            <div><strong>Events:</strong> {(config.watchEvents || ['created']).join(', ')}</div>
            {config.filePattern && (
              <div><strong>Pattern:</strong> {config.filePattern}</div>
            )}
            {config.fileExtensions && config.fileExtensions.length > 0 && (
              <div><strong>Extensions:</strong> {config.fileExtensions.join(', ')}</div>
            )}
            {config.minSize && (
              <div><strong>Min Size:</strong> {formatBytes(config.minSize)}</div>
            )}
            {config.maxSize && (
              <div><strong>Max Size:</strong> {formatBytes(config.maxSize)}</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FileConfig;