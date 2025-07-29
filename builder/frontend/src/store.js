// frontend/src/store.js
import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from 'reactflow';
import { nanoid } from 'nanoid';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api/tframex';

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
  selectedNodeId: null,

  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),

  onNodesChange: (changes) => set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) })),
  onEdgesChange: (changes) => set((state) => ({ edges: applyEdgeChanges(changes, state.edges) })),

  onConnect: (connection) => {
    console.log('onConnect fired! Connection:', connection);
    const nodes = get().nodes;
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);

    // --- CONNECTION TYPE 1: Agent to Pattern's general config input ---
    if (
      targetNode?.data?.component_category === 'pattern' &&
      sourceNode?.data?.component_category === 'agent' &&
      connection.targetHandle?.startsWith('pattern_agent_input_')
    ) {
      const paramName = connection.targetHandle.substring('pattern_agent_input_'.length);
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
    const listMatch = connection.targetHandle?.match(
      /^pattern_list_item_input_(.+?)_(\d+)$/ // Updated regex to match generic paramName
    );
    if (
      targetNode?.data?.component_category === 'pattern' &&
      sourceNode?.data?.component_category === 'agent' &&
      listMatch
    ) {
      // listMatch[1] is paramName, listMatch[2] is index
      const [, paramName, idxStr] = listMatch;
      const index = parseInt(idxStr, 10);
      const agentIdToAssign = sourceNode.data.tframex_component_id || sourceNode.id;

      // Grab or init the array
      const currentList = Array.isArray(targetNode.data[paramName])
        ? [...targetNode.data[paramName]]
        : [];
      // Ensure slot exists
      while (currentList.length <= index) {
        currentList.push(null);
      }

      // Assign and update
      currentList[index] = agentIdToAssign;
      get().updateNodeData(targetNode.id, { [paramName]: currentList });

      // Draw the edge
      set((state) => ({
        edges: addEdge(
          {
            ...connection,
            type: 'smoothstep',
            style: { ...connection.style, stroke: '#4CAF50', strokeWidth: 2, zIndex: 0 },
            animated: false,
            data: { ...connection.data, connectionType: 'agentToPatternListItem' },
          },
          state.edges
        ),
      }));
      return;
    }

    // --- CONNECTION TYPE 3: Tool's "attachment" handle to Agent's "tool input" handle ---
    if (
      sourceNode?.data?.component_category === 'tool' &&
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
    if (
      sourceNode?.data?.component_category === 'tool' &&
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
          data: { ...connection.data, connectionType: 'toolDataOutputToAgent' }
        }, state.edges),
      }));
      return;
    }

    // --- CONNECTION TYPE 5: TextInputNode's output to an Agent's "message input" handle ---
    if (
      sourceNode?.type === 'textInput' &&
      targetNode?.data?.component_category === 'agent' &&
      connection.targetHandle === 'input_message_in'
    ) {
      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          animated: true,
          style: { strokeWidth: 2, stroke: '#0ea5e9' },
          data: { ...connection.data, connectionType: 'textInputToAgent' }
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
    const {
      component_category,
      id: componentId,
      name: componentName,
      tframex_agent_type,
      config_options,
      constructor_params_schema,
    } = nodeDataFromDrop;

    let defaultNodeData = {
      label: componentName || componentId,
      component_category,
      tframex_component_id: componentId,
    };

    let nodeType = componentId;

    if (component_category === 'agent') {
      defaultNodeData = {
        ...defaultNodeData,
        selected_tools: config_options?.default_tools || [],
        template_vars_config: {},
        system_prompt_override: "",
        tframex_agent_type,
        can_use_tools: config_options?.can_use_tools || false,
        strip_think_tags_override: config_options?.strip_think_tags || false,
      };
    } else if (component_category === 'pattern') {
      const patternParams = {};
      // Removed specific listAgentParams, now all 'list' type_hints are treated generally
      if (constructor_params_schema) {
        for (const paramName in constructor_params_schema) {
          const paramInfo = constructor_params_schema[paramName];
          if (paramInfo.type_hint?.toLowerCase().includes('list')) { // General list initialization
            patternParams[paramName] = [];
          } else if (
            paramInfo.type_hint?.toLowerCase().includes('agent') ||
            paramName.startsWith('agent_') ||
            paramName.endsWith('_agent_name')
          ) {
            patternParams[paramName] = null;
          } else if (
            paramName === 'routes' &&
            paramInfo.type_hint?.toLowerCase().includes('dict')
          ) {
            patternParams[paramName] = {};
          } else if (paramInfo.type_hint?.toLowerCase().includes('dict')) { // General dict initialization
            patternParams[paramName] = {};
          } else if (
            paramInfo.type_hint
              ?.toLowerCase()
              .includes('int') ||
            paramInfo.type_hint
              ?.toLowerCase()
              .includes('float')
          ) {
            patternParams[paramName] =
              paramInfo.default !== "REQUIRED" &&
              paramInfo.default !== undefined
                ? parseFloat(paramInfo.default) || null
                : null;
          } else if (
            paramInfo.type_hint
              ?.toLowerCase()
              .includes('bool')
          ) {
            patternParams[paramName] =
              paramInfo.default !== "REQUIRED" &&
              paramInfo.default !== undefined
                ? String(paramInfo.default).toLowerCase() === 'true'
                : false;
          } else {
            patternParams[paramName] =
              paramInfo.default !== "REQUIRED" &&
              paramInfo.default !== undefined
                ? String(paramInfo.default)
                : '';
          }
        }
      }
      defaultNodeData = { ...defaultNodeData, ...patternParams };
    } else if (component_category === 'tool') {
      defaultNodeData.is_tool_node = true;
      defaultNodeData.has_data_output =
        nodeDataFromDrop.config_options?.has_data_output ||
        (nodeDataFromDrop.parameters_schema &&
          Object.keys(nodeDataFromDrop.parameters_schema)
            .length > 0 &&
          nodeDataFromDrop.description
            ?.toLowerCase()
            .includes("return"));
    } else if (
      component_category === 'utility' &&
      componentId === 'textInput'
    ) {
      nodeType = 'textInput';
      defaultNodeData = {
        label: "Text Input",
        text_content: "Enter your prompt or text here...",
        component_category: 'utility',
      };
    }

    const newNode = {
      id: `${nodeType}-${nanoid(6)}`,
      type: nodeType,
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
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    }));
  },

  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
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
        selectedNodeId: null,
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

    let initialInputContent = "User input from Studio to start the flow.";
    const textInputNode = nodes.find(n => n.type === 'textInput');
    if (textInputNode) {
      const isConnectedAsStart = edges.some(edge =>
        edge.source === textInputNode.id &&
        nodes.find(n => n.id === edge.target)?.data.component_category === 'agent' &&
        !edges.some(e => e.target === textInputNode.id)
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
  tframexComponents: { agents: [], tools: [], patterns: [], utility: [] },
  isComponentLoading: false,
  componentError: null,
  fetchTFrameXComponents: async () => {
    if (get().isComponentLoading) return;
    set({ isComponentLoading: true, componentError: null });
    try {
      const response = await axios.get(`${API_BASE_URL}/components`);
      if (response.data && typeof response.data === 'object') {
        const utilityComponents = [
          {
            id: 'textInput',
            name: 'Text Input',
            description: 'A node to provide text input to a flow or agent. Has a large text box.',
            component_category: 'utility',
            config_options: {}
          }
        ];
        set({
          tframexComponents: {
            agents: response.data.agents || [],
            tools: response.data.tools || [],
            patterns: response.data.patterns || [],
            utility: utilityComponents,
          },
          isComponentLoading: false,
        });
        console.log("Fetched TFrameX components (and added utility):", get().tframexComponents);
      } else {
        throw new Error("Invalid component response format from server.");
      }
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

  // === Chatbot for Flow Builder State ===
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

    await fetchTFrameXComponents();

    try {
      const payload = { message: userMessage, nodes, edges };
      console.log("🚀 [FIXED VERSION] Sending to chatbot flow builder:", payload);
      
      const response = await axios.post(`${API_BASE_URL}/chatbot_flow_builder`, payload);
      console.log("Raw response from chatbot flow builder:", response);
      console.log("Response data from chatbot flow builder:", response.data);
      console.log("Response data type:", typeof response.data);

      // More defensive checks for response structure
      if (!response) {
        console.error("No response object received:", response);
        addChatMessage('bot', "Error: No response received from server.", 'error');
        return;
      }

      if (!response.data) {
        console.error("Response object has no data field:", response);
        addChatMessage('bot', "Error: Server response missing data field.", 'error');
        return;
      }

      let responseData;
      try {
        // Handle case where response.data might be a string that needs parsing
        if (typeof response.data === 'string') {
          console.log("Response data is string, attempting to parse JSON:", response.data);
          responseData = JSON.parse(response.data);
        } else {
          responseData = response.data;
        }
      } catch (parseError) {
        console.error("Failed to parse response data:", parseError, response.data);
        addChatMessage('bot', "Error: Could not parse server response.", 'error');
        return;
      }

      console.log("Parsed responseData:", responseData);
      console.log("ResponseData type:", typeof responseData);

      const reply = responseData?.reply || "Received no reply from chatbot flow builder.";
      const flowUpdate = responseData?.flow_update;

      console.log("Extracted reply:", reply);
      console.log("Extracted flowUpdate:", flowUpdate);

      console.log("🔵 About to call addChatMessage with reply:", reply);
      try {
        addChatMessage('bot', reply);
        console.log("✅ addChatMessage succeeded");
      } catch (addMessageError) {
        console.error("❌ Error in addChatMessage:", addMessageError);
        throw addMessageError;
      }

      if (flowUpdate && Array.isArray(flowUpdate.nodes) && Array.isArray(flowUpdate.edges)) {
        const allKnownTypes = [
          ...get().tframexComponents.agents.map(a => a.id),
          ...get().tframexComponents.patterns.map(p => p.id),
          ...get().tframexComponents.tools.map(t => t.id),
          ...get().tframexComponents.utility.map(u => u.id),
          'textInput'
        ];
        const allNodesValid = flowUpdate.nodes.every(node => allKnownTypes.includes(node.type));

        if (allNodesValid) {
          set({ nodes: flowUpdate.nodes, edges: flowUpdate.edges });
          addChatMessage('bot', "(Flow canvas updated successfully)", 'info');
        } else {
          addChatMessage('bot', "(Chatbot proposed a flow with unknown component types. Update aborted.)", 'error');
          console.warn("Chatbot proposed invalid node types.", flowUpdate.nodes.map(n=>n.type), "Known:", allKnownTypes);
        }
      } else if (responseData.hasOwnProperty('flow_update') && flowUpdate !== null) {
        addChatMessage('bot', "(Chatbot returned an invalid flow structure)", 'error');
      }

      // Return the response data for TerminalPanel
      return responseData;
    } catch (error) {
      console.error("Error sending chat message to flow builder:", error);
      console.error("Error details:", {
        message: error.message,
        response: error.response,
        request: error.request
      });
      
      let errorMessage = "Failed to get response from chatbot flow builder.";
      if (error.response) {
        console.error("Backend error response:", error.response.data);
        errorMessage = `Chatbot Builder Error (${error.response.status}): ${error.response.data?.error || error.response.data?.reply || 'Unknown backend error'}`;
      } else if (error.request) {
        errorMessage = "Network Error: Could not connect to the chatbot flow builder backend.";
      } else {
        errorMessage = `Request Error: ${error.message}`;
      }
      addChatMessage('bot', errorMessage, 'error');
      
      // Return error response for TerminalPanel
      return { reply: errorMessage, flow_update: null };
    } finally {
      set({ isChatbotLoading: false });
    }
  },
}));

// Persist projects & currentProjectId
useStore.subscribe(
  (state) => ({
    projects: state.projects,
    currentProjectId: state.currentProjectId,
  }),
  (currentState) => {
    if (currentState.projects && currentState.currentProjectId) {
      saveState('tframexStudioProjects', currentState.projects);
      saveState('tframexStudioCurrentProject', currentState.currentProjectId);
    }
  },
  { fireImmediately: false }
);

// Initial load of components
useStore.getState().fetchTFrameXComponents();