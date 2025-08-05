// src/components/TopBar.jsx
import React, { useState, useCallback, useEffect } from 'react';
import { useStore } from '../store';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Save, Play, Trash2, Plus, FolderOpen, Code, Settings, Database, Check, User, ChevronDown } from 'lucide-react';
import ModelConfigurationPanel from './ModelConfigurationPanel';
import UserProfile from './auth/UserProfile';

const TopBar = () => {
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);
  const loadProject = useStore((state) => state.loadProject);
  const createProject = useStore((state) => state.createProject);
  const deleteProject = useStore((state) => state.deleteProject);
  const saveCurrentProject = useStore((state) => state.saveCurrentProject);
  const runFlow = useStore((state) => state.runFlow);
  const isRunning = useStore((state) => state.isRunning);

  // Auth state
  const { user, isAuthenticated } = useAuth();

  const [newProjectName, setNewProjectName] = useState('');
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle', 'saving', 'saved'
  const [showUserProfile, setShowUserProfile] = useState(false);

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
        {/* User Profile - Only show if authenticated */}
        {isAuthenticated && (
          <Dialog open={showUserProfile} onOpenChange={setShowUserProfile}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-9 px-2 hover:bg-sidebar-border"
              >
                <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-2">
                  <User className="w-3 h-3 text-blue-600" />
                </div>
                <span className="text-sm font-medium max-w-24 truncate">
                  {user?.first_name || user?.username || 'User'}
                </span>
                <ChevronDown className="w-3 h-3 ml-1 text-muted-foreground" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <UserProfile onClose={() => setShowUserProfile(false)} />
            </DialogContent>
          </Dialog>
        )}

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