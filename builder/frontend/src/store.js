// src/store.js
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
  
  onNodesChange: (changes) => set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) })),
  onEdgesChange: (changes) => set((state) => ({ edges: applyEdgeChanges(changes, state.edges) })),
  
  onConnect: (connection) => {
    const nodes = get().nodes;
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);

    // --- CONNECTION TYPE 1: Agent to Pattern's general config input ---
    // (e.g., connecting an Agent to a RouterPattern's 'router_agent_name' input)
    if (targetNode?.data?.component_category === 'pattern' && 
        sourceNode?.data?.component_category === 'agent' &&
        connection.targetHandle?.startsWith('pattern_agent_input_') && // Target is a specific pattern param input
        connection.sourceHandle === 'output_message_out' // Source is the agent's main output
      ) {
      
      const paramName = connection.targetHandle.substring('pattern_agent_input_'.length);
      const agentIdToAssign = sourceNode.data.tframex_component_id || sourceNode.id;

      get().updateNodeData(targetNode.id, { [paramName]: agentIdToAssign });
      
      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          style: { ...connection.style, stroke: '#F59E0B', strokeWidth: 2.5, zIndex: 0 }, // Amber, slightly thicker
          animated: false,
          data: { ...connection.data, connectionType: 'agentInstanceToPatternParam' }
        }, state.edges),
      }));
      return;
    }

    // --- CONNECTION TYPE 2: Agent to Pattern's list item slot ---
    // (e.g., connecting Agent to DiscussionPattern's 'participant_agent_names[0]' slot)
    if (targetNode?.data?.component_category === 'pattern' &&
        sourceNode?.data?.component_category === 'agent' &&
        connection.targetHandle?.startsWith('pattern_list_item_input_') && // Target is a list item slot
        connection.sourceHandle === 'output_message_out' // Source is the agent's main output
      ) {
      
      const parts = connection.targetHandle.split('_');
      const paramName = parts[4];
      const index = parseInt(parts[5], 10);
      const agentIdToAssign = sourceNode.data.tframex_component_id || sourceNode.id;

      const currentList = Array.isArray(targetNode.data[paramName]) ? [...targetNode.data[paramName]] : [];
      // Ensure the list is long enough (it should be if UI added slots correctly)
      while (currentList.length <= index) {
        currentList.push(null); // Pad with null if necessary
      }

      if (index >= 0 && index < currentList.length) {
        currentList[index] = agentIdToAssign;
        get().updateNodeData(targetNode.id, { [paramName]: currentList });

        set((state) => ({
          edges: addEdge({
            ...connection,
            type: 'smoothstep',
            style: { ...connection.style, stroke: '#4CAF50', strokeWidth: 2, zIndex: 0 }, // Green
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
        connection.sourceHandle === 'tool_attachment_out' && // From tool's attachment handle
        connection.targetHandle === 'tool_input_handle'       // To agent's tool input handle
      ) {
      
      const toolName = sourceNode.data.tframex_component_id || sourceNode.id;
      const currentSelectedTools = targetNode.data.selected_tools || [];
      
      if (!currentSelectedTools.includes(toolName)) {
        get().updateNodeData(targetNode.id, {
          selected_tools: [...currentSelectedTools, toolName]
        });
      }
      
      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#a5b4fc', strokeDasharray: '5 5', strokeWidth: 1.5, zIndex: 0 }, // Indigo, dashed
          data: { ...connection.data, connectionType: 'toolAttachment' }
        }, state.edges),
      }));
      return;
    }

    // --- CONNECTION TYPE 4: Tool's "data output" handle to an Agent's "message input" handle ---
    // This also implies enabling the tool.
    if (sourceNode?.data?.component_category === 'tool' &&
        connection.sourceHandle === 'tool_output_data' &&    // From tool's data output
        targetNode?.data?.component_category === 'agent' &&
        connection.targetHandle === 'input_message_in'      // To agent's message input
      ) {
        
        const toolName = sourceNode.data.tframex_component_id || sourceNode.id;
        const currentSelectedTools = targetNode.data.selected_tools || [];
        if (!currentSelectedTools.includes(toolName)) {
            get().updateNodeData(targetNode.id, {
                selected_tools: [...currentSelectedTools, toolName]
            });
            console.log(`UI: Tool '${toolName}' implicitly enabled on Agent '${targetNode.data.label || targetNode.id}' due to data connection.`);
        }
        // Proceed to create a standard data flow edge
        set((state) => ({
            edges: addEdge({ 
                ...connection, 
                type: 'smoothstep', 
                animated: true, 
                style: { strokeWidth: 2, stroke: '#7c3aed' }, // Purple for tool data
                data: {...connection.data, connectionType: 'toolDataOutputToAgent'} 
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
          style: { strokeWidth: 2 } // Default flow color from App.jsx will apply
        }, state.edges),
    }));
  },

  addNode: (nodeDataFromDrop, position) => {
    const { component_category, id: componentId, name: componentName, tframex_agent_type, config_options, constructor_params_schema } = nodeDataFromDrop;
    
    let defaultNodeData = { 
      label: componentName || componentId,
      component_category: component_category,
      tframex_component_id: componentId, 
    };

    if (component_category === 'agent') {
      defaultNodeData = {
        ...defaultNodeData,
        selected_tools: config_options?.default_tools || [], 
        template_vars_config: {}, 
        tframex_agent_type: tframex_agent_type,
        can_use_tools: config_options?.can_use_tools || false,
        strip_think_tags_override: config_options?.strip_think_tags,
      };
    } else if (component_category === 'pattern') {
      const patternParams = {};
      const listAgentParams = ['participant_agent_names', 'tasks', 'steps']; // From TFrameXPatternNode
      if (constructor_params_schema) {
        for (const paramName in constructor_params_schema) {
          const paramInfo = constructor_params_schema[paramName];
          if (listAgentParams.includes(paramName) && paramInfo.type_hint?.toLowerCase().includes('list')) {
            patternParams[paramName] = []; // CRITICAL: Initialize as empty list for agent slots
          } else if (paramInfo.type_hint?.toLowerCase().includes('agent') || paramName.startsWith('agent_') || paramName.endsWith('_agent')) {
            patternParams[paramName] = null; 
          } else if (paramInfo.type_hint?.toLowerCase().includes('list')) patternParams[paramName] = [];
          else if (paramInfo.type_hint?.toLowerCase().includes('dict')) patternParams[paramName] = {};
          else if (paramInfo.type_hint?.toLowerCase().includes('int') || paramInfo.type_hint?.toLowerCase().includes('float')) patternParams[paramName] = null;
          else if (paramInfo.type_hint?.toLowerCase().includes('bool')) patternParams[paramName] = false;
          else patternParams[paramName] = '';
          
          if (paramInfo.default && paramInfo.default !== "REQUIRED") {
            try { patternParams[paramName] = JSON.parse(paramInfo.default); }
            catch (e) { patternParams[paramName] = paramInfo.default; }
          }
        }
      }
      defaultNodeData = { ...defaultNodeData, ...patternParams };
    } else if (component_category === 'tool') {
        defaultNodeData.is_tool_node = true;
        // Example: backend might tell us if a tool produces data
        // This info would ideally come from the component discovery endpoint
        // Assuming nodeDataFromDrop contains fields like 'parameters_schema' and 'description' if they are relevant
        defaultNodeData.has_data_output = nodeDataFromDrop.config_options?.has_data_output || 
                                          (nodeDataFromDrop.parameters_schema && Object.keys(nodeDataFromDrop.parameters_schema).length > 0 && nodeDataFromDrop.description?.toLowerCase().includes("return"));
    }

    const newNode = {
      id: `${componentId}-${nanoid(6)}`, 
      type: componentId, // This should match the registered custom node type names
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
        // Persistence handled by subscribe
        console.log(`Project '${currentProject.name}' saved.`);
    }
  },

  loadProject: (projectId) => {
    const { projects, saveCurrentProject } = get();
    const projectToLoad = projects[projectId];

    if (projectToLoad) {
      saveCurrentProject(); // Save current state before switching
      set({
        nodes: projectToLoad.nodes || [...initialDefaultProjectNodes],
        edges: projectToLoad.edges || [],
        currentProjectId: projectId,
        output: "Output will appear here...", // Clear output
        chatHistory: [], // Clear chat history
      });
      // Persistence handled by subscribe
      console.log(`Project '${projectToLoad.name}' loaded.`);
    } else {
        console.warn(`Project with ID ${projectId} not found.`);
    }
  },

  createProject: (name) => {
    const { projects, saveCurrentProject } = get();
    saveCurrentProject(); // Save current state before creating

    const newProjectId = `project_${nanoid(8)}`;
    const newProject = {
        name: name || `New TFrameX Project ${Object.keys(projects).length + 1}`,
        nodes: [...initialDefaultProjectNodes], // Start with default nodes
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
    });
    // Persistence handled by subscribe
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
      // Persistence handled by subscribe

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
    saveCurrentProject(); // Save before running

    set({ isRunning: true, output: "Executing TFrameX flow..." });
    console.log("Sending to TFrameX backend:", { nodes, edges });

    // TODO: Allow UI to specify initial_input and global_flow_template_vars
    const payload = {
        nodes,
        edges,
        initial_input: "User input from Studio to start the flow.", // Example
        global_flow_template_vars: { "studio_user": "VisualBuilder" } // Example
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
        errorMessage = `TFrameX Backend Error (${error.response.status}): ${error.response.data?.error || 'Unknown error'}`;
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
  tframexComponents: { agents: [], tools: [], patterns: [] },
  isComponentLoading: false,
  componentError: null,
  fetchTFrameXComponents: async () => {
    if (get().isComponentLoading) return;
    set({ isComponentLoading: true, componentError: null });
    try {
      const response = await axios.get(`${API_BASE_URL}/components`);
      if (response.data && typeof response.data === 'object') {
        set({
          tframexComponents: {
            agents: response.data.agents || [],
            tools: response.data.tools || [],
            patterns: response.data.patterns || [],
          },
          isComponentLoading: false,
        });
         console.log("Fetched TFrameX components:", response.data);
      } else { throw new Error("Invalid component response format from server."); }
    } catch (err) {
      console.error("Failed to fetch TFrameX components:", err);
      set({
        componentError: `Could not load TFrameX components. Backend error: ${err.message}. Is the backend running on port 5001?`,
        tframexComponents: { agents: [], tools: [], patterns: [] },
        isComponentLoading: false,
      });
    }
  },

  // === Code Registration State ===
  isRegisteringCode: false,
  registrationStatus: null, // { success: boolean, message: string }
  registerTFrameXCode: async (pythonCode) => {
    if (get().isRegisteringCode) return;
    set({ isRegisteringCode: true, registrationStatus: null });
    try {
      const response = await axios.post(`${API_BASE_URL}/register_code`, { python_code: pythonCode });
      set({ registrationStatus: response.data, isRegisteringCode: false });
      if (response.data?.success) {
        get().fetchTFrameXComponents(); // Re-fetch components after successful registration
      }
    } catch (error) {
      const message = error.response?.data?.error || error.message || "Failed to register code.";
      set({ registrationStatus: { success: false, message }, isRegisteringCode: false });
    }
  },

  // === Chatbot for Flow Building State ===
  chatHistory: [], // Array of { sender: 'user' | 'bot', message: string, type?: 'error' | 'normal' | 'info' }
  isChatbotLoading: false,
  addChatMessage: (sender, message, type = 'normal') => {
    set((state) => ({
      chatHistory: [...state.chatHistory, { sender, message, type }] //.slice(-50) // Optional: limit history
    }));
  },
  clearChatHistory: () => set({ chatHistory: [] }),
  sendChatMessageToFlowBuilder: async (userMessage) => {
    const { nodes, edges, addChatMessage, fetchTFrameXComponents } = get();
    if (!userMessage.trim()) return;

    addChatMessage('user', userMessage);
    set({ isChatbotLoading: true });

    await fetchTFrameXComponents(); 

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
        set({ nodes: flowUpdate.nodes, edges: flowUpdate.edges });
        addChatMessage('bot', "(Flow canvas updated successfully)", 'info');
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
  (state) => ({ projects: state.projects, currentProjectId: state.currentProjectId }),
  (currentState) => {
    if (currentState.projects && currentState.currentProjectId) {
      saveState('tframexStudioProjects', currentState.projects);
      saveState('tframexStudioCurrentProject', currentState.currentProjectId);
    }
  },
  { fireImmediately: false } // Only save on actual changes after initial load
);

// --- Initial Fetch of TFrameX Components ---
useStore.getState().fetchTFrameXComponents();