# Agent-Builder for TFrameX v1.1.0

![TFrameX Agent Builder](https://github.com/user-attachments/assets/d29608da-1218-4628-bb49-ba5a943beffc)

<p align="center">
  <strong>Visual agent builder for TFrameX - Create sophisticated LLM agents and workflows with a drag-and-drop interface.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/tframex/">
    <img src="https://img.shields.io/badge/TFrameX-v1.1.0-blue.svg" alt="TFrameX version">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  </a>
  <a href="https://github.com/TesslateAI/Agent-Builder">
    <img src="https://img.shields.io/badge/github-Agent--Builder-orange.svg" alt="GitHub">
  </a>
</p>

---

**Agent-Builder** is a powerful visual development environment for [TFrameX v1.1.0](https://github.com/TesslateAI/TFrameX), the extensible task & flow orchestration framework for LLMs. Build, test, and deploy sophisticated multi-agent systems with enterprise-grade features.

![Animation](https://github.com/user-attachments/assets/829692a1-6fa1-41e1-8c59-98f4a9cffedd)

## ✨ Features

### Core Features
- 🎨 **Visual Flow Designer**: Drag-and-drop interface powered by ReactFlow
- 🤖 **TFrameX 1.1.0 Integration**: Full support for all v1.1.0 features
- 🔌 **MCP Support**: Model Context Protocol integration for external services
- 🚀 **Production Ready**: Optimized build process with Docker support
- 🛠️ **Dynamic Code Registration**: Add agents and tools on the fly
- 📊 **Enterprise Features**: Authentication, RBAC, metrics, and audit logging ready

### TFrameX v1.1.0 Features
- **Enhanced Agents**: LLMAgent, ToolAgent with strip_think_tags support
- **MCP Integration**: Connect to external services via MCP servers
- **Improved APIs**: Modern async/await patterns throughout
- **Multi-LLM Support**: OpenAI, Anthropic, Ollama, and more
- **Enterprise Ready**: Metrics, storage backends, session management
- **CLI Integration**: Compatible with `tframex` CLI tools

### Visual Builder Features
- **Component Palette**: All TFrameX components available to drag and drop
- **Pattern Support**: Sequential, Parallel, Router, and Discussion patterns
- **Agent-as-Tool**: Visual connections for agent delegation
- **Properties Panel**: Fine-tune every aspect of agents and tools
- **Real-time Execution**: See results and logs immediately
- **AI Assistant**: Natural language flow building helper
- **Project Management**: Save and load flow designs

## 🚀 Quick Start

### For Local TFrameX Development

If you have TFrameX cloned locally (recommended for now):

```bash
# Make sure TFrameX is in the parent directory
cd /path/to/parent
git clone https://github.com/TesslateAI/TFrameX.git
git clone https://github.com/TesslateAI/Agent-Builder.git
cd Agent-Builder

# Use the development start script
./start-dev.sh
```

### Standard Installation

When TFrameX 1.1.0 is published to PyPI:

```bash
git clone https://github.com/TesslateAI/Agent-Builder.git
cd Agent-Builder
./start.sh
```

The application will be available at **http://localhost:5000**

### Alternative Installation Methods

#### Using Make
```bash
make install     # Install dependencies and build
make run         # Run in production mode
# OR
make run-dev     # Run with hot reload for development
```

#### Using Docker
```bash
docker build -t agent-builder .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key agent-builder
```

#### Manual Setup with uv
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up environment
uv venv
source .venv/bin/activate
uv pip install -e .

# Build frontend
cd builder/frontend && npm install && npm run build
cd ../..

# Run
cd builder/backend && python app.py
```
    *   Customize an agent's system prompt or its list of enabled tools.
    *   Define parameters for patterns (e.g., which agent is the router in a `RouterPattern`).
    *   Set the content for a `Text Input` node.
4.  **Extend (Optional):** Use the **Add Code** tab in the sidebar to register new TFrameX agents or tools by pasting Python code. They'll appear in the "Components" tab.
5.  **AI Assist (Optional):** Use the **AI Flow Builder** chat to describe changes or additions to your flow, and let the AI attempt to update the canvas.
6.  **Run:** Click the "Run Flow" button in the Top Bar to execute your entire visual flow.
7.  **Iterate:** Observe the results in the **Output Panel**, refine your design, and run again!

## 📋 Prerequisites

*   **Python 3.8+**
*   **TFrameX Library:** Ensure TFrameX is installed in your Python environment.
    ```bash
    pip install tframex
    ```
*   **Node.js and npm (or yarn):** Required for the frontend.
*   **LLM API Access:** An OpenAI-compatible API endpoint (e.g., a local Ollama instance, vLLM, etc).
*   **Environment Variables:** Your backend needs to know how to connect to your LLM. See "Backend Setup" below.

## 🚀 Getting Started

Follow these steps to get Tesslate Studio up and running:

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Backend Setup (Flask & TFrameX):**
    *   Navigate to the backend directory: `cd builder/backend`
    *   Create and activate a Python virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows: venv\Scripts\activate
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   **Configure your LLM:**
        *   Copy the example environment file: `cp deploy/docker/.env.example deploy/docker/.env`
        *   Edit the `deploy/docker/.env` file with your LLM details. Example for local Ollama:
            ```env
            OPENAI_API_BASE="http://localhost:11434/v1"
            OPENAI_API_KEY="ollama" # Placeholder for Ollama
            OPENAI_MODEL_NAME="llama3" # Your preferred model
            ```
            For OpenAI API:
            ```env
            # OPENAI_API_KEY="your_actual_openai_api_key"
            # OPENAI_MODEL_NAME="gpt-3.5-turbo"
            # OPENAI_API_BASE="https://api.openai.com/v1" # (Often default)
            ```
    *   Run the backend server:
        ```bash
        python app.py
        ```
        The backend will typically start on `http://127.0.0.1:5001`.

3.  **Frontend Setup (React & Vite):**
    *   Open a new terminal.
    *   Navigate to the frontend directory: `cd builder/frontend`
    *   Install Node.js dependencies:
        ```bash
        npm install
        # or if you use yarn:
        # yarn install
        ```
    *   Run the frontend development server:
        ```bash
        npm run dev
        # or
        # yarn dev
        ```
        The frontend will typically start on `http://localhost:5173`.

4.  **Access Tesslate Studio:**
    Open your web browser and navigate to the frontend URL (e.g., `http://localhost:5173`).

## 🧭 Exploring the Interface

*   **Top Bar:**
    *   **Logo & Title:** "Tesslate Studio".
    *   **Project Management:** Select, create, save, or delete your visual flow projects.
    *   **Run Flow Button:** The primary button to execute the current visual flow on the canvas.

*   **Left Sidebar (Tabs):**
    *   **Components:** A palette of draggable TFrameX components:
        *   **Agents:** Your defined `LLMAgent`s, `ToolAgent`s.
        *   **Patterns:** `SequentialPattern`, `ParallelPattern`, `RouterPattern`, `DiscussionPattern`.
        *   **Tools:** Your registered TFrameX tools.
        *   **Utility:** Nodes like `Text Input` to feed initial data into your flows.
    *   **AI Flow Builder:** A chat interface to get AI assistance. Describe what you want to build or modify, and the AI will attempt to generate the ReactFlow JSON to update your canvas.
    *   **Add Code:** A panel where you can paste Python code defining new TFrameX agents or tools (using `@tframex_app.agent(...)` or `@tframex_app.tool(...)`). Successful registration makes them available in the "Components" tab.

*   **Main Canvas:** This is your workspace! A ReactFlow powered area where you drag components from the palette, connect their handles to define relationships, and arrange your visual flow.

*   **Right Panel (Tabs):**
    *   **Output:** Displays detailed logs and the final result from TFrameX when you run a flow. If your flow generates files (e.g., using a tool), preview links might appear here.
    *   **Properties:** This panel becomes active when you select a node on the canvas. It provides contextual options to configure the selected node:
        *   **Agent Nodes:** Edit display label, override the system prompt, manage which tools are enabled (tools are enabled by connecting them to the agent's dedicated tool input handle), toggle `strip_think_tags`, and configure template variables for the system prompt. A blue dot indicator shows if an agent's configuration is modified from its base TFrameX definition.
        *   **Pattern Nodes:** Edit display label and configure all necessary parameters for the specific pattern (e.g., list of agent/pattern names for `SequentialPattern`'s `steps`, the router agent for `RouterPattern`). Agent/Pattern parameters are often set by connecting other nodes to the pattern's input handles or by selecting from dropdowns.
        *   **Text Input Node:** Set the text content that this node will output.
        *   **Tool Nodes:** Primarily informational, showing the tool's name and description. Tools are "enabled" for agents by connecting the tool's attachment handle to an agent's tool input handle.

## 🔧 Key Features in Detail

### Visual Flow Construction
Drag components onto the canvas and connect their handles. Handles are color-coded or styled to indicate their purpose:
*   **Blue Handles (typically):** Standard message/data flow between agents and patterns.
*   **Purple Handles (on Tools/Agents):** Connect a Tool node to an Agent node to enable that tool for the agent.
*   **Amber Handles (on Patterns):** Connect an Agent or another Pattern to a Pattern's specific parameter input (e.g., assigning a `RouterAgent` to a `RouterPattern`).
*   **Green Handles (on Patterns):** Connect Agents to list-based parameters of a Pattern (e.g., adding agents to a `DiscussionPattern`'s participants).
*   Edges are styled (solid, dashed, animated) to visually differentiate connection types.

### Dynamic Code Registration
The "Add Code" tab allows you to paste Python code snippets that define new TFrameX agents or tools.
*   **Important:** Your code *must* use the globally available `tframex_app` instance for decorators (e.g., `@tframex_app.agent(...)`).
*   The backend executes this code, registering the new components with the running TFrameX application.
*   Upon successful registration, the new components will appear in the "Components" palette, ready to be used.

### AI Flow Builder
Chat with an AI assistant to help build your flows.
*   The AI considers your text prompt, the list of available TFrameX components, and the current state of your visual flow on the canvas.
*   It attempts to generate a new ReactFlow JSON structure (nodes and edges) that you can apply to your canvas.

### Execution and Overrides
When you click "Run Flow":
1.  The frontend sends the current visual graph (nodes and edges) to the backend.
2.  The backend's `flow_translator.py` intelligently converts this visual representation into an executable `tframex.Flow` object.
3.  **Important:** Agent configurations made in the Studio's Properties Panel (like system prompt overrides or specific tool selections for a node) are applied as *temporary overrides* for that specific agent instance *within that run*. This means your base TFrameX agent definitions (in your Python code) are not permanently altered by the Studio unless you explicitly re-register them via the "Add Code" panel. This allows for flexible experimentation in the UI.

## 🔗 How Tesslate Studio Works with TFrameX

*   **Studio as the Conductor:** Tesslate Studio acts as the visual conductor, allowing you to define *how* TFrameX components interact.
*   **TFrameX as the Orchestra:** TFrameX is the underlying engine that provides the agents, tools, patterns, and executes the actual LLM calls and logic.
*   **Translation Layer:** The backend of Tesslate Studio (specifically `flow_translator.py` and `component_manager.py`) is responsible for:
    *   Discovering agents, tools, and patterns from your TFrameX application.
    *   Translating the visual graph from the frontend into a TFrameX `Flow` object.
    *   Managing temporary, run-specific configurations for agents based on your UI settings.
    *   Dynamically registering new Python-defined components into the TFrameX application.

## 💻 Tech Stack

*   **Frontend:** React, Vite, ReactFlow, Zustand, Tailwind CSS, shadcn/ui
*   **Backend:** Flask, TFrameX

## 🤝 Contributing

Contributions are highly welcome! Whether it's bug reports, feature requests, documentation improvements, or code contributions, we'd love to see how you can help make Tesslate Studio even better.

Please feel free to open an issue to discuss your ideas or submit a pull request.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
