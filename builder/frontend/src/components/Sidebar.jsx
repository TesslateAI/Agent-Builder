// builder/frontend/src/components/Sidebar.jsx
import React, { useEffect } from 'react';
import NodesPanel from './NodesPanel';
import CodeRegistrationPanel from './CodeRegistrationPanel';
import { useStore } from '../store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Box, Code2, Layers } from 'lucide-react';

const Sidebar = () => {
  const tframexComponents = useStore((state) => state.tframexComponents);
  const fetchTFrameXComponents = useStore((state) => state.fetchTFrameXComponents);
  const isLoading = useStore((state) => state.isComponentLoading);
  const error = useStore((state) => state.componentError);

  useEffect(() => {
    const hasComponents = tframexComponents.agents.length > 0 || 
                         tframexComponents.tools.length > 0 || 
                         tframexComponents.patterns.length > 0;
    if (!hasComponents && !isLoading && !error) {
      fetchTFrameXComponents();
    }
  }, [fetchTFrameXComponents, tframexComponents, isLoading, error]);

  return (
    <aside className="w-80 flex flex-col bg-sidebar border-r border-sidebar-border h-full">
      <Tabs defaultValue="nodes" className="flex flex-col flex-grow h-full">
        <div className="px-4 py-3 border-b border-sidebar-border">
          <h2 className="text-sm font-semibold text-sidebar-foreground">Workspace</h2>
        </div>
        
        <TabsList className="grid w-full grid-cols-2 bg-transparent border-b border-sidebar-border rounded-none p-0 h-auto">
          <TabsTrigger 
            value="nodes" 
            className="rounded-none py-2.5 data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=inactive]:text-muted-foreground"
          >
            <Layers className="h-4 w-4 mr-2" />
            Components
          </TabsTrigger>
          <TabsTrigger 
            value="register" 
            className="rounded-none py-2.5 data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none data-[state=inactive]:text-muted-foreground"
          >
            <Code2 className="h-4 w-4 mr-2" />
            Register Code
          </TabsTrigger>
        </TabsList>

        <TabsContent value="nodes" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
          <div className="h-full overflow-y-auto">
            <NodesPanel tframexComponents={tframexComponents} isLoading={isLoading} error={error} />
          </div>
        </TabsContent>
        
        <TabsContent value="register" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
          <div className="h-full overflow-y-auto">
            <CodeRegistrationPanel />
          </div>
        </TabsContent>
      </Tabs>
    </aside>
  );
};

export default Sidebar;