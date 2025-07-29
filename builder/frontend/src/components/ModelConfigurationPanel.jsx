// src/components/ModelConfigurationPanel.jsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, Settings, Eye, EyeOff } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const ModelConfigurationPanel = () => {
  const [models, setModels] = useState([
    {
      id: 1,
      name: 'Default Llama Model',
      apiKey: 'LLM|724781956865705|0pfHARu1VlHMu-wxkjIHDL4KqRU',
      baseUrl: 'https://api.llama.com/compat/v1/',
      modelName: 'Llama-4-Maverick-17B-128E-Instruct-FP8',
      isDefault: true
    }
  ]);

  const [newModel, setNewModel] = useState({
    name: '',
    apiKey: '',
    baseUrl: '',
    modelName: ''
  });

  const [showApiKeys, setShowApiKeys] = useState({});
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const addModel = () => {
    if (newModel.name && newModel.apiKey && newModel.baseUrl && newModel.modelName) {
      const newId = Math.max(...models.map(m => m.id), 0) + 1;
      setModels([...models, {
        ...newModel,
        id: newId,
        isDefault: false
      }]);
      setNewModel({ name: '', apiKey: '', baseUrl: '', modelName: '' });
      setIsDialogOpen(false);
    }
  };

  const removeModel = (id) => {
    if (models.length > 1) {
      setModels(models.filter(m => m.id !== id));
    }
  };

  const setDefaultModel = (id) => {
    setModels(models.map(m => ({ ...m, isDefault: m.id === id })));
  };

  const toggleApiKeyVisibility = (id) => {
    setShowApiKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const maskApiKey = (apiKey) => {
    if (apiKey.length <= 8) return '*'.repeat(apiKey.length);
    return apiKey.substring(0, 4) + '*'.repeat(apiKey.length - 8) + apiKey.substring(apiKey.length - 4);
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
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>AI Model Configuration</DialogTitle>
          <DialogDescription>
            Configure multiple OpenAI-compatible API endpoints for your flows
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Existing Models */}
          <div className="space-y-3">
            {models.map((model) => (
              <Card key={model.id} className={`${model.isDefault ? 'ring-2 ring-primary' : ''}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">
                      {model.name}
                      {model.isDefault && (
                        <span className="ml-2 text-xs bg-primary/20 text-primary px-2 py-1 rounded-full">
                          Default
                        </span>
                      )}
                    </CardTitle>
                    <div className="flex items-center space-x-2">
                      {!model.isDefault && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDefaultModel(model.id)}
                          className="h-8"
                        >
                          Set Default
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeModel(model.id)}
                        disabled={models.length <= 1}
                        className="h-8 w-8"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground mb-1 block">
                        Model Name
                      </label>
                      <div className="text-sm bg-muted/50 px-3 py-2 rounded-md">
                        {model.modelName}
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground mb-1 block">
                        Base URL
                      </label>
                      <div className="text-sm bg-muted/50 px-3 py-2 rounded-md truncate">
                        {model.baseUrl}
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">
                      API Key
                    </label>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 text-sm bg-muted/50 px-3 py-2 rounded-md font-mono">
                        {showApiKeys[model.id] ? model.apiKey : maskApiKey(model.apiKey)}
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
                    Model Name
                  </label>
                  <Input
                    value={newModel.modelName}
                    onChange={(e) => setNewModel({ ...newModel, modelName: e.target.value })}
                    placeholder="gpt-4o-mini"
                    className="h-9"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Base URL
                </label>
                <Input
                  value={newModel.baseUrl}
                  onChange={(e) => setNewModel({ ...newModel, baseUrl: e.target.value })}
                  placeholder="https://api.openai.com/v1/"
                  className="h-9"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  API Key
                </label>
                <Input
                  type="password"
                  value={newModel.apiKey}
                  onChange={(e) => setNewModel({ ...newModel, apiKey: e.target.value })}
                  placeholder="sk-..."
                  className="h-9"
                />
              </div>
              <Button
                onClick={addModel}
                className="w-full h-9"
                disabled={!newModel.name || !newModel.apiKey || !newModel.baseUrl || !newModel.modelName}
              >
                Add Model
              </Button>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ModelConfigurationPanel;