// builder/frontend/src/components/Sidebar.jsx
import React, { useEffect } from 'react';
import NodesPanel from './NodesPanel';
import CodeRegistrationPanel from './CodeRegistrationPanel';
import TriggerPanel from './triggers/TriggerPanel';
import { useStore } from '../store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import { Box, Code2, Layers, Zap } from 'lucide-react';

const Sidebar = () => {
  const tframexComponents = useStore((state) => state.tframexComponents);
  const fetchTFrameXComponents = useStore((state) => state.fetchTFrameXComponents);
  const isLoading = useStore((state) => state.isComponentLoading);
  const error = useStore((state) => state.componentError);

  useEffect(() => {
    const hasComponents = tframexComponents.agents.length > 0 || 
                         tframexComponents.tools.length > 0 || 
                         tframexComponents.patterns.length > 0 ||
                         tframexComponents.mcp_servers?.length > 0;
    if (!hasComponents && !isLoading && !error) {
      fetchTFrameXComponents();
    }
  }, [fetchTFrameXComponents, tframexComponents, isLoading, error]);

  return (
    <TooltipProvider>
      <aside className="w-80 flex flex-col bg-sidebar border-r border-sidebar-border h-full">
        <div className="h-14 px-4 border-b border-sidebar-border flex items-center flex-shrink-0">
          <div className="flex items-center space-x-3">
            <img
              src="/Tesslate.svg"
              alt="Tesslate"
              className="h-6 w-auto"
            />
            <div>
              <h2 className="text-sm font-semibold text-sidebar-foreground leading-none">
                Tesslate Agent Builder
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Powered by TFrameX v1.1.0
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex-grow flex flex-col px-4 pt-3 pb-4 min-h-0">
          <Tabs defaultValue="nodes" className="flex flex-col h-full">
            <div className="h-full bg-card/50 rounded-lg border border-border/50 overflow-hidden flex flex-col">
              <TabsList className="grid w-full grid-cols-3 bg-transparent p-1 pb-0 flex-shrink-0 gap-1 rounded-none border-none">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <TabsTrigger 
                      value="nodes" 
                      className="h-8 px-3 transition-all duration-200 text-muted-foreground hover:text-foreground hover:bg-muted hover:shadow-md text-xs font-medium rounded-md flex items-center justify-center [&[data-state=active]]:!bg-primary [&[data-state=active]]:!text-primary-foreground [&[data-state=active]]:!shadow-lg"
                    >
                      <Layers className="h-4 w-4" />
                    </TabsTrigger>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Components</p>
                  </TooltipContent>
                </Tooltip>
                
                <Tooltip>
                  <TooltipTrigger asChild>
                    <TabsTrigger 
                      value="triggers" 
                      className="h-8 px-3 transition-all duration-200 text-muted-foreground hover:text-foreground hover:bg-muted hover:shadow-md text-xs font-medium rounded-md flex items-center justify-center [&[data-state=active]]:!bg-warning [&[data-state=active]]:!text-white [&[data-state=active]]:!shadow-lg"
                    >
                      <Zap className="h-4 w-4" />
                    </TabsTrigger>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Triggers</p>
                  </TooltipContent>
                </Tooltip>
                
                <Tooltip>
                  <TooltipTrigger asChild>
                    <TabsTrigger 
                      value="register" 
                      className="h-8 px-3 transition-all duration-200 text-muted-foreground hover:text-foreground hover:bg-muted hover:shadow-md text-xs font-medium rounded-md flex items-center justify-center [&[data-state=active]]:!bg-secondary [&[data-state=active]]:!text-secondary-foreground [&[data-state=active]]:!shadow-lg"
                    >
                      <Code2 className="h-4 w-4" />
                    </TabsTrigger>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Add Code</p>
                  </TooltipContent>
                </Tooltip>
              </TabsList>

              <div className="border-t border-border/50 mx-3"></div>

              <TabsContent value="nodes" className="flex-1 min-h-0 data-[state=inactive]:hidden m-0">
                <div className="h-full overflow-y-auto p-3 pt-3">
                  <NodesPanel tframexComponents={tframexComponents} isLoading={isLoading} error={error} />
                </div>
              </TabsContent>
              
              <TabsContent value="triggers" className="flex-1 min-h-0 data-[state=inactive]:hidden m-0">
                <div className="h-full overflow-y-auto p-3 pt-3">
                  <TriggerPanel />
                </div>
              </TabsContent>
              
              <TabsContent value="register" className="flex-1 min-h-0 data-[state=inactive]:hidden m-0">
                <div className="h-full overflow-y-auto p-3 pt-3">
                  <CodeRegistrationPanel />
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </aside>
    </TooltipProvider>
  );
};

export default Sidebar;