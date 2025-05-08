// src/store.js
import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  // addEdge, // Keep addEdge if needed elsewhere (not used directly in store logic provided)
} from 'reactflow';
import { nanoid } from 'nanoid'; // For unique IDs
import axios from 'axios'; // Import axios

// --- Persistence Helpers ---
// Helper function to load state from localStorage
const loadState = (key) => {
  try {
    const serializedState = localStorage.getItem(key);
    if (serializedState === null) {
      return undefined; // No state saved
    }
    return JSON.parse(serializedState);
  } catch (err) {
    console.error("Could not load state from localStorage", err);
    return undefined;
  }
};

// Helper function to save state to localStorage
const saveState = (key, state) => {
  try {
    const serializedState = JSON.stringify(state);
    localStorage.setItem(key, serializedState);
  } catch (err) {
    console.error("Could not save state to localStorage", err);
  }
};


// --- Initial Project Data ---
// Placeholders for example content - load or define appropriately
const exampleContextContent = `The user is interested in Python programming best practices, especially regarding code cleanliness, performance, and concurrency. They are working with potentially large codebases and interacting with external APIs.`; // Replace with actual context.txt content or fetch mechanism

const exampleLongTextContent = `Python is dynamically typed, which offers flexibility but can lead to runtime errors if not carefully managed. This means variables can change type during execution. Static analysis tools like MyPy help mitigate this by adding optional type hints (PEP 484) and checking them before runtime, catching potential type errors early in the development cycle. This improves code reliability and maintainability, especially in larger projects.

Another key aspect is its extensive standard library, often called "batteries included". It covers areas from web protocols (HTTP, email) to GUI development (Tkinter), data processing (CSV, JSON, XML), operating system interfaces, and more. This reduces the need for external packages for common tasks.

The Global Interpreter Lock (GIL) in CPython, the most common Python implementation, is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecode simultaneously within a single process. While it simplifies memory management (making C extensions easier to write), it can limit the performance of CPU-bound multithreaded programs on multi-core processors, as only one thread runs Python code at a time. However, it doesn't significantly impact I/O-bound tasks, where threads spend most of their time waiting for external operations (like network requests or disk reads).

Asynchronous programming with the \`asyncio\` library provides concurrency for I/O-bound tasks without needing multiple OS threads. It uses an event loop and \`async\`/\`await\` syntax to manage coroutines, allowing the program to switch between tasks when one is waiting for I/O, leading to efficient handling of many concurrent connections or operations. This is particularly useful for web servers, network clients, and applications involving significant waiting time. Libraries like \`aiohttp\` build upon asyncio for asynchronous web development.`; // Replace with actual longtext.txt content or fetch mechanism


const initialProjects = {
  'example1': {
    name: "Example 1: Basic Agent",
    nodes: [
      { id: 'basic-1', type: 'basicAgent', position: { x: 100, y: 100 }, data: { label: 'Basic Agent', prompt: 'Explain the difference between synchronous and asynchronous programming using a simple analogy.', maxTokens: 300 } },
    ],
    edges: [],
  },
  'example2': {
    name: "Example 2: Context Agent",
    nodes: [
      { id: 'context-1', type: 'contextAgent', position: { x: 100, y: 100 }, data: { label: 'Context Agent', context: exampleContextContent, prompt: 'What are 3 key recommendations for writing clean Python code based on the context?' } },
    ],
    edges: [],
  },
  'example3': {
    name: "Example 3: Chain of Agents",
    nodes: [
      { id: 'chain-1', type: 'chainOfAgents', position: { x: 100, y: 100 }, data: { label: 'Chain Summarizer', initialPrompt: "Based on the provided text, explain the implications of Python's dynamic typing and the GIL.", longText: exampleLongTextContent, chunkSize: 2000, chunkOverlap: 200, maxTokens: 500 } },
    ],
    edges: [],
  },
   'example4': {
    name: "Example 4: Multi Call System",
    nodes: [
      { id: 'multi-1', type: 'multiCallSystem', position: { x: 100, y: 100 }, data: { label: 'Website Generator', prompt: 'Make the best looking website for a html css js tailwind coffee shop landing page.', numCalls: 5, baseFilename: 'website_call', maxTokens: 35000, outputDir: 'example_outputs/ex4_multi_call_outputs' } },
    ],
    edges: [],
  },
  // 'example5': Removed Software Builder as per first file's comments
  'new_project': {
      name: "New Project",
      nodes: [],
      edges: [],
  }
};

const savedProjects = loadState('reactFlowProjects') || initialProjects;
const initialProjectId = loadState('reactFlowCurrentProject') || 'example1'; // Default to first example

