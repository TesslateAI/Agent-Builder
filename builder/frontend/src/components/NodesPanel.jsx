// frontend/src/components/NodesPanel.jsx
// builder/frontend/src/components/NodesPanel.jsx
import React from 'react';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Loader2, Terminal, Zap, Cog, Puzzle, Wrench, TextIcon, Server, Webhook, Clock, Mail, FolderOpen } from 'lucide-react';

const DraggableNodeItem = ({ component }) => {
  const onDragStart = (event, componentData) => {
    event.dataTransfer.setData('application/tframex_component', JSON.stringify(componentData));
    event.dataTransfer.effectAllowed = 'move';
  };

  let Icon = Zap; // Default
  let categoryColor = 'text-muted-foreground';
  
  if (component.component_category === 'agent') {
    Icon = Cog;
    categoryColor = 'text-primary';
  } else if (component.component_category === 'pattern') {
    Icon = Puzzle;
    categoryColor = 'text-secondary';
  } else if (component.component_category === 'tool') {
    Icon = Wrench;
    categoryColor = 'text-accent';
  } else if (component.component_category === 'utility' && component.id === 'textInput') {
    Icon = TextIcon;
    categoryColor = 'text-info';
  } else if (component.component_category === 'mcp_server') {
    Icon = Server;
    categoryColor = 'text-success';
  } else if (component.component_category === 'triggers') {
    categoryColor = 'text-warning';
    if (component.id === 'webhookTrigger') Icon = Webhook;
    else if (component.id === 'emailTrigger') Icon = Mail;
    else if (component.id === 'scheduleTrigger') Icon = Clock;
    else if (component.id === 'fileTrigger') Icon = FolderOpen;
    else Icon = Zap;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className="group relative flex items-center gap-3 p-3 rounded-lg border border-border/30 bg-card/20 cursor-grab hover:bg-card/40 hover:border-primary/50 hover:shadow-md transition-all duration-200 ease-in-out active:scale-[0.98] active:shadow-lg mb-2"
          onDragStart={(event) => onDragStart(event, component)}
          draggable
        >
          <div className={`flex items-center justify-center w-8 h-8 rounded-md bg-surface/60 group-hover:bg-surface/80 transition-colors ${categoryColor}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
              {component.name}
            </h4>
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-1 h-6 bg-primary/40 rounded-full" />
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs">
        <div className="space-y-1">
          <p className="font-medium">{component.name}</p>
          {component.description && (
            <p className="text-xs text-muted-foreground">{component.description}</p>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
};

const NodesPanel = ({ tframexComponents, isLoading, error }) => {
  const { agents = [], tools = [], patterns = [], utility = [], mcp_servers = [], triggers = [] } = tframexComponents || {};

  return (
    <div className="p-4">
      {isLoading && (
        <div className="flex items-center justify-center text-muted-foreground py-4">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading TFrameX Components...
        </div>
      )}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <Terminal className="h-4 w-4" /> <AlertTitle>Error Loading Components</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {!isLoading && !error && (agents.length === 0 && tools.length === 0 && patterns.length === 0 && utility.length === 0 && mcp_servers.length === 0 && triggers.length === 0) && (
        <div className="text-center text-muted-foreground py-4 text-sm">No TFrameX components found or registered.</div>
      )}

      {!isLoading && !error && (
        <div className="space-y-6">
          {utility.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-info" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">Utility</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {utility.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
              </div>
            </div>
          )}
          {agents.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-primary" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">Agents</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {agents
                  .sort((a, b) => {
                    const moveToBottom = ['ConversationalAssistant', 'FlowBuilderAgent', 'OrchestratorAgent'];
                    const aIsBottom = moveToBottom.includes(a.id);
                    const bIsBottom = moveToBottom.includes(b.id);
                    if (aIsBottom && !bIsBottom) return 1;
                    if (!aIsBottom && bIsBottom) return -1;
                    return 0;
                  })
                  .map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)
                }
              </div>
            </div>
          )}
          {patterns.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-secondary" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">Patterns</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {patterns.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
              </div>
            </div>
          )}
          {tools.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-accent" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">Tools</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {tools.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
              </div>
            </div>
          )}
          {triggers.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-warning" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">Triggers</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {triggers.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
              </div>
            </div>
          )}
          {mcp_servers.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-success" />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/80">MCP Servers</h3>
                <div className="flex-1 h-px bg-border/50" />
              </div>
              <div className="space-y-1">
                {mcp_servers.map((comp) => <DraggableNodeItem key={comp.id} component={comp} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NodesPanel;