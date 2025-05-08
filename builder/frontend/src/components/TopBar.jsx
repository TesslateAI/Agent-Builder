// src/components/TopBar.jsx
import React, { useState, useCallback } from 'react';
import { useStore } from '../store';
import { Button } from '@/components/ui/button'; // Use shadcn Button
import { Input } from '@/components/ui/input'; // Use shadcn Input
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"; // Use shadcn Select
import { Save, Play, Trash2, PlusCircle } from 'lucide-react'; // Icons

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

  const handleCreateProject = useCallback(() => {
    createProject(newProjectName.trim() || undefined); // Pass undefined for default name
    setNewProjectName('');
  }, [createProject, newProjectName]);

  const handleProjectChange = (value) => {
    // Shadcn Select's onValueChange provides the value directly
    if (value) {
      loadProject(value);
    }
  };

   const handleDeleteClick = () => {
        if (currentProjectId) {
            // Optional: Add a confirmation dialog here
            deleteProject(currentProjectId);
        }
    };

  return (
    <div className="h-16 bg-card border-b border-border flex items-center justify-between px-4 shadow-sm flex-shrink-0">
      {/* Left Side: Logo & Project Controls */}
      <div className="flex items-center space-x-4">
         {/* Logo and Title Group */}
         <div className="flex items-center flex-shrink-0"> {/* Grouping element */}
             <img
                src="/Tesslate.svg" // Path relative to public folder
                alt="Tesslate Logo"
                className="h-6 w-auto mr-2" // Adjust height as needed, add margin between logo and text
             />
             <span className="text-lg font-semibold text-foreground whitespace-nowrap">
                Tesslate Studio
             </span>
         </div>

        {/* Project Selector */}
        <Select
            value={currentProjectId || ''}
            onValueChange={handleProjectChange}
            disabled={isRunning}
        >
            <SelectTrigger className="w-[180px] text-sm">
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

         {/* Create New Project */}
        <div className="flex items-center space-x-2">
            <Input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="New Project Name..."
                className="w-40 h-9 text-sm" // Adjusted height and width
                disabled={isRunning}
            />
            <Button
                onClick={handleCreateProject}
                variant="secondary"
                size="sm" // Smaller button
                disabled={isRunning}
                title="Create New Project"
            >
                <PlusCircle className="h-4 w-4 mr-1" /> Create
            </Button>
            <Button
                onClick={handleDeleteClick}
                variant="destructive"
                size="icon" // Icon button
                title="Delete Current Project"
                disabled={isRunning || !currentProjectId || Object.keys(projects).length <= 1}
            >
               <Trash2 className="h-4 w-4" />
               <span className="sr-only">Delete Project</span> {/* Keep for accessibility */}
            </Button>
        </div>
      </div>

      {/* Right Side: Action Buttons */}
      <div className="flex items-center space-x-3">
         <Button
            onClick={saveCurrentProject}
            variant="outline"
            size="sm"
            disabled={isRunning}
        >
            <Save className="h-4 w-4 mr-2" /> Save Project
        </Button>
        <Button
          onClick={runFlow}
          size="sm"
          disabled={isRunning}
          className={`font-semibold transition-colors duration-150 ease-in-out ${
            isRunning ? 'bg-muted text-muted-foreground cursor-not-allowed' : 'bg-primary text-primary-foreground hover:bg-primary/90'
          }`}
        >
          {isRunning ? (
             <>
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></span>
                Running...
             </>
          ) : (
             <>
                <Play className="h-4 w-4 mr-2 fill-current" /> Run Flow
             </>
          )}
        </Button>
      </div>
    </div>
  );
};

export default TopBar;