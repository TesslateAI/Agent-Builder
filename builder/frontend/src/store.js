// frontend/src/store.js
import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from 'reactflow';
import { nanoid } from 'nanoid';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001/api/tframex';

const loadState = (key) => {
  try {
    const serializedState = localStorage.getItem(key);
    if (serializedState === null) return undefined;
    return JSON.parse(serializedState);
  } catch (err) {
    console.error("Could not load state from localStorage", err);
    return undefined;
  }
};

const saveState = (key, state) => {
  try {
    const serializedState = JSON.stringify(state);
    localStorage.setItem(key, serializedState);
  } catch (err) {
    console.error("Could not save state to localStorage", err);
  }
};

const initialDefaultProjectNodes = [];
const initialProjects = {
  'default_project': {
    name: "My TFrameX Flow",
    nodes: [...initialDefaultProjectNodes],
    edges: [],
  },
};

const savedProjects = loadState('tframexStudioProjects') || initialProjects;
const initialProjectId = loadState('tframexStudioCurrentProject') || 'default_project';

export const useStore = create((set, get) => ({
  // === React Flow State ===
  nodes: savedProjects[initialProjectId]?.nodes || [...initialDefaultProjectNodes],
  edges: savedProjects[initialProjectId]?.edges || [],
  selectedNodeId: null, // For properties panel
  isPropertiesPanelOpen: false, // For properties panel

  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId, isPropertiesPanelOpen: !!nodeId }),
  togglePropertiesPanel: (isOpen) => set(state => ({ 
    isPropertiesPanelOpen: isOpen === undefined ? !state.isPropertiesPanelOpen : isOpen 
  })),
  
  onNodesChange: (changes) => set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) })),
  onEdgesChange: (changes) => set((state) => ({ edges: applyEdgeChanges(changes, state.edges) })),
  
  onConnect: (connection) => {
    const nodes = get().nodes;
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);

    // --- CONNECTION TYPE 1: Agent to Pattern's general config input ---
    if (targetNode?.data?.component_category === 'pattern' && 
        sourceNode?.data?.component_category === 'agent' &&
        connection.targetHandle?.startsWith('pattern_agent_input_')
      ) {
      
      const paramName = connection.targetHandle.substring('pattern_agent_input_'.length);
      // Use the agent's TFrameX ID if available, otherwise its ReactFlow node ID as a fallback reference
      const agentIdToAssign = sourceNode.data.tframex_component_id || sourceNode.id;

      get().updateNodeData(targetNode.id, { [paramName]: agentIdToAssign });
      
      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          style: { ...connection.style, stroke: '#F59E0B', strokeWidth: 2.5, zIndex: 0 },
          animated: false,
          data: { ...connection.data, connectionType: 'agentInstanceToPatternParam' }
        }, state.edges),
      }));
      return;
    }

    // --- CONNECTION TYPE 2: Agent to Pattern's list item slot ---
    if (targetNode?.data?.component_category === 'pattern' &&
        sourceNode?.data?.component_category === 'agent' &&
        connection.targetHandle?.startsWith('pattern_list_item_input_')
      ) {
      
      const parts = connection.targetHandle.split('_'); // e.g. pattern_list_item_input_steps_0
      const paramName = parts[4]; 
      const index = parseInt(parts[5], 10);
      const agentIdToAssign = sourceNode.data.tframex_component_id || sourceNode.id;

      const currentList = Array.isArray(targetNode.data[paramName]) ? [...targetNode.data[paramName]] : [];
      while (currentList.length <= index) {
        currentList.push(null);
      }

      if (index >= 0 && index < currentList.length) {
        currentList[index] = agentIdToAssign;
        get().updateNodeData(targetNode.id, { [paramName]: currentList });

        set((state) => ({
          edges: addEdge({
            ...connection,
            type: 'smoothstep',
            style: { ...connection.style, stroke: '#4CAF50', strokeWidth: 2, zIndex: 0 },
            animated: false,
            data: { ...connection.data, connectionType: 'agentToPatternListItem' }
          }, state.edges),
        }));
      } else {
        console.warn("Invalid index for pattern list item connection:", paramName, index, currentList.length);
      }
      return;
    }

    // --- CONNECTION TYPE 3: Tool's "attachment" handle to Agent's "tool input" handle ---
    if (sourceNode?.data?.component_category === 'tool' && 
        targetNode?.data?.component_category === 'agent' &&
        connection.sourceHandle === 'tool_attachment_out' &&
        connection.targetHandle === 'tool_input_handle'
      ) {
      
      const toolId = sourceNode.data.tframex_component_id || sourceNode.id;
      const currentSelectedTools = targetNode.data.selected_tools || [];
      
      if (!currentSelectedTools.includes(toolId)) {
        get().updateNodeData(targetNode.id, {
          selected_tools: [...currentSelectedTools, toolId]
        });
        console.log(`UI: Tool '${toolId}' enabled on Agent '${targetNode.data.label || targetNode.id}' via connection.`);
      }
      
      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#a5b4fc', strokeDasharray: '5 5', strokeWidth: 1.5, zIndex: 0 }, 
          data: { ...connection.data, connectionType: 'toolAttachment' }
        }, state.edges),
      }));
      return;
    }

    // --- CONNECTION TYPE 4: Tool's "data output" handle to an Agent's "message input" handle ---
    // This also implies enabling the tool.
    if (sourceNode?.data?.component_category === 'tool' &&
        connection.sourceHandle === 'tool_output_data' &&
        targetNode?.data?.component_category === 'agent' &&
        connection.targetHandle === 'input_message_in'
      ) {
        
        const toolId = sourceNode.data.tframex_component_id || sourceNode.id;
        const currentSelectedTools = targetNode.data.selected_tools || [];
        if (!currentSelectedTools.includes(toolId)) {
            get().updateNodeData(targetNode.id, {
                selected_tools: [...currentSelectedTools, toolId]
            });
            console.log(`UI: Tool '${toolId}' implicitly enabled on Agent '${targetNode.data.label || targetNode.id}' due to data connection.`);
        }
        set((state) => ({
            edges: addEdge({ 
                ...connection, 
                type: 'smoothstep', 
                animated: true, 
                style: { strokeWidth: 2, stroke: '#7c3aed' }, 
                data: {...connection.data, connectionType: 'toolDataOutputToAgent'} 
            }, state.edges),
        }));
        return;
    }
     // --- CONNECTION TYPE 5: TextInputNode's output to an Agent's "message input" handle ---
    if (sourceNode?.type === 'textInput' && // Check type for TextInputNode
        targetNode?.data?.component_category === 'agent' &&
        connection.targetHandle === 'input_message_in'
      ) {
        // This is a standard data flow, but we can style it if needed
        // The content from TextInputNode (data.text_content) will be naturally
        // part of the message payload if TFrameX handles inputs generically.
        // No special data update on the agent node is needed here, beyond the edge itself.
        set((state) => ({
            edges: addEdge({
                ...connection,
                type: 'smoothstep',
                animated: true,
                style: { strokeWidth: 2, stroke: '#0ea5e9' }, // Cyan for text input
                data: {...connection.data, connectionType: 'textInputToAgent'}
            }, state.edges),
        }));
        return;
    }
    
    // --- DEFAULT: Standard data flow edge ---
    set((state) => ({
      edges: addEdge({ 
          ...connection, 
          type: 'smoothstep', 
          animated: true, 
          style: { strokeWidth: 2 } 
        }, state.edges),
    }));
  },

  addNode: (nodeDataFromDrop, position) => {
    const { component_category, id: componentId, name: componentName, tframex_agent_type, config_options, constructor_params_schema } = nodeDataFromDrop;
    
    let defaultNodeData = { 
      label: componentName || componentId,
      component_category: component_category, // Store this if it's coming from drop
      tframex_component_id: componentId, // Store the original TFrameX ID
    };

    let nodeType = componentId; // Default to componentId as node type

    if (component_category === 'agent') {
      defaultNodeData = {
        ...defaultNodeData,
        selected_tools: config_options?.default_tools || [], 
        template_vars_config: {}, 
        system_prompt_override: "", // Initialize for properties panel
        tframex_agent_type: tframex_agent_type,
        can_use_tools: config_options?.can_use_tools || false,
        strip_think_tags_override: config_options?.strip_think_tags, // Use original default
      };
      // nodeType is already componentId, which is correct for agents
    } else if (component_category === 'pattern') {
      const patternParams = {};
      const listAgentParams = ['participant_agent_names', 'tasks', 'steps'];
      if (constructor_params_schema) {
        for (const paramName in constructor_params_schema) {
          const paramInfo = constructor_params_schema[paramName];
          // Initialize based on type hints for better UI experience in PatternNode
          if (listAgentParams.includes(paramName) && paramInfo.type_hint?.toLowerCase().includes('list')) {
            patternParams[paramName] = []; 
          } else if (paramInfo.type_hint?.toLowerCase().includes('agent') || paramName.startsWith('agent_') || paramName.endsWith('_agent_name')) {
            patternParams[paramName] = null; 
          } else if (paramName === 'routes' && paramInfo.type_hint?.toLowerCase().includes('dict')) {
            patternParams[paramName] = {}; // Initialize routes as an empty object
          } else if (paramInfo.type_hint?.toLowerCase().includes('list')) {
            patternParams[paramName] = [];
          } else if (paramInfo.type_hint?.toLowerCase().includes('dict')) {
             patternParams[paramName] = {};
          } else if (paramInfo.type_hint?.toLowerCase().includes('int') || paramInfo.type_hint?.toLowerCase().includes('float')) {
             patternParams[paramName] = paramInfo.default !== "REQUIRED" && paramInfo.default !== undefined ? parseFloat(paramInfo.default) || null : null;
          } else if (paramInfo.type_hint?.toLowerCase().includes('bool')) {
             patternParams[paramName] = paramInfo.default !== "REQUIRED" && paramInfo.default !== undefined ? (String(paramInfo.default).toLowerCase() === 'true') : false;
          } else { // Default to string or use actual default
             patternParams[paramName] = paramInfo.default !== "REQUIRED" && paramInfo.default !== undefined ? String(paramInfo.default) : '';
          }
        }
      }
      defaultNodeData = { ...defaultNodeData, ...patternParams };
      // nodeType is componentId (Pattern class name)
    } else if (component_category === 'tool') {
        defaultNodeData.is_tool_node = true; // Mark as tool
        defaultNodeData.has_data_output = nodeDataFromDrop.config_options?.has_data_output || 
                                          (nodeDataFromDrop.parameters_schema && Object.keys(nodeDataFromDrop.parameters_schema).length > 0 && nodeDataFromDrop.description?.toLowerCase().includes("return"));
      // nodeType is componentId (Tool name)
    } else if (component_category === 'utility' && componentId === 'textInput') { // For TextInputNode
        nodeType = 'textInput'; // Specific type for ReactFlow
        defaultNodeData = {
            label: "Text Input",
            text_content: "Enter your prompt or text here...",
            component_category: 'utility', // Mark for properties panel or filtering
        };
    }


    const newNode = {
      id: `${nodeType}-${nanoid(6)}`, // Use nodeType for ID prefix
      type: nodeType, // This MUST match a key in ReactFlow's nodeTypes
      position,
      data: defaultNodeData,
    };
    set((state) => ({ nodes: [...state.nodes, newNode] }));
  },

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  updateNodeData: (nodeId, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
      ),
    }));
  },

  // === Project Management State ===
  projects: savedProjects,
  currentProjectId: initialProjectId,
  
  saveCurrentProject: () => {
    const { nodes, edges, currentProjectId, projects } = get();
    const currentProject = projects[currentProjectId];
    if (currentProject) {
        const updatedProjects = {
            ...projects,
            [currentProjectId]: { ...currentProject, nodes, edges }
        };
        set({ projects: updatedProjects });
        console.log(`Project '${currentProject.name}' saved.`);
    }
  },

  loadProject: (projectId) => {
    const { projects, saveCurrentProject } = get();
    const projectToLoad = projects[projectId];

    if (projectToLoad) {
      saveCurrentProject(); 
      set({
        nodes: projectToLoad.nodes || [...initialDefaultProjectNodes],
        edges: projectToLoad.edges || [],
        currentProjectId: projectId,
        output: "Output will appear here...", 
        chatHistory: [], 
        selectedNodeId: null, // Reset selection
        isPropertiesPanelOpen: false,
      });
      console.log(`Project '${projectToLoad.name}' loaded.`);
    } else {
        console.warn(`Project with ID ${projectId} not found.`);
    }
  },

  createProject: (name) => {
    const { projects, saveCurrentProject } = get();
    saveCurrentProject(); 

    const newProjectId = `project_${nanoid(8)}`;
    const newProject = {
        name: name || `New TFrameX Project ${Object.keys(projects).length + 1}`,
        nodes: [...initialDefaultProjectNodes], 
        edges: []
    };
    const updatedProjects = { ...projects, [newProjectId]: newProject };
    set({
        projects: updatedProjects,
        nodes: [...initialDefaultProjectNodes],
        edges: [],
        currentProjectId: newProjectId,
        output: "Output will appear here...",
        chatHistory: [],
        selectedNodeId: null,
        isPropertiesPanelOpen: false,
    });
    console.log(`Project '${newProject.name}' created.`);
  },

  deleteProject: (projectId) => {
      const { projects, currentProjectId, loadProject } = get();
      if (!projects[projectId]) return;
      if (Object.keys(projects).length <= 1) {
          alert("Cannot delete the last project.");
          return;
      }
       if (!confirm(`Are you sure you want to delete project "${projects[projectId].name}"? This cannot be undone.`)) {
           return;
       }

      const updatedProjects = { ...projects };
      delete updatedProjects[projectId];

      let nextProjectId = currentProjectId;
      if (currentProjectId === projectId) {
          nextProjectId = Object.keys(updatedProjects)[0];
      }

      set({ projects: updatedProjects });

       if (currentProjectId === projectId) {
           loadProject(nextProjectId); 
       }
      console.log(`Project "${projects[projectId].name}" deleted.`);
  },

  // === Execution State ===
  output: "Output will appear here...",
  isRunning: false,
  runFlow: async () => {
    const { nodes, edges, saveCurrentProject } = get();
    saveCurrentProject(); 

    set({ isRunning: true, output: "Executing TFrameX flow..." });
    console.log("Sending to TFrameX backend:", { nodes, edges });

    // Find the first TextInputNode if it exists and is connected to an agent
    let initialInputContent = "User input from Studio to start the flow."; // Default
    const textInputNode = nodes.find(n => n.type === 'textInput');
    if (textInputNode) {
        const isConnectedAsStart = edges.some(edge => 
            edge.source === textInputNode.id &&
            nodes.find(n => n.id === edge.target)?.data.component_category === 'agent' &&
            !edges.some(e => e.target === textInputNode.id) // Ensure TextInputNode itself has no inputs
        );
        if (isConnectedAsStart) {
            initialInputContent = textInputNode.data.text_content || initialInputContent;
        }
    }


    const payload = {
        nodes,
        edges,
        initial_input: initialInputContent,
        global_flow_template_vars: { "studio_user": "VisualBuilder" } 
    };

    try {
      const response = await axios.post(`${API_BASE_URL}/flow/execute`, payload);
      console.log("Received from TFrameX backend:", response.data);
      set({ output: response.data.output || "Execution finished, but no output from TFrameX backend." });
    } catch (error) {
      console.error("Error running TFrameX flow:", error);
      let errorMessage = "Failed to run TFrameX flow.";
      if (error.response) {
        console.error("TFrameX Backend Error Data:", error.response.data);
        console.error("TFrameX Backend Error Status:", error.response.status);
        errorMessage = `TFrameX Backend Error (${error.response.status}): ${error.response.data?.error || 'Unknown error'}\n\nOutput Log:\n${error.response.data?.output || ''}`;
      } else if (error.request) {
        console.error("No response received:", error.request);
        errorMessage = "Network Error: Could not connect to the TFrameX backend. Is it running?";
      } else {
        console.error('Request Setup Error', error.message);
        errorMessage = `Request Error: ${error.message}`;
      }
      set({ output: errorMessage });
    } finally {
      set({ isRunning: false });
    }
  },
  clearOutput: () => set({ output: "" }),

  // === TFrameX Components State ===
  tframexComponents: { agents: [], tools: [], patterns: [], utility: [] }, // Added utility
  isComponentLoading: false,
  componentError: null,
  fetchTFrameXComponents: async () => {
    if (get().isComponentLoading) return;
    set({ isComponentLoading: true, componentError: null });
    try {
      const response = await axios.get(`${API_BASE_URL}/components`);
      if (response.data && typeof response.data === 'object') {
        // Add TextInputNode to utility components for NodesPanel
        const utilityComponents = [
          {
            id: 'textInput', // This will be the node type
            name: 'Text Input',
            description: 'A node to provide text input to a flow or agent. Has a large text box.',
            component_category: 'utility', // For categorization
            config_options: {}
          }
        ];
        set({
          tframexComponents: {
            agents: response.data.agents || [],
            tools: response.data.tools || [],
            patterns: response.data.patterns || [],
            utility: utilityComponents, // Add our frontend-only utility node
          },
          isComponentLoading: false,
        });
         console.log("Fetched TFrameX components (and added utility):", get().tframexComponents);
      } else { throw new Error("Invalid component response format from server."); }
    } catch (err) {
      console.error("Failed to fetch TFrameX components:", err);
      set({
        componentError: `Could not load TFrameX components. Backend error: ${err.message}. Is the backend running on port 5001?`,
        tframexComponents: { agents: [], tools: [], patterns: [], utility: [] },
        isComponentLoading: false,
      });
    }
  },

  // === Code Registration State ===
  isRegisteringCode: false,
  registrationStatus: null, 
  registerTFrameXCode: async (pythonCode) => {
    if (get().isRegisteringCode) return;
    set({ isRegisteringCode: true, registrationStatus: null });
    try {
      const response = await axios.post(`${API_BASE_URL}/register_code`, { python_code: pythonCode });
      set({ registrationStatus: response.data, isRegisteringCode: false });
      if (response.data?.success) {
        get().fetchTFrameXComponents(); 
      }
    } catch (error) {
      const message = error.response?.data?.error || error.message || "Failed to register code.";
      set({ registrationStatus: { success: false, message }, isRegisteringCode: false });
    }
  },

  // === Chatbot for Flow Building State ===
  chatHistory: [], 
  isChatbotLoading: false,
  addChatMessage: (sender, message, type = 'normal') => {
    set((state) => ({
      chatHistory: [...state.chatHistory, { sender, message, type }] 
    }));
  },
  clearChatHistory: () => set({ chatHistory: [] }),
  sendChatMessageToFlowBuilder: async (userMessage) => {
    const { nodes, edges, addChatMessage, fetchTFrameXComponents } = get();
    if (!userMessage.trim()) return;

    addChatMessage('user', userMessage);
    set({ isChatbotLoading: true });

    // Fetch latest components in case user registered new ones
    await fetchTFrameXComponents(); 
    // The discover_tframex_components on backend will be called by the chatbot endpoint anyway,
    // but fetching here ensures UI is up-to-date if chatbot needs to refer to something.

    try {
      const payload = {
        message: userMessage,
        nodes: nodes, 
        edges: edges,
      };
      const response = await axios.post(`${API_BASE_URL}/chatbot_flow_builder`, payload);
      console.log("Received from chatbot flow builder:", response.data);
      
      const reply = response.data?.reply || "Received no reply from chatbot flow builder.";
      const flowUpdate = response.data?.flow_update;

      addChatMessage('bot', reply);

      if (flowUpdate && Array.isArray(flowUpdate.nodes) && Array.isArray(flowUpdate.edges)) {
        // Before applying, ensure node types from chatbot exist in our dynamicNodeTypes
        // This is a simplified check; a more robust check would involve `get().tframexComponents`
        const allKnownTypes = [
            ...get().tframexComponents.agents.map(a => a.id),
            ...get().tframexComponents.patterns.map(p => p.id),
            ...get().tframexComponents.tools.map(t => t.id),
            ...get().tframexComponents.utility.map(u => u.id), // like 'textInput'
            'tframexAgent', 'tframexPattern', 'tframexTool' // Generic fallbacks if used
        ];
        
        const allNodesValid = flowUpdate.nodes.every(node => allKnownTypes.includes(node.type));

        if (allNodesValid) {
            set({ nodes: flowUpdate.nodes, edges: flowUpdate.edges });
            addChatMessage('bot', "(Flow canvas updated successfully)", 'info');
        } else {
            addChatMessage('bot', "(Chatbot proposed a flow with unknown component types. Update aborted.)", 'error');
            console.warn("Chatbot proposed invalid node types. Proposed:", flowUpdate.nodes.map(n=>n.type), "Known:", allKnownTypes);
        }
      } else if (response.data?.hasOwnProperty('flow_update') && flowUpdate !== null) {
        addChatMessage('bot', "(Chatbot returned an invalid flow structure)", 'error');
      }
    } catch (error) {
      console.error("Error sending chat message to flow builder:", error);
      let errorMessage = "Failed to get response from chatbot flow builder.";
      if (error.response) {
        errorMessage = `Chatbot Builder Error (${error.response.status}): ${error.response.data?.error || error.response.data?.reply || 'Unknown backend error'}`;
      } else if (error.request) {
        errorMessage = "Network Error: Could not connect to the chatbot flow builder backend.";
      } else {
        errorMessage = `Request Error: ${error.message}`;
      }
      addChatMessage('bot', errorMessage, 'error');
    } finally {
      set({ isChatbotLoading: false });
    }
  },
}));

// --- Persistence Subscription ---
useStore.subscribe(
  (state) => ({ 
    projects: state.projects, 
    currentProjectId: state.currentProjectId,
    // nodes: state.nodes, // Removed nodes/edges from direct save for project structure
    // edges: state.edges,
   }),
  (currentState) => {
    if (currentState.projects && currentState.currentProjectId) {
      // Save the entire projects object and the current project ID
      saveState('tframexStudioProjects', currentState.projects);
      saveState('tframexStudioCurrentProject', currentState.currentProjectId);

      // If you still want to save the current nodes/edges separately for some reason (e.g. quick recovery),
      // you could, but it's better to rely on the project structure.
      // const currentProject = currentState.projects[currentState.currentProjectId];
      // if (currentProject) {
      //   saveState('tframexStudioNodes', currentProject.nodes);
      //   saveState('tframexStudioEdges', currentProject.edges);
      // }
    }
  },
  { fireImmediately: false } 
);

// --- Initial Fetch of TFrameX Components ---
useStore.getState().fetchTFrameXComponents();