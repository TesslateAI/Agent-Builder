// src/components/Sidebar.jsx
import React, { useState, useEffect } from 'react';
import NodesPanel from './NodesPanel';
import ChatbotPanel from './ChatbotPanel';
import { useStore } from '../store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"; // Use shadcn Tabs

const Sidebar = () => {
  // Shadcn Tabs manages its own active state via the defaultValue/value prop
  const agentDefinitions = useStore((state) => state.agentDefinitions);
  const fetchAgentDefinitions = useStore((state) => state.fetchAgentDefinitions);
  const isLoading = useStore((state) => state.isDefinitionLoading);
  const error = useStore((state) => state.definitionError);

  useEffect(() => {
      if (agentDefinitions.length === 0 && !isLoading && !error) {
          fetchAgentDefinitions();
      }
  }, [fetchAgentDefinitions, agentDefinitions.length, isLoading, error]);

  return (
    // Use background defined by shadcn's card or background
    <aside className="w-72 flex flex-col bg-card border-r border-border h-full">
      <Tabs defaultValue="nodes" className="flex flex-col flex-grow h-full">
        {/* Tabs Header */}
        <TabsList className="grid w-full grid-cols-2 rounded-none border-b border-border">
          <TabsTrigger value="nodes" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
             Nodes
          </TabsTrigger>
          <TabsTrigger value="chatbot" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
             Chatbot
          </TabsTrigger>
        </TabsList>

        {/* Content Area */}
        <TabsContent value="nodes" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
            {/* NodesPanel content needs padding */}
            <div className="h-full overflow-y-auto p-3">
                <NodesPanel agentDefs={agentDefinitions} isLoading={isLoading} error={error} />
            </div>
        </TabsContent>
        <TabsContent value="chatbot" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
           {/* ChatbotPanel already has internal padding */}
           <ChatbotPanel />
        </TabsContent>
      </Tabs>
    </aside>
  );
};

export default Sidebar;