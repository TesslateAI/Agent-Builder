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
      <div className="h-14 px-4 border-b border-sidebar-border flex items-center flex-shrink-0">
        <h2 className="text-sm font-semibold text-sidebar-foreground">Workspace</h2>
      </div>
      
      <div className="flex-grow flex flex-col px-4 pt-3 pb-4 min-h-0">
        <Tabs defaultValue="nodes" className="flex flex-col h-full">
          <TabsList className="flex w-full justify-center bg-card/50 rounded-t-lg border-x border-t border-border/50 p-2 flex-shrink-0 gap-1">
            <TabsTrigger 
              value="nodes" 
              className="py-2.5 px-1.5 transition-all duration-200 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground data-[state=inactive]:hover:bg-card text-xs font-medium rounded-md mt-0.5"
            >
              <Layers className="h-3 w-3 mr-1" />
              <span>Components</span>
            </TabsTrigger>
            <TabsTrigger 
              value="register" 
              className="py-2.5 px-1.5 transition-all duration-200 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground data-[state=inactive]:hover:bg-card text-xs font-medium rounded-md mt-0.5"
            >
              <Code2 className="h-3 w-3 mr-1" />
              <span>Add Code</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="nodes" className="flex-1 min-h-0 data-[state=inactive]:hidden -mt-px">
            <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-hidden">
              <div className="h-full overflow-y-auto">
                <NodesPanel tframexComponents={tframexComponents} isLoading={isLoading} error={error} />
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="register" className="flex-1 min-h-0 data-[state=inactive]:hidden -mt-px">
            <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-hidden">
              <div className="h-full overflow-y-auto">
                <CodeRegistrationPanel />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </aside>
  );
};

export default Sidebar;