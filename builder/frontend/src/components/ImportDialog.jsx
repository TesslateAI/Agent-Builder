// src/components/ImportDialog.jsx
import React, { useState, useRef } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, FileText, AlertCircle, CheckCircle2, Info, FileUp } from 'lucide-react';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getLayoutedElements, LAYOUT_DIRECTIONS } from '../utils/autoLayout';

const ImportDialog = ({ trigger }) => {
  const setNodes = useStore((state) => state.setNodes);
  const setEdges = useStore((state) => state.setEdges);
  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);

  const [importContent, setImportContent] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [error, setError] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  
  const fileInputRef = useRef(null);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      setImportContent(content);
      validateContent(content);
    };
    reader.readAsText(file);
  };

  const validateContent = async (content) => {
    if (!content.trim()) {
      setValidationResult(null);
      setError(null);
      return;
    }

    setIsValidating(true);
    setError(null);
    setValidationResult(null);

    try {
      const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/tframex';
      const response = await axios.post(`${API_BASE_URL}/flows/import/validate`, {
        content: content
      });

      if (response.data.valid) {
        setValidationResult(response.data);
      } else {
        setError(response.data.error || 'Invalid format');
      }

    } catch (err) {
      console.error('Validation failed:', err);
      setError(err.response?.data?.error || err.message || 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  };

  const handleContentChange = (value) => {
    setImportContent(value);
    // Debounce validation
    clearTimeout(window.importValidationTimeout);
    window.importValidationTimeout = setTimeout(() => {
      validateContent(value);
    }, 500);
  };

  const handleImport = async () => {
    if (!importContent.trim()) {
      setError('Please provide content to import');
      return;
    }

    setIsImporting(true);
    setError(null);

    try {
      const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/tframex';
      const response = await axios.post(`${API_BASE_URL}/flows/import`, {
        content: importContent
      });

      if (response.data.success) {
        const importedFlow = response.data.flow;
        
        // Option 1: Replace current flow
        if (nodes.length === 0 || window.confirm('Replace current flow with imported flow? This will clear the current canvas.')) {
          setNodes(importedFlow.nodes || []);
          setEdges(importedFlow.edges || []);
        } else {
          // Option 2: Merge with current flow (add to existing)
          const mergedNodes = [...nodes, ...(importedFlow.nodes || [])];
          const mergedEdges = [...edges, ...(importedFlow.edges || [])];
          
          // Apply auto-layout to avoid overlaps
          const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            mergedNodes, 
            mergedEdges, 
            LAYOUT_DIRECTIONS.LEFT_TO_RIGHT
          );
          
          setNodes(layoutedNodes);
          setEdges(layoutedEdges);
        }

        // Show warnings if any
        if (response.data.warnings?.length > 0) {
          console.warn('Import warnings:', response.data.warnings);
        }

        // Close dialog on success
        setIsDialogOpen(false);
        
        // Reset state
        setImportContent('');
        setValidationResult(null);
        setError(null);

      } else {
        setError('Import failed: ' + (response.data.error || 'Unknown error'));
      }

    } catch (err) {
      console.error('Import failed:', err);
      setError(err.response?.data?.error || err.message || 'Import failed');
    } finally {
      setIsImporting(false);
    }
  };

  const handleDialogOpenChange = (open) => {
    setIsDialogOpen(open);
    if (!open) {
      // Reset state when closing
      setImportContent('');
      setValidationResult(null);
      setError(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Dialog open={isDialogOpen} onOpenChange={handleDialogOpenChange}>
      {trigger || (
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9">
                <Upload className="h-4 w-4" />
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            <p>Import Flow</p>
          </TooltipContent>
        </Tooltip>
      )}
      
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
        <DialogHeader className="pb-4">
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Upload className="h-4 w-4" />
            Import Flow
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Import a flow from JSON, YAML, Mermaid formats or paste content directly.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto max-h-[calc(80vh-120px)]">
          {/* File Upload */}
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="space-y-3">
              <label className="text-sm font-medium flex items-center gap-2">
                <FileUp className="h-4 w-4" />
                Upload File
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.yaml,.yml,.mmd"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <Button 
                variant="outline" 
                onClick={() => fileInputRef.current?.click()}
                className="w-full border-dashed border-2 hover:border-primary/50 hover:bg-primary/5 transition-all duration-200"
              >
                <FileUp className="h-4 w-4 mr-2" />
                Choose File (.json, .yaml, .mmd)
              </Button>
            </div>
          </div>

          {/* Text Input */}
          <div className="space-y-3">
            <label className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Or Paste Content
            </label>
            <Textarea
              value={importContent}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder="Paste your flow content here (JSON, YAML, or Mermaid format)..."
              className="min-h-[150px] max-h-[200px] font-mono text-sm resize-none"
            />
            {importContent && (
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Content length: {formatFileSize(new Blob([importContent]).size)}</span>
                <span className={isValidating ? "text-amber-400" : validationResult ? "text-green-400" : error ? "text-red-400" : ""}>
                  {isValidating ? "Validating..." : validationResult ? "✓ Valid" : error ? "✗ Invalid" : "Ready"}
                </span>
              </div>
            )}
          </div>

          {/* Validation Status */}
          {isValidating && (
            <Alert className="bg-amber-500/10 border-amber-500/20 text-amber-400">
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              <AlertDescription>Validating content...</AlertDescription>
            </Alert>
          )}

          {/* Validation Success */}
          {validationResult && !error && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Valid format detected</div>
                    <div className="text-sm text-muted-foreground">
                      {validationResult.preview?.nodes_count} nodes, {validationResult.preview?.edges_count} connections
                    </div>
                  </div>
                  <div className="bg-muted px-2 py-1 rounded text-xs font-mono">
                    {validationResult.detected_format?.toUpperCase()}
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Dependencies Info */}
          {validationResult?.preview?.dependencies && (
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Dependencies
                </label>
                <div className="text-sm space-y-2">
                  {validationResult.preview.dependencies.custom_components?.length > 0 && (
                    <div>
                      <div className="font-medium mb-1">Custom Components:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.custom_components.map((comp, i) => (
                          <span key={i} className="px-2 py-1 bg-orange-500/10 text-orange-400 text-xs rounded">
                            {comp}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {validationResult.preview.dependencies.required_models?.length > 0 && (
                    <div>
                      <div className="font-medium mb-1">Required Models:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.required_models.map((model, i) => (
                          <span key={i} className="px-2 py-1 bg-purple-500/10 text-purple-400 text-xs rounded">
                            {model}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {validationResult.preview.dependencies.mcp_servers?.length > 0 && (
                    <div>
                      <div className="font-medium mb-1">MCP Servers:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.mcp_servers.map((server, i) => (
                          <span key={i} className="px-2 py-1 bg-teal-500/10 text-teal-400 text-xs rounded">
                            {server}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Import Options Info */}
          {validationResult && nodes.length > 0 && (
            <Alert className="bg-amber-500/10 border-amber-500/20 text-amber-400">
              <Info className="h-4 w-4" />
              <AlertDescription>
                You have {nodes.length} nodes on the current canvas. 
                Import will ask whether to replace or merge with existing flow.
              </AlertDescription>
            </Alert>
          )}

          {/* Import Button */}
          <Button 
            onClick={handleImport} 
            disabled={!validationResult || isImporting || isValidating}
            className="w-full"
          >
            {isImporting ? (
              <>
                <div className="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
                <span>Importing Flow...</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                <span>Import Flow</span>
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImportDialog;