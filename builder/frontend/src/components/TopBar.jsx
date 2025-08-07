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
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Save, Play, Trash2, Plus, FolderOpen, Code, Settings, Database, Check, User, ChevronDown, Download, Upload, X } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import ModelConfigurationPanel from './ModelConfigurationPanel';
import UserProfile from './auth/UserProfile';
import ExportDialog from './ExportDialog';
import ImportDialog from './ImportDialog';

// Reusable tooltip button component
const TooltipButton = ({ tooltip, children, ...props }) => (
  <Tooltip>
    <TooltipTrigger asChild>
      <Button {...props}>
        {children}
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      <p>{tooltip}</p>
    </TooltipContent>
  </Tooltip>
);

const TopBar = () => {
  const projects = useStore((state) => state.projects);
  const currentProjectId = useStore((state) => state.currentProjectId);
  const loadProject = useStore((state) => state.loadProject);
  const createProject = useStore((state) => state.createProject);
  const deleteProject = useStore((state) => state.deleteProject);
  const saveCurrentProject = useStore((state) => state.saveCurrentProject);
  const runFlow = useStore((state) => state.runFlow);
  const isRunning = useStore((state) => state.isRunning);
  
  // Auto-save state
  const autoSaveStatus = useStore((state) => state.autoSaveStatus);
  const lastSaveTime = useStore((state) => state.lastSaveTime);

  // Auth state
  const { user, isAuthenticated } = useAuth();

  const [newProjectName, setNewProjectName] = useState('');
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle', 'saving', 'saved'
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, projectId: null, projectName: '' });

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

  const handleDeleteClick = (e, projectId, projectName) => {
    e.stopPropagation(); // Prevent select from triggering
    setDeleteConfirm({ show: true, projectId, projectName });
  };

  const confirmDelete = () => {
    if (deleteConfirm.projectId) {
      deleteProject(deleteConfirm.projectId);
      setDeleteConfirm({ show: false, projectId: null, projectName: '' });
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm({ show: false, projectId: null, projectName: '' });
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
    <TooltipProvider>
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
                <div className="w-6 h-6 bg-muted rounded-full flex items-center justify-center mr-2">
                  <User className="w-3 h-3 text-muted-foreground" />
                </div>
                <span className="text-sm font-medium max-w-24 truncate">
                  {user?.first_name || user?.username || 'User'}
                </span>
                <ChevronDown className="w-3 h-3 ml-1 text-muted-foreground" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
              <UserProfile onClose={() => setShowUserProfile(false)} />
            </DialogContent>
          </Dialog>
        )}

        {/* Project Controls */}
        <div className="flex items-center space-x-2">
          {/* Auto-save Status */}
          <div className="flex items-center justify-center w-4 h-4 mr-1">
            {autoSaveStatus === 'saving' && (
              <div className="h-3 w-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
            {autoSaveStatus === 'saved' && (
              <Check className="h-3 w-3 text-success" />
            )}
          </div>
          <Select
            value={currentProjectId || ''}
            onValueChange={handleProjectChange}
            disabled={isRunning}
          >
            <SelectTrigger className="w-[200px] h-9 focus:ring-0">
              <FolderOpen className="h-4 w-4 mr-2 text-muted-foreground" />
              <SelectValue placeholder="Select Project" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(projects).map(([id, project]) => {
                const isDeletable = Object.keys(projects).length > 1;
                const isCurrentProject = id === currentProjectId;
                return (
                  <SelectItem key={id} value={id} className="hover:bg-sidebar-border focus:bg-sidebar-border pr-12">
                    <div className="flex items-center justify-between w-full group">
                      <span className="flex-1 min-w-0 truncate">
                        {project.name}
                      </span>
                      {isDeletable && (
                        <Button
                          onMouseDown={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleDeleteClick(e, id, project.name);
                          }}
                          variant="ghost"
                          size="sm"
                          className="absolute right-2 z-10 h-6 w-6 p-0 text-muted-foreground hover:bg-destructive/20 hover:text-destructive rounded shrink-0"
                          title="Delete project"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>

          <div className="flex items-center">
            <Input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateProject()}
              placeholder="New project..."
              className="w-32 h-9 rounded-r-none border-r-0 focus:ring-0 focus:ring-offset-0 focus-visible:ring-0 focus-visible:ring-offset-0"
              disabled={isRunning}
            />
            <TooltipButton
              tooltip="Add new project"
              onClick={handleCreateProject}
              variant="secondary"
              size="sm"
              className="rounded-l-none h-9"
              disabled={isRunning || !newProjectName.trim()}
            >
              <Plus className="h-4 w-4" />
            </TooltipButton>
          </div>
        </div>
      </div>

      {/* Right Side: Action Buttons */}
      <div className="flex items-center space-x-2">
        <ModelConfigurationPanel />
        
        <ImportDialog />
        <ExportDialog />

        <TooltipButton
          tooltip={saveStatus === 'saved' ? 'Project saved!' : saveStatus === 'saving' ? 'Saving project...' : 'Save project'}
          onClick={handleSaveClick}
          variant="ghost"
          size="icon"
          className={`h-9 w-9 transition-colors ${
            saveStatus === 'saved' 
              ? 'bg-success/20 text-success hover:bg-success/20' 
              : ''
          }`}
          disabled={isRunning || saveStatus === 'saving'}
        >
          {saveStatus === 'saved' ? (
            <Check className="h-4 w-4" />
          ) : (
            <Save className="h-4 w-4" />
          )}
        </TooltipButton>

        <TooltipButton
          tooltip={isRunning ? 'Flow is running...' : 'Run the current flow'}
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
        </TooltipButton>

      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm.show} onOpenChange={(open) => !open && cancelDelete()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-destructive" />
              Delete Project
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteConfirm.projectName}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={cancelDelete}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </TooltipProvider>
  );
};

export default TopBar;