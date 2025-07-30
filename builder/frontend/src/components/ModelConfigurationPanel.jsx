// src/components/ModelConfigurationPanel.jsx
import React, { useState, useEffect } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, Settings, Eye, EyeOff, AlertCircle, TestTube, CheckCircle2 } from 'lucide-react';
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

const ModelConfigurationPanel = () => {
  const models = useStore((state) => state.models);
  const fetchModels = useStore((state) => state.fetchModels);
  const addModel = useStore((state) => state.addModel);
  const deleteModel = useStore((state) => state.deleteModel);
  const setDefaultModel = useStore((state) => state.setDefaultModel);

  // Provider presets for better UX
  const providerPresets = {
    openai: { base_url: 'https://api.openai.com/v1', placeholder: 'gpt-4' },
    anthropic: { base_url: 'https://api.anthropic.com', placeholder: 'claude-3-opus-20240229' },
    ollama: { base_url: 'http://localhost:11434/v1', placeholder: 'llama2' },
    custom: { base_url: '', placeholder: 'model-name' }
  };

  const [newModel, setNewModel] = useState({
    name: '',
    provider: 'openai',
    api_key: '',
    base_url: providerPresets.openai.base_url,
    model_name: ''
  });

  const [showApiKeys, setShowApiKeys] = useState({});
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [testingModel, setTestingModel] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);


  const handleAddModel = async () => {
    // Validate required fields
    const hasRequiredFields = newModel.name && newModel.base_url && newModel.model_name && 
      (newModel.provider === 'ollama' || newModel.api_key);
    
    if (hasRequiredFields) {
      setIsLoading(true);
      setError(null);
      try {
        // Set default API key for Ollama if not provided
        const modelToAdd = newModel.provider === 'ollama' && !newModel.api_key 
          ? { ...newModel, api_key: 'ollama' }
          : newModel;
          
        await addModel(modelToAdd);
        setNewModel({ 
          name: '', 
          provider: 'openai', 
          api_key: '', 
          base_url: providerPresets.openai.base_url, 
          model_name: '' 
        });
        setIsDialogOpen(false);
        setTestResult(null);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to add model');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleDeleteModel = async (id) => {
    if (models.length > 1) {
      setIsLoading(true);
      try {
        await deleteModel(id);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to delete model');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleSetDefaultModel = async (id) => {
    setIsLoading(true);
    try {
      await setDefaultModel(id);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to set default model');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleApiKeyVisibility = (id) => {
    setShowApiKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const maskApiKey = (apiKey) => {
    if (!apiKey || apiKey.length <= 8) return '*'.repeat(apiKey?.length || 0);
    return apiKey.substring(0, 4) + '*'.repeat(apiKey.length - 8) + apiKey.substring(apiKey.length - 4);
  };

  const handleTestModel = async () => {
    setTestingModel(true);
    setTestResult(null);
    setError(null);
    
    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/tframex/models/test`,
        newModel
      );
      
      if (response.data.success) {
        setTestResult({ success: true, message: 'Model connection successful!' });
      } else {
        setTestResult({ success: false, message: response.data.error || 'Test failed' });
      }
    } catch (err) {
      setTestResult({ 
        success: false, 
        message: err.response?.data?.error || 'Connection test failed'
      });
    } finally {
      setTestingModel(false);
    }
  };

  return (
    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-9"
          title="Configure AI Models"
        >
          <Settings className="h-4 w-4 mr-2" />
          Models
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>AI Model Configuration</DialogTitle>
          <DialogDescription>
            Configure multiple LLM providers for your agents. Each agent can use a different model.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto flex-grow px-1">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Existing Models */}
          <div className="space-y-3 mt-2">
            {models.map((model) => (
              <Card key={model.id} className={`${model.is_default ? 'ring-2 ring-primary' : ''}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">
                      {model.name}
                      {model.is_default && (
                        <span className="ml-2 text-xs bg-primary/20 text-primary px-2 py-1 rounded-full">
                          Default
                        </span>
                      )}
                    </CardTitle>
                    <div className="flex items-center space-x-2">
                      {!model.is_default && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSetDefaultModel(model.id)}
                          className="h-8"
                          disabled={isLoading}
                        >
                          Set Default
                        </Button>
                      )}
                      {!model.is_default && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteModel(model.id)}
                          disabled={models.length <= 1 || isLoading}
                          className="h-8 w-8"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground mb-1 block">
                        Model
                      </label>
                      <div className="text-sm bg-muted/50 px-3 py-2 rounded-md text-muted-foreground">
                        {model.model_name}
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground mb-1 block">
                        Provider
                      </label>
                      <div className="text-sm bg-muted/50 px-3 py-2 rounded-md capitalize flex items-center text-muted-foreground">
                        <span className={`w-2 h-2 rounded-full mr-2 ${
                          model.provider === 'openai' ? 'bg-green-500' :
                          model.provider === 'anthropic' ? 'bg-purple-500' :
                          model.provider === 'ollama' ? 'bg-orange-500' :
                          'bg-gray-500'
                        }`} />
                        {model.provider}
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">
                      Base URL
                    </label>
                    <div className="text-sm bg-muted/50 px-3 py-2 rounded-md truncate text-muted-foreground">
                      {model.base_url}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">
                      API Key
                    </label>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 text-sm bg-muted/50 px-3 py-2 rounded-md font-mono text-muted-foreground break-all">
                        {showApiKeys[model.id] ? model.api_key : maskApiKey(model.api_key)}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => toggleApiKeyVisibility(model.id)}
                        className="h-8 w-8"
                      >
                        {showApiKeys[model.id] ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Add New Model Form */}
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center">
                <Plus className="h-4 w-4 mr-2" />
                Add New Model
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Display Name
                  </label>
                  <Input
                    value={newModel.name}
                    onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                    placeholder="My Custom Model"
                    className="h-9"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Provider
                  </label>
                  <Select
                    value={newModel.provider}
                    onValueChange={(value) => {
                      setNewModel({
                        ...newModel,
                        provider: value,
                        base_url: providerPresets[value].base_url
                      });
                    }}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                      <SelectItem value="ollama">Ollama (Local)</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Model Name
                  </label>
                  <Input
                    value={newModel.model_name}
                    onChange={(e) => setNewModel({ ...newModel, model_name: e.target.value })}
                    placeholder={providerPresets[newModel.provider].placeholder}
                    className="h-9"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Base URL
                  </label>
                  <Input
                    value={newModel.base_url}
                    onChange={(e) => setNewModel({ ...newModel, base_url: e.target.value })}
                    placeholder="https://api.example.com/v1"
                    className={`h-9 ${newModel.provider !== 'custom' ? 'text-muted-foreground' : ''}`}
                    disabled={newModel.provider !== 'custom'}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  API Key
                </label>
                <Input
                  type="password"
                  value={newModel.api_key}
                  onChange={(e) => setNewModel({ ...newModel, api_key: e.target.value })}
                  placeholder={newModel.provider === 'ollama' ? 'ollama (or leave empty)' : 'sk-...'}
                  className="h-9"
                />
              </div>
              {testResult && (
                <Alert variant={testResult.success ? "default" : "destructive"} className="py-2">
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <AlertDescription className="text-xs">
                    {testResult.message}
                  </AlertDescription>
                </Alert>
              )}
              
              <div className="flex gap-2">
                <Button
                  onClick={handleTestModel}
                  variant="outline"
                  className="flex-1 h-9"
                  disabled={
                    (newModel.provider !== 'ollama' && !newModel.api_key) || 
                    !newModel.base_url || 
                    !newModel.model_name || 
                    testingModel
                  }
                >
                  <TestTube className="h-4 w-4 mr-2" />
                  {testingModel ? 'Testing...' : 'Test Connection'}
                </Button>
                <Button
                  onClick={handleAddModel}
                  className="flex-1 h-9"
                  disabled={
                    !newModel.name || 
                    (newModel.provider !== 'ollama' && !newModel.api_key) || 
                    !newModel.base_url || 
                    !newModel.model_name || 
                    isLoading
                  }
                >
                  {isLoading ? 'Adding...' : 'Add Model'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ModelConfigurationPanel;