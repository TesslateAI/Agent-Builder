// src/components/ExportDialog.jsx
import React, { useState } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Download, FileText, Code, GitBranch, AlertCircle, CheckCircle2 } from 'lucide-react';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Textarea } from "@/components/ui/textarea";

const ExportDialog = ({ trigger }) => {
  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);

  const [selectedFormat, setSelectedFormat] = useState('json');
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [error, setError] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const exportFormats = [
    {
      value: 'json',
      label: 'JSON',
      description: 'Complete flow definition with all data',
      icon: <Code className="w-4 h-4" />,
      fileExt: 'json'
    },
    {
      value: 'yaml',
      label: 'YAML',
      description: 'Human-readable format for documentation',
      icon: <FileText className="w-4 h-4" />,
      fileExt: 'yaml'
    },
    {
      value: 'mermaid',
      label: 'Mermaid',
      description: 'Diagram format for visual documentation',
      icon: <GitBranch className="w-4 h-4" />,
      fileExt: 'mmd'
    }
  ];

  const currentProject = projects[currentProjectId];
  const flowName = currentProject?.name || 'Current Flow';

  const handleExport = async () => {
    if (!nodes || nodes.length === 0) {
      setError('No nodes to export. Create a flow first.');
      return;
    }

    setIsExporting(true);
    setError(null);
    setExportResult(null);

    try {
      const payload = {
        name: flowName,
        description: currentProject?.description || '',
        nodes: nodes,
        edges: edges,
        format: selectedFormat
      };

      const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/tframex';
      const response = await axios.post(`${API_BASE_URL}/flows/export-current`, payload);

      if (response.data.content) {
        setExportResult({
          content: response.data.content,
          format: response.data.format,
          filename: response.data.filename
        });
      } else {
        throw new Error('No content received from export');
      }

    } catch (err) {
      console.error('Export failed:', err);
      setError(err.response?.data?.error || err.message || 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownload = () => {
    if (!exportResult) return;

    const blob = new Blob([exportResult.content], {
      type: getContentType(exportResult.format)
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = exportResult.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyToClipboard = async () => {
    if (!exportResult) return;

    try {
      await navigator.clipboard.writeText(exportResult.content);
      // Could add a toast notification here
      console.log('Content copied to clipboard');
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const getContentType = (format) => {
    const types = {
      json: 'application/json',
      yaml: 'application/x-yaml',
      mermaid: 'text/plain'
    };
    return types[format] || 'text/plain';
  };

  const handleDialogOpenChange = (open) => {
    setIsDialogOpen(open);
    if (!open) {
      // Reset state when closing
      setExportResult(null);
      setError(null);
    }
  };

  return (
    <Dialog open={isDialogOpen} onOpenChange={handleDialogOpenChange}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="icon" className="h-9 w-9" title="Export Flow">
            <Download className="h-4 w-4" />
          </Button>
        )}
      </DialogTrigger>
      
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
        <DialogHeader className="pb-4">
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Download className="h-4 w-4" />
            Export Flow
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Export "{flowName}" to different formats for sharing, backup, or documentation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto max-h-[calc(80vh-120px)]">          
          {/* Flow Info */}
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <span className="font-medium">{nodes.length}</span>
                  <span className="text-muted-foreground">nodes</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-medium">{edges.length}</span>
                  <span className="text-muted-foreground">edges</span>
                </div>
              </div>
              <div className="text-sm">
                <span className="font-medium">{currentProject?.name || 'Unnamed Project'}</span>
              </div>
            </div>
          </div>

          {/* Format Selection */}
          <div className="space-y-3">
            <label className="text-sm font-medium">Export Format</label>
            <div className="grid grid-cols-1 gap-2">
              {exportFormats.map((format) => {
                const isSelected = selectedFormat === format.value;
                
                return (
                  <div 
                    key={format.value}
                    className={`cursor-pointer transition-all duration-200 p-3 rounded-lg border ${
                      isSelected 
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-muted/50'
                    }`}
                    onClick={() => setSelectedFormat(format.value)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded">
                        {format.icon}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{format.label}</div>
                        <div className="text-sm text-muted-foreground">{format.description}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 rounded text-xs font-mono bg-muted text-muted-foreground">
                          .{format.fileExt}
                        </span>
                        {isSelected && (
                          <div className="w-2 h-2 rounded-full bg-primary"></div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Export Button */}
          {!exportResult && (
            <Button 
              onClick={handleExport} 
              disabled={isExporting || nodes.length === 0}
              className="w-full"
            >
              {isExporting ? (
                <>
                  <div className="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  <span>Exporting to {selectedFormat.toUpperCase()}...</span>
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  <span>Export as {selectedFormat.toUpperCase()}</span>
                </>
              )}
            </Button>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Export Result */}
          {exportResult && (
            <div className="space-y-4">
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Export successful!</div>
                      <div className="text-sm text-muted-foreground">File ready: {exportResult.filename}</div>
                    </div>
                    <div className="bg-muted px-2 py-1 rounded text-xs font-mono">
                      {exportResult.format?.toUpperCase()}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>

              {/* Preview */}
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Preview
                </label>
                <Textarea
                  value={exportResult.content}
                  readOnly
                  className="min-h-[150px] max-h-[200px] font-mono text-sm resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <Button onClick={handleDownload} className="flex-1">
                  <Download className="w-4 h-4 mr-2" />
                  Download File
                </Button>
                <Button onClick={handleCopyToClipboard} variant="outline">
                  <FileText className="w-4 h-4 mr-2" />
                  Copy
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ExportDialog;