// src/components/NodesPanel.jsx
import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"; // Use shadcn Card
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"; // Use shadcn Alert
import { Loader2, Terminal } from 'lucide-react'; // Icons

const DraggableNode = ({ type, label, description }) => {
  const onDragStart = (event, nodeType, nodeLabel) => {
    const nodeInfo = { type: nodeType, label: nodeLabel };
    event.dataTransfer.setData('application/reactflow', JSON.stringify(nodeInfo));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card
      className="mb-3 cursor-grab hover:border-primary transition-colors duration-150 ease-in-out"
      onDragStart={(event) => onDragStart(event, type, label)}
      draggable
      title={description || label} // Tooltip
    >
      <CardHeader className="p-3">
        <CardTitle className="text-sm font-semibold">{label}</CardTitle>
        {description && <CardDescription className="text-xs mt-1">{description}</CardDescription>}
      </CardHeader>
    </Card>
  );
};


const NodesPanel = ({ agentDefs, isLoading, error }) => {
    // Container div with padding is now handled in Sidebar for TabsContent
    return (
        <>
            {isLoading && (
                <div className="flex items-center justify-center text-muted-foreground py-4">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading nodes...
                </div>
            )}
            {error && (
                 <Alert variant="destructive" className="mx-1">
                    <Terminal className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}
            {!isLoading && !error && agentDefs.length === 0 && (
                <div className="text-center text-muted-foreground py-4 text-sm">No nodes available.</div>
            )}
            {!isLoading && !error && agentDefs.map((def) => (
                <DraggableNode
                key={def.id}
                type={def.id}
                label={def.name}
                description={def.description}
                />
            ))}
        </>
    );
};

export default NodesPanel;