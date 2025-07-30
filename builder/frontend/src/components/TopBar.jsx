// src/components/TopBar.jsx
import React, { useState, useCallback, useEffect } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Save, Play, Trash2, Plus, FolderOpen, Code, Settings, Database, Check } from 'lucide-react';
import ModelConfigurationPanel from './ModelConfigurationPanel';

const TopBar = () => {
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);
  const loadProject = useStore((state) => state.loadProject);
  const createProject = useStore((state) => state.createProject);
  const deleteProject = useStore((state) => state.deleteProject);
  const saveCurrentProject = useStore((state) => state.saveCurrentProject);
  const runFlow = useStore((state) => state.runFlow);
  const isRunning = useStore((state) => state.isRunning);

  const [newProjectName, setNewProjectName] = useState('');
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle', 'saving', 'saved'

  const handleCreateProject = useCallback(() => {
    if (newProjectName.trim()) {
      createProject(newProjectName.trim());
      setNewProjectName('');
    }
  }, [createProject, newProjectName]);

  const handleProjectChange = (value) => {
    if (value) {
      loadProject(value);
    }
  };

  const handleDeleteClick = () => {
    if (currentProjectId && window.confirm(`Delete project "${projects[currentProjectId]?.name}"?`)) {
      deleteProject(currentProjectId);
    }
  };

  const handleSaveClick = useCallback(() => {
    setSaveStatus('saving');
    saveCurrentProject();
    setSaveStatus('saved');
  }, [saveCurrentProject]);

  // Reset save status after showing success feedback
  useEffect(() => {
    if (saveStatus === 'saved') {
      const timer = setTimeout(() => {
        setSaveStatus('idle');
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  return (
    <div className="h-14 bg-sidebar border-b border-sidebar-border flex items-center justify-between px-6 flex-shrink-0">
      {/* Left Side: Project Controls */}
      <div className="flex items-center space-x-6">
        {/* Project Controls */}
        <div className="flex items-center space-x-2">
          <Select
            value={currentProjectId || ''}
            onValueChange={handleProjectChange}
            disabled={isRunning}
          >
            <SelectTrigger className="w-[200px] h-9">
              <FolderOpen className="h-4 w-4 mr-2 text-muted-foreground" />
              <SelectValue placeholder="Select Project" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(projects).map(([id, project]) => (
                <SelectItem key={id} value={id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex items-center">
            <Input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateProject()}
              placeholder="New project..."
              className="w-32 h-9 rounded-r-none border-r-0"
              disabled={isRunning}
            />
            <Button
              onClick={handleCreateProject}
              variant="secondary"
              size="sm"
              className="rounded-l-none h-9"
              disabled={isRunning || !newProjectName.trim()}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          <Button
            onClick={handleDeleteClick}
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            disabled={isRunning || !currentProjectId || Object.keys(projects).length <= 1}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Right Side: Action Buttons */}
      <div className="flex items-center space-x-2">
        <ModelConfigurationPanel />

        <Button
          onClick={handleSaveClick}
          variant="ghost"
          size="sm"
          className={`h-9 transition-colors ${
            saveStatus === 'saved' 
              ? 'bg-green-100 text-green-700 hover:bg-green-100' 
              : ''
          }`}
          disabled={isRunning || saveStatus === 'saving'}
        >
          {saveStatus === 'saved' ? (
            <>
              <Check className="h-4 w-4 mr-2" />
              Saved!
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {saveStatus === 'saving' ? 'Saving...' : 'Save'}
            </>
          )}
        </Button>

        <Button
          onClick={runFlow}
          size="sm"
          className={`h-9 min-w-[100px] ${
            isRunning 
              ? 'bg-primary/20 text-primary cursor-not-allowed' 
              : 'bg-primary text-primary-foreground hover:bg-primary/90'
          }`}
          disabled={isRunning}
        >
          {isRunning ? (
            <>
              <div className="h-4 w-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Running
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Flow
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

export default TopBar;