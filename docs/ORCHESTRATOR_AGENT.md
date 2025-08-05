# OrchestratorAgent Implementation Guide

The OrchestratorAgent is a sophisticated flow coordination agent that provides intelligent assistance for building and optimizing TFrameX workflows. It leverages specialized tools for flow analysis, component prediction, and optimization suggestions.

## Overview

The OrchestratorAgent extends the existing Agent-Builder architecture by adding:

- **Flow Structure Analysis**: Deep analysis of current flow topology and patterns
- **Component Prediction**: AI-powered suggestions for next components to add
- **Flow Optimization**: Performance and maintainability improvement recommendations
- **Tool Integration**: Uses specialized flow analysis tools for data-driven insights

## Architecture

### Agent Configuration

The OrchestratorAgent is configured in `builder/backend/tframex_config.py`:

```python
@tframex_app_instance.agent(
    name="OrchestratorAgent",
    description="Coordinates flow building activities with tool calling for analysis, prediction, and optimization.",
    system_prompt=orchestrator_agent_prompt,
    strip_think_tags=True,
    can_use_tools=True,
    tool_names=["Flow Structure Analyzer", "Drag-Drop Predictor", "Flow Optimizer", "Math Calculator", "Text Pattern Matcher"]
)
```

### Available Tools

The agent has access to three specialized flow analysis tools:

1. **Flow Structure Analyzer**: Analyzes flow topology, detects patterns, identifies issues
2. **Drag-Drop Predictor**: Predicts optimal next components based on current state and user intent
3. **Flow Optimizer**: Suggests improvements for performance, maintainability, and reliability

## API Endpoints

### 1. Flow Analysis
**Endpoint**: `POST /api/tframex/orchestrator/analyze`

Analyzes the current flow structure and provides insights.

```javascript
const response = await fetch('/api/tframex/orchestrator/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nodes: currentNodes,
    edges: currentEdges,
    request: 'Analyze this flow for potential improvements'
  })
});

const result = await response.json();
// result.analysis contains detailed analysis
```

### 2. Component Prediction
**Endpoint**: `POST /api/tframex/orchestrator/predict`

Predicts what components should be added next to the flow.

```javascript
const response = await fetch('/api/tframex/orchestrator/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nodes: currentNodes,
    edges: currentEdges,
    intent: 'I want to process files and calculate statistics'
  })
});

const result = await response.json();
// result.predictions contains suggested components
```

### 3. Flow Optimization
**Endpoint**: `POST /api/tframex/orchestrator/optimize`

Provides optimization suggestions for existing flows.

```javascript
const response = await fetch('/api/tframex/orchestrator/optimize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nodes: currentNodes,
    edges: currentEdges,
    goals: ['performance', 'maintainability', 'reliability']
  })
});

const result = await response.json();
// result.optimizations contains improvement suggestions
```

### 4. Agent Testing
**Endpoint**: `POST /api/tframex/orchestrator/test`

Tests basic OrchestratorAgent functionality.

```javascript
const response = await fetch('/api/tframex/orchestrator/test', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Test the flow analysis tools'
  })
});

const result = await response.json();
// result.success and result.response
```

## Usage Examples

### React Component Integration

Here's an example of how to integrate the OrchestratorAgent into a React component:

```jsx
import React, { useState } from 'react';
import { useStore } from '../store';

const FlowOrchestrator = () => {
  const nodes = useStore((state) => state.nodes);
  const edges = useStore((state) => state.edges);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeFlow = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/tframex/orchestrator/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes,
          edges,
          request: 'Analyze current flow structure and suggest improvements'
        })
      });
      
      const result = await response.json();
      setAnalysis(result.analysis);
    } catch (error) {
      console.error('Flow analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const predictNext = async (intent) => {
    setLoading(true);
    try {
      const response = await fetch('/api/tframex/orchestrator/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes,
          edges,
          intent
        })
      });
      
      const result = await response.json();
      return result.predictions;
    } catch (error) {
      console.error('Prediction failed:', error);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flow-orchestrator">
      <button onClick={analyzeFlow} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze Flow'}
      </button>
      
      <button onClick={() => predictNext('add file processing capabilities')}>
        Suggest Next Components
      </button>
      
      {analysis && (
        <div className="analysis-results">
          <h3>Flow Analysis</h3>
          <pre>{analysis}</pre>
        </div>
      )}
    </div>
  );
};

export default FlowOrchestrator;
```

