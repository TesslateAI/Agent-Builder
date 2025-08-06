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
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="icon" className="h-9 w-9" title="Import Flow">
            <Upload className="h-4 w-4" />
          </Button>
        )}
      </DialogTrigger>
      
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden bg-card/95 backdrop-blur-xl border-border/50">
        <DialogHeader className="pb-6 border-b border-border/50">
          <DialogTitle className="flex items-center gap-3 text-xl font-semibold">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Upload className="h-5 w-5" />
            </div>
            Import Flow
          </DialogTitle>
          <DialogDescription className="text-muted-foreground mt-2">
            Import a flow from JSON, YAML, Mermaid formats or paste content directly.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto max-h-[calc(90vh-140px)] px-1">
          {/* File Upload */}
          <Card className="bg-card/50 backdrop-blur border-border/30 hover:bg-card/70 transition-all duration-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-3 font-medium">
                <div className="p-1.5 rounded-md bg-blue-500/10 text-blue-400">
                  <FileUp className="h-4 w-4" />
                </div>
                Upload File
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-4">
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
                  className="w-full h-12 border-dashed border-2 hover:border-primary/50 hover:bg-primary/5 transition-all duration-200"
                >
                  <FileUp className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Choose File</div>
                    <div className="text-xs text-muted-foreground">.json, .yaml, .mmd</div>
                  </div>
                </Button>
                <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                  <div className="h-px bg-border flex-1"></div>
                  <span>Supported formats: JSON, YAML, Mermaid</span>
                  <div className="h-px bg-border flex-1"></div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Text Input */}
          <Card className="bg-card/50 backdrop-blur border-border/30 hover:bg-card/70 transition-all duration-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-3 font-medium">
                <div className="p-1.5 rounded-md bg-green-500/10 text-green-400">
                  <FileText className="h-4 w-4" />
                </div>
                Or Paste Content
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <Textarea
                  value={importContent}
                  onChange={(e) => handleContentChange(e.target.value)}
                  placeholder="Paste your flow content here (JSON, YAML, or Mermaid format)..."
                  className="min-h-[200px] font-mono text-sm bg-background/50 border-border/50 focus:border-primary/50 resize-none transition-all duration-200"
                />
                {importContent && (
                  <div className="flex items-center justify-between text-xs text-muted-foreground px-2">
                    <span>Content length: {formatFileSize(new Blob([importContent]).size)}</span>
                    <span className={isValidating ? "text-amber-400" : validationResult ? "text-green-400" : error ? "text-red-400" : ""}>
                      {isValidating ? "Validating..." : validationResult ? "✓ Valid" : error ? "✗ Invalid" : "Ready"}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Validation Status */}
          {isValidating && (
            <Alert className="bg-amber-500/10 border-amber-500/20 text-amber-400">
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              <AlertDescription className="font-medium">Validating content...</AlertDescription>
            </Alert>
          )}

          {/* Validation Success */}
          {validationResult && !error && (
            <Alert className="bg-green-500/10 border-green-500/20 text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <div className="font-medium flex items-center gap-2">
                    <span className="bg-green-500/20 px-2 py-0.5 rounded text-xs font-semibold">
                      {validationResult.detected_format?.toUpperCase()}
                    </span>
                    Valid format detected
                  </div>
                  <div className="text-sm text-foreground font-medium">
                    {validationResult.preview?.name}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                      {validationResult.preview?.nodes_count} nodes
                    </span>
                    <span className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                      {validationResult.preview?.edges_count} connections
                    </span>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Dependencies Info */}
          {validationResult?.preview?.dependencies && (
            <Card className="bg-blue-500/5 backdrop-blur border-blue-500/20">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-3 font-medium text-blue-400">
                  <div className="p-1.5 rounded-md bg-blue-500/10">
                    <Info className="h-4 w-4" />
                  </div>
                  Dependencies
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-3 text-sm">
                  {validationResult.preview.dependencies.custom_components?.length > 0 && (
                    <div className="p-3 rounded-lg bg-background/50 border border-border/30">
                      <div className="font-medium text-foreground mb-1">Custom Components:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.custom_components.map((comp, i) => (
                          <span key={i} className="px-2 py-1 bg-orange-500/10 text-orange-400 text-xs rounded border border-orange-500/20">
                            {comp}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {validationResult.preview.dependencies.required_models?.length > 0 && (
                    <div className="p-3 rounded-lg bg-background/50 border border-border/30">
                      <div className="font-medium text-foreground mb-1">Required Models:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.required_models.map((model, i) => (
                          <span key={i} className="px-2 py-1 bg-purple-500/10 text-purple-400 text-xs rounded border border-purple-500/20">
                            {model}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {validationResult.preview.dependencies.mcp_servers?.length > 0 && (
                    <div className="p-3 rounded-lg bg-background/50 border border-border/30">
                      <div className="font-medium text-foreground mb-1">MCP Servers:</div>
                      <div className="flex flex-wrap gap-1">
                        {validationResult.preview.dependencies.mcp_servers.map((server, i) => (
                          <span key={i} className="px-2 py-1 bg-teal-500/10 text-teal-400 text-xs rounded border border-teal-500/20">
                            {server}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive" className="bg-red-500/10 border-red-500/20 text-red-400">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="font-medium">{error}</AlertDescription>
            </Alert>
          )}

          {/* Import Options Info */}
          {validationResult && nodes.length > 0 && (
            <Alert className="bg-amber-500/10 border-amber-500/20 text-amber-400">
              <Info className="h-4 w-4" />
              <AlertDescription className="font-medium">
                You have {nodes.length} nodes on the current canvas. 
                Import will ask whether to replace or merge with existing flow.
              </AlertDescription>
            </Alert>
          )}

          {/* Import Button */}
          <div className="sticky bottom-0 bg-card/95 backdrop-blur-xl border-t border-border/50 pt-4 -mx-1 px-1">
            <Button 
              onClick={handleImport} 
              disabled={!validationResult || isImporting || isValidating}
              className="w-full h-12 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              {isImporting ? (
                <>
                  <div className="w-5 h-5 mr-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  <span>Importing Flow...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5 mr-3" />
                  <span>Import Flow</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImportDialog;