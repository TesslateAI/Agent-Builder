// frontend/src/store.js
import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from 'reactflow';
import { nanoid } from 'nanoid';
import axios from 'axios';
import { debounce } from 'lodash';
import { getLayoutedElements, LAYOUT_DIRECTIONS } from './utils/autoLayout';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/tframex';

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
    viewport: { x: 0, y: 0, zoom: 1 },
  },
};

const savedProjects = loadState('tframexStudioProjects') || initialProjects;
const savedCurrentProjectId = loadState('tframexStudioCurrentProject');

// Ensure currentProjectId is valid - if saved ID doesn't exist in projects, use first available project
const initialProjectId = savedCurrentProjectId && savedProjects[savedCurrentProjectId] 
  ? savedCurrentProjectId 
  : Object.keys(savedProjects)[0] || 'default_project';

// Debounced save function for performance during dragging
const debouncedSaveProjects = debounce((projects) => {
  saveState('tframexStudioProjects', projects);
}, 500);

// Debounced auto-save function with longer delay for regular changes
const debouncedAutoSave = debounce(() => {
  const state = useStore.getState();
  if (state.currentProjectId && state.projects[state.currentProjectId]) {
    state.saveCurrentProject();
    state.setAutoSaveStatus('saved');
  }
}, 2000); // 2 second delay for auto-save

export const useStore = create((set, get) => ({
  // === React Flow State ===
  nodes: savedProjects[initialProjectId]?.nodes || [...initialDefaultProjectNodes],
  edges: savedProjects[initialProjectId]?.edges || [],
  selectedNodeId: null,

  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),

  onNodesChange: (changes) => {
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) }));
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
  },
  onEdgesChange: (changes) => {
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges) }));
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
  },

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

    // --- CONNECTION TYPE 3B: MCP Server's "attachment" handle to Agent's "tool input" handle ---
    if (
      sourceNode?.data?.component_category === 'mcp_server' &&
      targetNode?.data?.component_category === 'agent' &&
      connection.sourceHandle === 'mcp_server_attachment_out' &&
      connection.targetHandle === 'tool_input_handle'
    ) {
      const serverAlias = sourceNode.data.server_alias || sourceNode.id;
      const currentConnectedServers = targetNode.data.connected_mcp_servers || [];

      if (!currentConnectedServers.includes(serverAlias)) {
        get().updateNodeData(targetNode.id, {
          connected_mcp_servers: [...currentConnectedServers, serverAlias]
        });
        console.log(`UI: MCP Server '${serverAlias}' connected to Agent '${targetNode.data.label || targetNode.id}' via connection.`);
      }

      set((state) => ({
        edges: addEdge({
          ...connection,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#10b981', strokeDasharray: '3 7', strokeWidth: 2, zIndex: 0 },
          data: { ...connection.data, connectionType: 'mcpServerAttachment' }
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
    
    // Trigger auto-save after any connection
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
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
        connected_mcp_servers: [],
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
    } else if (component_category === 'mcp_server') {
      nodeType = 'MCPServerNode';
      defaultNodeData = {
        ...defaultNodeData,
        server_alias: '',
        command: '',
        args: [],
        env: {},
        status: 'disconnected',
        available_tools: [],
      };
    } else if (
      component_category === 'utility' &&
      componentId === 'textInput'
    ) {
      nodeType = 'textInput';
      defaultNodeData = {
        label: "Text Input",
        text_content: "",
        component_category: 'utility',
      };
    } else if (component_category === 'triggers') {
      // Handle individual trigger types
      if (componentId === 'webhookTrigger') {
        nodeType = 'webhookTrigger';
        defaultNodeData = {
          label: "Webhook Trigger",
          name: "Webhook Trigger",
          description: "",
          enabled: true,
          component_category: 'triggers',
          webhookConfig: {
            method: 'POST',
            path: '/webhook',
            headers: {},
            auth: { type: 'none' }
          }
        };
      } else if (componentId === 'emailTrigger') {
        nodeType = 'emailTrigger';
        defaultNodeData = {
          label: "Email Trigger",
          name: "Email Trigger", 
          description: "",
          enabled: true,
          component_category: 'triggers',
          emailConfig: {
            host: 'imap.gmail.com',
            port: 993,
            username: '',
            password: '',
            folder: 'INBOX'
          }
        };
      } else if (componentId === 'scheduleTrigger') {
        nodeType = 'scheduleTrigger';
        defaultNodeData = {
          label: "Schedule Trigger",
          name: "Schedule Trigger",
          description: "",
          enabled: true,
          component_category: 'triggers',
          scheduleConfig: {
            type: 'interval',
            interval: 5,
            intervalUnit: 'minutes',
            cron: ''
          }
        };
      } else if (componentId === 'fileTrigger') {
        nodeType = 'fileTrigger';
        defaultNodeData = {
          label: "File Trigger",
          name: "File Trigger",
          description: "",
          enabled: true,
          component_category: 'triggers',
          fileConfig: {
            path: '',
            pattern: '*',
            events: ['created', 'modified'],
            recursive: false
          }
        };
      }
    }

    const newNode = {
      id: `${nodeType}-${nanoid(6)}`,
      type: nodeType,
      position,
      data: defaultNodeData,
    };
    set((state) => ({ nodes: [...state.nodes, newNode] }));
    
    // Trigger auto-save after adding a node
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
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
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
  },

  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    }));
    get().setAutoSaveStatus('saving');
    debouncedAutoSave();
  },

  // === Project Management State ===
  projects: savedProjects,
  currentProjectId: initialProjectId,

  saveCurrentProject: (viewport) => {
    const { nodes, edges, currentProjectId, projects } = get();
    const currentProject = projects[currentProjectId];
    if (currentProject) {
      const updatedProjects = {
        ...projects,
        [currentProjectId]: { 
          ...currentProject, 
          nodes, 
          edges,
          viewport: viewport || currentProject.viewport || { x: 0, y: 0, zoom: 1 }
        }
      };
      set({ projects: updatedProjects });
      
      // Immediately save to localStorage to ensure persistence
      saveState('tframexStudioProjects', updatedProjects);
      saveState('tframexStudioCurrentProject', currentProjectId);
      
      console.log(`Project '${currentProject.name}' saved to memory and localStorage.`);
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
      
      // Save the current project ID to localStorage
      saveState('tframexStudioCurrentProject', projectId);
      
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
      edges: [],
      viewport: { x: 0, y: 0, zoom: 1 }
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
    
    // Save the new project and current project ID to localStorage
    saveState('tframexStudioProjects', updatedProjects);
    saveState('tframexStudioCurrentProject', newProjectId);
    
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
    
    // Save updated projects to localStorage
    saveState('tframexStudioProjects', updatedProjects);

    if (currentProjectId === projectId) {
      loadProject(nextProjectId);
    }
    console.log(`Project "${projects[projectId].name}" deleted.`);
  },

  // === Execution State ===
  output: "Output will appear here...",
  isRunning: false,
  
  // === Auto-save State ===
  autoSaveEnabled: true, // Always enabled
  autoSaveStatus: 'idle', // 'idle', 'saving', 'saved'
  lastSaveTime: null,
  
  setAutoSaveStatus: (status) => {
    set({ 
      autoSaveStatus: status,
      lastSaveTime: status === 'saved' ? new Date().toISOString() : get().lastSaveTime
    });
    // Reset status after showing saved
    if (status === 'saved') {
      setTimeout(() => {
        const currentStatus = get().autoSaveStatus;
        if (currentStatus === 'saved') {
          set({ autoSaveStatus: 'idle' });
        }
      }, 3000);
    }
  },
  runFlow: async () => {
    const { nodes, edges, saveCurrentProject } = get();
    saveCurrentProject(); // This will save viewport too

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
  tframexComponents: { agents: [], tools: [], patterns: [], utility: [], mcp_servers: [], triggers: [] },
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

        const triggerComponents = [
          {
            id: 'webhookTrigger',
            name: 'Webhook Trigger',
            description: 'HTTP endpoint that triggers flows when receiving requests',
            component_category: 'triggers',
            config_options: {}
          },
          {
            id: 'emailTrigger',
            name: 'Email Trigger',
            description: 'Monitor email accounts and trigger flows on new messages',
            component_category: 'triggers',
            config_options: {}
          },
          {
            id: 'scheduleTrigger',
            name: 'Schedule Trigger',
            description: 'Time-based triggers using cron expressions or intervals',
            component_category: 'triggers',
            config_options: {}
          },
          {
            id: 'fileTrigger',
            name: 'File Trigger',
            description: 'Watch file systems for changes and trigger flows',
            component_category: 'triggers',
            config_options: {}
          }
        ];
        set({
          tframexComponents: {
            agents: response.data.agents || [],
            tools: response.data.tools || [],
            patterns: response.data.patterns || [],
            utility: utilityComponents,
            mcp_servers: response.data.mcp_servers || [],
            triggers: triggerComponents,
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
        componentError: `Could not load TFrameX components. Backend error: ${err.message}. Is the backend running and accessible?`,
        tframexComponents: { agents: [], tools: [], patterns: [], utility: [], mcp_servers: [], triggers: [] },
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
    console.log("🚀 START sendChatMessageToFlowBuilder:", userMessage);
    const { nodes, edges, addChatMessage, fetchTFrameXComponents } = get();
    console.log("📊 Current state - nodes:", nodes.length, "edges:", edges.length);
    
    if (!userMessage.trim()) {
      console.log("❌ Empty message, returning");
      return;
    }

    addChatMessage('user', userMessage);
    set({ isChatbotLoading: true });
    console.log("⏳ Set loading state to true");

    await fetchTFrameXComponents();
    console.log("📦 Components fetched");

    try {
      const payload = { message: userMessage, nodes, edges };
      console.log("🚀 [DETAILED LOGGING] Sending to chatbot flow builder:", payload);
      
      const response = await axios.post(`${API_BASE_URL}/chatbot_flow_builder`, payload);
      console.log("📡 Raw response from chatbot flow builder:", response);
      console.log("📋 Response data from chatbot flow builder:", response.data);
      console.log("🔍 Response data type:", typeof response.data);

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

      console.log("💬 Extracted reply:", reply);
      console.log("🔄 Extracted flowUpdate:", flowUpdate);
      console.log("🔄 flowUpdate type:", typeof flowUpdate);
      console.log("🔄 flowUpdate structure:", {
        hasFlowUpdate: !!flowUpdate,
        hasNodes: flowUpdate && Array.isArray(flowUpdate.nodes),
        hasEdges: flowUpdate && Array.isArray(flowUpdate.edges),
        nodesLength: flowUpdate?.nodes?.length,
        edgesLength: flowUpdate?.edges?.length
      });

      console.log("🔵 About to call addChatMessage with reply:", reply);
      try {
        addChatMessage('bot', reply);
        console.log("✅ addChatMessage succeeded");
      } catch (addMessageError) {
        console.error("❌ Error in addChatMessage:", addMessageError);
        throw addMessageError;
      }

      if (flowUpdate && Array.isArray(flowUpdate.nodes) && Array.isArray(flowUpdate.edges)) {
        console.log("🎯 FLOW UPDATE PROCESSING STARTED");
        console.log("🔄 Processing flow update:", flowUpdate);
        
        // Get current state
        const currentState = get();
        const existingNodes = currentState.nodes;
        const existingEdges = currentState.edges;
        
        console.log("📊 Current state before processing:", {
          existingNodesCount: existingNodes.length,
          existingEdgesCount: existingEdges.length,
          tframexComponents: {
            agents: currentState.tframexComponents.agents.length,
            patterns: currentState.tframexComponents.patterns.length,
            tools: currentState.tframexComponents.tools.length,
            utility: currentState.tframexComponents.utility.length,
            mcp_servers: currentState.tframexComponents.mcp_servers.length,
            triggers: currentState.tframexComponents.triggers.length
          }
        });
        
        // Create mapping from component names to IDs for validation
        const componentTypeMap = new Map();
        
        // Build component type mapping
        [...currentState.tframexComponents.agents, 
         ...currentState.tframexComponents.patterns, 
         ...currentState.tframexComponents.tools,
         ...currentState.tframexComponents.utility,
         ...currentState.tframexComponents.mcp_servers,
         ...currentState.tframexComponents.triggers].forEach(comp => {
          componentTypeMap.set(comp.id, comp.id);
          componentTypeMap.set(comp.name, comp.id);
        });
        
        // Add special node types
        componentTypeMap.set('textInput', 'textInput');
        componentTypeMap.set('MCPServerNode', 'MCPServerNode');
        
        console.log("🗺️ Component mapping ready:", componentTypeMap.size, "types");
        
        // Process and validate new nodes
        const processedNodes = [];
        let allNodesValid = true;
        
        // Process and validate nodes
        for (const newNode of flowUpdate.nodes) {
          const mappedType = componentTypeMap.get(newNode.type);
          
          if (!mappedType) {
            console.error(`❌ Unknown node type: ${newNode.type}`);
            console.error(`❌ Available types:`, Array.from(componentTypeMap.keys()));
            allNodesValid = false;
            break;
          }
          
          // Find next available position to avoid overlaps
          const findAvailablePosition = (preferredX = 100, preferredY = 100) => {
            const spacing = 200;
            const maxCols = 6;
            let position = { x: preferredX, y: preferredY };
            
            for (let row = 0; row < 10; row++) {
              for (let col = 0; col < maxCols; col++) {
                const testX = 100 + (col * spacing);
                const testY = 100 + (row * spacing);
                
                // Check if position is free
                const positionTaken = [...existingNodes, ...processedNodes].some(node => 
                  Math.abs(node.position.x - testX) < 150 && 
                  Math.abs(node.position.y - testY) < 150
                );
                
                if (!positionTaken) {
                  return { x: testX, y: testY };
                }
              }
            }
            
            return position; // Fallback to preferred position
          };
          
          const newPosition = findAvailablePosition(newNode.position?.x, newNode.position?.y);
          console.log(`📍 Position calculated:`, newPosition);
          
          // Create processed node with unique ID and proper positioning
          const processedNode = {
            ...newNode,
            id: `${mappedType}-${nanoid(6)}`, // Generate unique ID
            type: mappedType, // Use mapped type
            position: newPosition,
            data: {
              ...newNode.data,
              // Ensure proper component mapping
              tframex_component_id: mappedType,
            }
          };
          
          console.log(`➕ Created processed node:`, {
            id: processedNode.id,
            type: processedNode.type,
            position: processedNode.position,
            label: processedNode.data?.label
          });
          
          processedNodes.push(processedNode);
        }
        
        console.log(`✅ Processed ${processedNodes.length} nodes, allNodesValid: ${allNodesValid}`);

        if (allNodesValid) {
          // Process edges with updated node IDs
          const nodeIdMapping = new Map();
          flowUpdate.nodes.forEach((originalNode, index) => {
            nodeIdMapping.set(originalNode.id, processedNodes[index].id);
          });
          
          const processedEdges = flowUpdate.edges.map(edge => ({
            ...edge,
            id: `edge-${nanoid(6)}`, // Generate unique edge ID
            source: nodeIdMapping.get(edge.source) || edge.source,
            target: nodeIdMapping.get(edge.target) || edge.target,
          }));
          
          // MERGE with existing nodes/edges instead of replacing
          const mergedNodes = [...existingNodes, ...processedNodes];
          const mergedEdges = [...existingEdges, ...processedEdges];
          
          // Merge nodes and edges
          console.log("🎯 Merged flow:", `+${processedNodes.length} nodes, +${processedEdges.length} edges`);
          
          set({ nodes: mergedNodes, edges: mergedEdges });
          
          // Apply auto-layout to newly added nodes
          setTimeout(() => {
            console.log("🎯 Applying auto-layout...");
            
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
              mergedNodes, 
              mergedEdges, 
              LAYOUT_DIRECTIONS.LEFT_TO_RIGHT
            );
            
            set({ nodes: layoutedNodes, edges: layoutedEdges });
            console.log("✅ Auto-layout applied successfully");
          }, 100);
          
          // Verify state update
          const stateAfterSet = get();
          console.log("📊 Flow state:", `${stateAfterSet.nodes.length} nodes, ${stateAfterSet.edges.length} edges`);
          
          addChatMessage('bot', `✅ Added ${processedNodes.length} nodes and ${processedEdges.length} edges to canvas!`, 'info');
          console.log("✅ SUCCESS MESSAGE ADDED TO CHAT");
        } else {
          console.error("❌ NODE VALIDATION FAILED");
          addChatMessage('bot', "(⚠️ Chatbot proposed a flow with unknown component types. Update aborted.)", 'error');
          console.warn("❌ Invalid node types found:", flowUpdate.nodes.map(n => n.type));
          console.warn("❌ Available types:", Array.from(componentTypeMap.keys()));
        }
      } else if (Object.prototype.hasOwnProperty.call(responseData, 'flow_update') && flowUpdate !== null) {
        console.error("❌ INVALID FLOW STRUCTURE:", {
          hasFlowUpdate: !!flowUpdate,
          isNodesArray: Array.isArray(flowUpdate?.nodes),
          isEdgesArray: Array.isArray(flowUpdate?.edges),
          flowUpdate
        });
        addChatMessage('bot', "(❌ Chatbot returned an invalid flow structure)", 'error');
      } else {
        console.log("ℹ️ No flow update in response - normal conversational response");
      }

      console.log("🏁 RETURNING RESPONSE DATA:", responseData);
      // Return the response data for TerminalPanel
      return responseData;
    } catch (error) {
      console.error("💥 EXCEPTION CAUGHT IN sendChatMessageToFlowBuilder:", error);
      console.error("💥 Error details:", {
        message: error.message,
        response: error.response,
        request: error.request,
        stack: error.stack
      });
      
      let errorMessage = "Failed to get response from chatbot flow builder.";
      if (error.response) {
        console.error("💥 Backend error response:", error.response.data);
        errorMessage = `Chatbot Builder Error (${error.response.status}): ${error.response.data?.error || error.response.data?.reply || 'Unknown backend error'}`;
      } else if (error.request) {
        console.error("💥 Network error - no response received");
        errorMessage = "Network Error: Could not connect to the chatbot flow builder backend.";
      } else {
        console.error("💥 Request setup error");
        errorMessage = `Request Error: ${error.message}`;
      }
      addChatMessage('bot', errorMessage, 'error');
      
      // Return error response for TerminalPanel
      return { reply: errorMessage, flow_update: null };
    } finally {
      console.log("🔄 FINALLY: Setting loading to false");
      set({ isChatbotLoading: false });
      console.log("🏁 sendChatMessageToFlowBuilder COMPLETE");
    }
  },

  // === Model Configuration Management ===
  models: [],
  defaultModelId: 'default',
  
  fetchModels: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/models`);
      set({ 
        models: response.data.models,
        defaultModelId: response.data.models.find(m => m.is_default)?.id || 'default'
      });
    } catch (error) {
      console.error("Error fetching models:", error);
    }
  },

  addModel: async (modelConfig) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/models`, modelConfig);
      const newModel = response.data.model;
      set((state) => ({ models: [...state.models, newModel] }));
      return newModel;
    } catch (error) {
      console.error("Error adding model:", error);
      throw error;
    }
  },

  deleteModel: async (modelId) => {
    try {
      await axios.delete(`${API_BASE_URL}/models/${modelId}`);
      set((state) => ({ 
        models: state.models.filter(m => m.id !== modelId) 
      }));
    } catch (error) {
      console.error("Error deleting model:", error);
      throw error;
    }
  },

  setDefaultModel: async (modelId) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/models/${modelId}/default`);
      set((state) => ({
        models: state.models.map(m => ({ ...m, is_default: m.id === modelId })),
        defaultModelId: modelId
      }));
      return response.data.model;
    } catch (error) {
      console.error("Error setting default model:", error);
      throw error;
    }
  },
}));

// Persist projects & currentProjectId with debouncing
useStore.subscribe(
  (state) => ({
    projects: state.projects,
    currentProjectId: state.currentProjectId,
  }),
  (currentState) => {
    if (currentState.projects && currentState.currentProjectId) {
      debouncedSaveProjects(currentState.projects);
      saveState('tframexStudioCurrentProject', currentState.currentProjectId);
    }
  },
  { fireImmediately: false }
);

// Initial load of components and models
useStore.getState().fetchTFrameXComponents();
useStore.getState().fetchModels();