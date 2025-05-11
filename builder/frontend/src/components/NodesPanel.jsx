// frontend/src/components/NodesPanel.jsx
// builder/frontend/src/components/NodesPanel.jsx
import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, Terminal, Zap, Cog, Puzzle, Wrench, TextIcon } from 'lucide-react'; // Added TextIcon

const DraggableNodeItem = ({ component }) => {
  const onDragStart = (event, componentData) => {
    event.dataTransfer.setData('application/tframex_component', JSON.stringify(componentData));
    event.dataTransfer.effectAllowed = 'move';
  };

  let Icon = Zap; // Default
  if (component.component_category === 'agent') Icon = Cog;
  else if (component.component_category === 'pattern') Icon = Puzzle;
  else if (component.component_category === 'tool') Icon = Wrench;
  else if (component.component_category === 'utility' && component.id === 'textInput') Icon = TextIcon;


  return (
    <Card
      className="mb-3 cursor-grab hover:border-primary transition-colors duration-150 ease-in-out active:shadow-lg active:border-primary"
      onDragStart={(event) => onDragStart(event, component)}
      draggable
      title={component.description || component.name}
    >
      <CardHeader className="p-3 flex flex-row items-center space-x-2">
        <Icon className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div>
            <CardTitle className="text-sm font-semibold">{component.name}</CardTitle>
            {component.description && <CardDescription className="text-xs mt-0.5 line-clamp-2">{component.description}</CardDescription>}
        </div>
      </CardHeader>
    </Card>
  );
};

const NodesPanel = ({ tframexComponents, isLoading, error }) => {
  const { agents = [], tools = [], patterns = [], utility = [] } = tframexComponents || {};

  return (
    <>
      {isLoading && (
        <div className="flex items-center justify-center text-muted-foreground py-4">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading TFrameX Components...
        </div>
      )}
      {error && (
        <Alert variant="destructive" className="mx-1">
          <Terminal className="h-4 w-4" /> <AlertTitle>Error Loading Components</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {!isLoading && !error && (agents.length === 0 && tools.length === 0 && patterns.length === 0 && utility.length === 0) && (
        <div className="text-center text-muted-foreground py-4 text-sm">No TFrameX components found or registered.</div>
      )}

      {!isLoading && !error && (
        <>
          {utility.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold uppercase text-muted-foreground px-1 mb-2">Utility</h3>
              {utility.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
            </div>
          )}
          {agents.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold uppercase text-muted-foreground px-1 mb-2">Agents</h3>
              {agents.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
            </div>
          )}
          {patterns.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold uppercase text-muted-foreground px-1 mb-2">Patterns</h3>
              {patterns.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
            </div>
          )}
          {tools.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold uppercase text-muted-foreground px-1 mb-2">Tools</h3>
              {tools.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
            </div>
          )}
        </>
      )}
    </>
  );
};

export default NodesPanel;