export const useStore = create((set, get) => ({
  // === React Flow State ===
  nodes: savedProjects[initialProjectId]?.nodes || [],
  edges: savedProjects[initialProjectId]?.edges || [],
  onNodesChange: (changes) => {
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) }));
  },
  onEdgesChange: (changes) => {
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges) }));
  },
  addNode: (newNode) => {
    set((state) => ({ nodes: [...state.nodes, newNode] }));
  },
  setNodes: (nodes) => {
    set({ nodes });
  },
  setEdges: (edges) => {
    set({ edges });
  },
  // Update data within a specific node
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
        // saveState('reactFlowProjects', updatedProjects); // Persisted via subscribe
        console.log(`Project '${currentProject.name}' saved.`);
    }
  },

  loadProject: (projectId) => {
    const { projects, saveCurrentProject } = get();
    const projectToLoad = projects[projectId];

    if (projectToLoad) {
      // Save the current state before switching
      saveCurrentProject();
      set({
        nodes: projectToLoad.nodes || [],
        edges: projectToLoad.edges || [],
        currentProjectId: projectId,
        output: "Output will appear here...", // Clear output on load
        chatHistory: [], // Clear chat history on load
      });
      // saveState('reactFlowCurrentProject', projectId); // Persisted via subscribe
      console.log(`Project '${projectToLoad.name}' loaded.`);
    } else {
        console.warn(`Project with ID ${projectId} not found.`);
    }
  },

  createProject: (name) => {
    const { projects, saveCurrentProject } = get();
    // Save the current state before creating
    saveCurrentProject();

    const newProjectId = `project_${nanoid(8)}`;
    const newProject = {
        name: name || `New Project ${Object.keys(projects).length + 1}`,
        nodes: [],
        edges: []
    };
    const updatedProjects = { ...projects, [newProjectId]: newProject };
    set({
        projects: updatedProjects,
        nodes: [], // Clear canvas for new project
        edges: [],
        currentProjectId: newProjectId,
        output: "Output will appear here...", // Clear output
        chatHistory: [], // Clear chat history
    });
    // saveState('reactFlowProjects', updatedProjects); // Persisted via subscribe
    // saveState('reactFlowCurrentProject', newProjectId); // Persisted via subscribe
    console.log(`Project '${newProject.name}' created.`);
  },

  deleteProject: (projectId) => {
      const { projects, currentProjectId, loadProject } = get();
      if (!projects[projectId]) return;
      if (Object.keys(projects).length <= 1) {
          alert("Cannot delete the last project.");
          return; // Don't delete the last project
      }
       if (!confirm(`Are you sure you want to delete project "${projects[projectId].name}"? This cannot be undone.`)) {
           return;
       }

      const updatedProjects = { ...projects };
      delete updatedProjects[projectId];

      // If deleting the current project, load another one (e.g., the first available)
      let nextProjectId = currentProjectId;
      if (currentProjectId === projectId) {
          nextProjectId = Object.keys(updatedProjects)[0];
      }

      set({ projects: updatedProjects });
      // saveState('reactFlowProjects', updatedProjects); // Persisted via subscribe

      // Load the next project AFTER state is updated
       if (currentProjectId === projectId) {
           loadProject(nextProjectId); // loadProject will handle setting currentProjectId and persisting
       } else {
           // If we deleted a non-current project, just save the updated projects list
           saveState('reactFlowProjects', updatedProjects);
       }

      console.log(`Project "${projects[projectId].name}" deleted.`);
  },


  // === Execution State ===
  output: "Output will appear here...",
  isRunning: false,
  runFlow: async () => {
    const { nodes, edges, saveCurrentProject } = get();
     // Save before running
    saveCurrentProject();

    set({ isRunning: true, output: "Executing flow..." });
    console.log("Sending to backend:", { nodes, edges });

    try {
      // Use the correct backend URL (ensure backend runs on port 5001 or change here)
      const response = await axios.post('http://localhost:5001/api/run', { nodes, edges });
      console.log("Received from backend:", response.data);
      set({ output: response.data.output || "Execution finished, but no output received." });
    } catch (error) {
      console.error("Error running flow:", error);
      let errorMessage = "Failed to run flow.";
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error("Backend Error Data:", error.response.data);
        console.error("Backend Error Status:", error.response.status);
        errorMessage = `Backend Error (${error.response.status}): ${error.response.data?.error || 'Unknown error'}`;
      } else if (error.request) {
        // The request was made but no response was received
        console.error("No response received:", error.request);
        errorMessage = "Network Error: Could not connect to the backend. Is it running?";
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Error', error.message);
        errorMessage = `Request Error: ${error.message}`;
      }
      set({ output: errorMessage });
    } finally {
      set({ isRunning: false });
    }
  },
  clearOutput: () => {
      set({ output: "" });
  },

  // === Agent Definitions State (NEW from first file) ===
  agentDefinitions: [], // Store fetched definitions
  isDefinitionLoading: false,
  definitionError: null,
  fetchAgentDefinitions: async () => {
      if (get().isDefinitionLoading) return; // Prevent concurrent fetches
      set({ isDefinitionLoading: true, definitionError: null });
      try {
          // Ensure backend is running on 5001 or update URL
          const response = await axios.get('http://localhost:5001/api/agents');
          if (response.data && Array.isArray(response.data)) {
              console.log("Fetched agent definitions:", response.data);
              set({ agentDefinitions: response.data, isDefinitionLoading: false });
          } else {
              throw new Error("Invalid response format from server.");
          }
      } catch (err) {
          console.error("Failed to fetch agent definitions:", err);
          set({
              definitionError: "Could not load nodes. Is the backend running on port 5001?",
              agentDefinitions: [],
              isDefinitionLoading: false
          });
      }
  },

  // === Chatbot State (NEW from first file) ===
  chatHistory: [], // Array of { sender: 'user' | 'bot', message: string, type?: 'error' | 'normal' }
  isChatbotLoading: false,
  addChatMessage: (sender, message, type = 'normal') => {
    set((state) => ({
      // Limit history length if desired
      chatHistory: [...state.chatHistory, { sender, message, type }] //.slice(-50)
    }));
  },
  clearChatHistory: () => set({ chatHistory: [] }),
  sendChatMessage: async (userMessage) => {
      const { nodes, edges, agentDefinitions, addChatMessage } = get();

      if (!userMessage.trim()) return; // Don't send empty messages

      // Add user message immediately
      addChatMessage('user', userMessage);
      set({ isChatbotLoading: true });

      try {
          const backendUrl = 'http://localhost:5001/api/chatbot'; // Ensure correct port
          const payload = {
              message: userMessage,
              nodes: nodes,
              edges: edges,
              // Send definitions the backend expects (check backend endpoint)
              // Assuming it needs the same format as /api/agents returns
              definitions: agentDefinitions
          };
          console.log("Sending to chatbot:", payload);

          const response = await axios.post(backendUrl, payload);
          console.log("Received from chatbot:", response.data);

          const reply = response.data?.reply || "Received no reply from chatbot.";
          const flowUpdate = response.data?.flow; // Expected: { nodes: [], edges: [] } or null/undefined

          addChatMessage('bot', reply); // Add the main reply first

          // Apply flow update ONLY if it's valid
          if (flowUpdate && Array.isArray(flowUpdate.nodes) && Array.isArray(flowUpdate.edges)) {
              console.log("Chatbot applying flow update:", flowUpdate);
              // Here you might want to add more sophisticated validation
              // e.g., check if node types in flowUpdate.nodes exist in agentDefinitions
              set({ nodes: flowUpdate.nodes, edges: flowUpdate.edges });
              // Optionally add a confirmation message after the main reply
              // addChatMessage('bot', 'Flow updated successfully.', 'info');
          } else if (response.data?.hasOwnProperty('flow') && flowUpdate !== null) {
              // If 'flow' key exists but isn't valid (and not explicitly null)
              console.warn("Chatbot returned an invalid flow update structure:", flowUpdate);
              addChatMessage('bot', "(Received an invalid flow structure from the chatbot)", 'error');
          }
           // If flowUpdate is null or undefined, or invalid, just show the main reply.

      } catch (error) {
          console.error("Error sending chat message:", error);
          let errorMessage = "Failed to get response from chatbot.";
          if (error.response) {
              errorMessage = `Chatbot Error (${error.response.status}): ${error.response.data?.error || error.response.data?.reply || 'Unknown backend error'}`;
          } else if (error.request) {
              errorMessage = "Network Error: Could not connect to the chatbot backend.";
          } else {
              errorMessage = `Request Error: ${error.message}`;
          }
          addChatMessage('bot', errorMessage, 'error'); // Add error message to chat
      } finally {
          set({ isChatbotLoading: false });
      }
  },

}));

// --- Persistence Subscription ---
// Persist changes to projects and the current project ID
useStore.subscribe(
  (state) => ({ projects: state.projects, currentProjectId: state.currentProjectId }),
  (currentState) => {
      if (currentState.projects && currentState.currentProjectId) {
          saveState('reactFlowProjects', currentState.projects);
          saveState('reactFlowCurrentProject', currentState.currentProjectId);
      }
  },
  { fireImmediately: false } // Only save on actual changes after initial load
);

// --- Initial Fetch ---
// Fetch agent definitions when the store is initialized
useStore.getState().fetchAgentDefinitions();