### Integration with Existing Chat Interface

The OrchestratorAgent can be integrated with the existing chat interface by adding orchestrator-specific prompts:

```javascript
// In your chat handler
const sendOrchestratorMessage = async (message, action = 'analyze') => {
  const endpoint = `/api/tframex/orchestrator/${action}`;
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nodes: getCurrentNodes(),
      edges: getCurrentEdges(),
      request: message,
      intent: message  // for predict endpoint
    })
  });
  
  return await response.json();
};
```

## Flow Analysis Tools Details

### Flow Structure Analyzer

The Flow Structure Analyzer provides:

- **Node Type Analysis**: Counts and categorizes different node types
- **Pattern Detection**: Identifies common flow patterns (sequential chains, parallel branches)
- **Issue Detection**: Finds isolated nodes, circular dependencies, unconnected tools
- **Best Practice Suggestions**: Recommends improvements based on flow topology

### Drag-Drop Predictor

The Drag-Drop Predictor offers:

- **Priority-Based Recommendations**: High, medium, and low priority suggestions
- **Intent-Aware Predictions**: Considers user intent and context
- **Component Validation**: Ensures suggested components are available and compatible
- **Workflow Continuation**: Suggests logical next steps in workflow development

### Flow Optimizer

The Flow Optimizer provides:

- **Performance Improvements**: Suggests patterns and optimizations for better execution
- **Structural Improvements**: Recommends breaking long chains, adding coordination patterns
- **Best Practices**: Ensures error handling, input validation, and maintainability
- **Goal-Oriented Optimization**: Customizable optimization based on specific goals

## Development Notes

### Adding New Tools

To add new tools for the OrchestratorAgent:

1. Create the tool in `builder/backend/builtin_tools/flow_analysis.py`
2. Update the tool registration count
3. Add the tool name to the OrchestratorAgent's `tool_names` list in `tframex_config.py`

### Extending Analysis Capabilities

The flow analysis tools can be extended with:

- **Performance Metrics**: Add timing and resource usage analysis
- **Security Analysis**: Detect potential security issues in flows
- **Compliance Checking**: Ensure flows meet organizational standards
- **Cost Optimization**: Suggest ways to reduce computational costs

### Error Handling

All orchestrator endpoints include comprehensive error handling:

- **Agent Registration Checks**: Ensures OrchestratorAgent is properly registered
- **Input Validation**: Validates node and edge data before processing
- **Tool Execution Monitoring**: Handles tool execution failures gracefully
- **Detailed Logging**: Provides debugging information for troubleshooting

## Testing

### Basic Functionality Test

```bash
curl -X POST http://localhost:5000/api/tframex/orchestrator/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test OrchestratorAgent functionality"}'
```

### Flow Analysis Test

```bash
curl -X POST http://localhost:5000/api/tframex/orchestrator/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [{"id": "1", "type": "ConversationalAssistant", "data": {"component_category": "agent"}}],
    "edges": [],
    "request": "Analyze this simple flow"
  }'
```

## Future Enhancements

Potential improvements for the OrchestratorAgent:

1. **Machine Learning Integration**: Learn from user patterns to improve predictions
2. **Template Suggestions**: Recommend pre-built flow templates
3. **Collaborative Features**: Multi-user flow building coordination
4. **Integration Testing**: Automated flow validation and testing
5. **Performance Monitoring**: Real-time flow execution monitoring and optimization

## Troubleshooting

### Common Issues

1. **Agent Not Registered**: Ensure OrchestratorAgent is properly registered in `tframex_config.py`
2. **Tool Execution Failures**: Check that flow analysis tools are correctly imported
3. **API Endpoint Errors**: Verify that the chatbot blueprint is properly registered
4. **Missing Dependencies**: Ensure all required dependencies are installed

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
logging.getLogger("ChatbotAPI").setLevel(logging.DEBUG)
logging.getLogger("FlowTranslator").setLevel(logging.DEBUG)
```

## Conclusion

The OrchestratorAgent provides a powerful foundation for intelligent flow building assistance. By leveraging specialized tools and AI-driven analysis, it enables users to create more effective and optimized TFrameX workflows with guided assistance throughout the development process.