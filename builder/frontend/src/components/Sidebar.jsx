// builder/frontend/src/components/Sidebar.jsx
import React, { useEffect } from 'react'; // Removed useState as Tabs manages its state
import NodesPanel from './NodesPanel';
import ChatbotPanel from './ChatbotPanel'; // Assuming ChatbotPanel calls sendChatMessageToFlowBuilder now
import CodeRegistrationPanel from './CodeRegistrationPanel'; // NEW
import { useStore } from '../store';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const Sidebar = () => {
  const tframexComponents = useStore((state) => state.tframexComponents);
  const fetchTFrameXComponents = useStore((state) => state.fetchTFrameXComponents);
  const isLoading = useStore((state) => state.isComponentLoading);
  const error = useStore((state) => state.componentError);

  useEffect(() => {
    // Fetch if no components are loaded and not currently loading/error
    const hasComponents = tframexComponents.agents.length > 0 || tframexComponents.tools.length > 0 || tframexComponents.patterns.length > 0;
    if (!hasComponents && !isLoading && !error) {
      fetchTFrameXComponents();
    }
  }, [fetchTFrameXComponents, tframexComponents, isLoading, error]);

  return (
    <aside className="w-80 flex flex-col bg-card border-r border-border h-full"> {/* Slightly wider */}
      <Tabs defaultValue="nodes" className="flex flex-col flex-grow h-full">
        <TabsList className="grid w-full grid-cols-3 rounded-none border-b border-border"> {/* 3 tabs */}
          <TabsTrigger value="nodes" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
            Components
          </TabsTrigger>
          <TabsTrigger value="chatbot" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
            AI Flow Builder
          </TabsTrigger>
          <TabsTrigger value="register" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
            Add Code
          </TabsTrigger>
        </TabsList>

        <TabsContent value="nodes" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
          <div className="h-full overflow-y-auto p-3">
            <NodesPanel tframexComponents={tframexComponents} isLoading={isLoading} error={error} />
          </div>
        </TabsContent>
        <TabsContent value="chatbot" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
          <ChatbotPanel /> 
        </TabsContent>
         <TabsContent value="register" className="flex-grow overflow-hidden mt-0 data-[state=inactive]:hidden">
            <div className="h-full overflow-y-auto p-3">
                <CodeRegistrationPanel />
            </div>
        </TabsContent>
      </Tabs>
    </aside>
  );
};

export default Sidebar;