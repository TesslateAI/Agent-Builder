# builder/backend/builtin_tools/flow_analysis.py
"""
Flow analysis tools for the Agent-Builder application.
Provides flow optimization, validation, and prediction capabilities.
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque


def register_flow_analysis_tools(tframex_app):
    """Register flow analysis tools with the TFrameXApp instance."""
    
    @tframex_app.tool(
        name="Flow Structure Analyzer",
        description="Analyze visual flow structure for patterns, issues, and optimization opportunities"
    )
    async def analyze_flow_structure(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze the structure of a visual flow."""
        try:
            analysis = {
                "success": True,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_types": {},
                "patterns": [],
                "issues": [],
                "suggestions": []
            }
            
            # Analyze node types and categories
            node_categories = defaultdict(int)
            agent_nodes = []
            pattern_nodes = []
            tool_nodes = []
            
            for node in nodes:
                node_data = node.get('data', {})
                category = node_data.get('component_category', 'unknown')
                node_categories[category] += 1
                
                if category == 'agent':
                    agent_nodes.append(node)
                elif category == 'pattern':
                    pattern_nodes.append(node)
                elif category == 'tool':
                    tool_nodes.append(node)
            
            analysis["node_types"] = dict(node_categories)
            
            # Build adjacency list for graph analysis
            adj_list = defaultdict(list)
            reverse_adj = defaultdict(list)
            
            for edge in edges:
                source = edge.get('source')
                target = edge.get('target')
                if source and target:
                    adj_list[source].append(target)
                    reverse_adj[target].append(source)
            
            # Detect patterns
            if len(agent_nodes) > 1 and len(pattern_nodes) == 0:
                analysis["patterns"].append("Sequential agent chain detected - consider using SequentialPattern")
            
            if len(agent_nodes) > 2 and any(len(adj_list[node['id']]) > 1 for node in agent_nodes):
                analysis["patterns"].append("Parallel execution detected - consider using ParallelPattern")
            
            # Find potential issues
            # 1. Isolated nodes
            isolated_nodes = []
            for node in nodes:
                node_id = node['id']
                if not adj_list[node_id] and not reverse_adj[node_id]:
                    isolated_nodes.append(node_id)
            
            if isolated_nodes:
                analysis["issues"].append(f"Isolated nodes found: {isolated_nodes}")
            
            # 2. Cycles detection
            def has_cycle():
                visited = set()
                rec_stack = set()
                
                def dfs(node):
                    if node in rec_stack:
                        return True
                    if node in visited:
                        return False
                    
                    visited.add(node)
                    rec_stack.add(node)
                    
                    for neighbor in adj_list[node]:
                        if dfs(neighbor):
                            return True
                    
                    rec_stack.remove(node)
                    return False
                
                for node in adj_list:
                    if node not in visited:
                        if dfs(node):
                            return True
                return False
            
            if has_cycle():
                analysis["issues"].append("Circular dependency detected in flow")
            
            # 3. Unconnected tools
            unconnected_tools = []
            for tool_node in tool_nodes:
                tool_id = tool_node['id']
                # Tools should be connected to agents via purple/tool handles
                connected_to_agent = False
                for edge in edges:
                    if edge.get('source') == tool_id:
                        target_node = next((n for n in nodes if n['id'] == edge['target']), None)
                        if target_node and target_node.get('data', {}).get('component_category') == 'agent':
                            connected_to_agent = True
                            break
                
                if not connected_to_agent:
                    unconnected_tools.append(tool_node.get('data', {}).get('label', tool_id))
            
            if unconnected_tools:
                analysis["issues"].append(f"Tools not connected to agents: {unconnected_tools}")
            
            # Generate suggestions
            if node_categories['agent'] > 0 and node_categories['tool'] == 0:
                analysis["suggestions"].append("Consider adding tools to enhance agent capabilities")
            
            if node_categories['agent'] > 3 and node_categories['pattern'] == 0:
                analysis["suggestions"].append("Complex flow detected - consider using coordination patterns")
            
            if node_categories['pattern'] > 0 and node_categories['agent'] < 2:
                analysis["suggestions"].append("Patterns work best with multiple agents")
            
            return analysis
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Flow analysis error: {str(e)}"
            }
    
    @tframex_app.tool(
        name="Drag-Drop Predictor", 
        description="Predict optimal next components to add to a flow based on current state"
    )
    async def predict_next_components(
        current_nodes: List[Dict[str, Any]],
        current_edges: List[Dict[str, Any]],
        user_intent: str = ""
    ) -> Dict[str, Any]:
        """Predict what components should be added next to the flow."""
        try:
            predictions = {
                "success": True,
                "recommendations": [],
                "priorities": {
                    "high": [],
                    "medium": [], 
                    "low": []
                }
            }
            
            # Analyze current state
            node_categories = defaultdict(int)
            agent_types = set()
            pattern_types = set()
            
            for node in current_nodes:
                data = node.get('data', {})
                category = data.get('component_category', 'unknown')
                node_categories[category] += 1
                
                if category == 'agent':
                    agent_types.add(node.get('type', ''))
                elif category == 'pattern':
                    pattern_types.add(node.get('type', ''))
            
            # High priority predictions
            if node_categories['agent'] == 0:
                predictions["priorities"]["high"].append({
                    "type": "agent",
                    "component": "ConversationalAssistant",
                    "reason": "Every flow needs at least one agent",
                    "category": "agent"
                })
            
            if node_categories['agent'] == 1 and "conversation" in user_intent.lower():
                predictions["priorities"]["high"].append({
                    "type": "agent", 
                    "component": "FlowBuilderAgent",
                    "reason": "Conversational flows often need flow building capabilities",
                    "category": "agent"
                })
            
            # Medium priority predictions
            if node_categories['agent'] > 1 and node_categories['pattern'] == 0:
                if "sequential" in user_intent.lower() or "chain" in user_intent.lower():
                    predictions["priorities"]["medium"].append({
                        "type": "pattern",
                        "component": "SequentialPattern", 
                        "reason": "Sequential execution pattern for agent chain",
                        "category": "pattern"
                    })
                elif "parallel" in user_intent.lower() or "concurrent" in user_intent.lower():
                    predictions["priorities"]["medium"].append({
                        "type": "pattern",
                        "component": "ParallelPattern",
                        "reason": "Parallel execution for concurrent processing", 
                        "category": "pattern"
                    })
                else:
                    predictions["priorities"]["medium"].append({
                        "type": "pattern",
                        "component": "SequentialPattern",
                        "reason": "Coordinate multiple agents with sequential pattern",
                        "category": "pattern"
                    })
            
            if node_categories['agent'] > 0 and node_categories['tool'] == 0:
                tool_suggestions = []
                if "file" in user_intent.lower() or "read" in user_intent.lower():
                    tool_suggestions.append("File Reader")
                if "math" in user_intent.lower() or "calculate" in user_intent.lower():
                    tool_suggestions.append("Math Calculator")
                if "text" in user_intent.lower() or "process" in user_intent.lower():
                    tool_suggestions.append("Text Pattern Matcher")
                if "time" in user_intent.lower() or "date" in user_intent.lower():
                    tool_suggestions.append("Date & Time Tool")
                
                if not tool_suggestions:
                    tool_suggestions = ["File Reader", "Math Calculator"]
                
                for tool in tool_suggestions:
                    predictions["priorities"]["medium"].append({
                        "type": "tool",
                        "component": tool,
                        "reason": f"Enhance agent capabilities with {tool.lower()}",
                        "category": "tool"
                    })
            
            # Low priority predictions
            if node_categories['agent'] > 2 and 'RouterPattern' not in pattern_types:
                predictions["priorities"]["low"].append({
                    "type": "pattern", 
                    "component": "RouterPattern",
                    "reason": "Route requests between multiple agents",
                    "category": "pattern"
                })
            
            if node_categories['agent'] > 2 and 'DiscussionPattern' not in pattern_types:
                predictions["priorities"]["low"].append({
                    "type": "pattern",
                    "component": "DiscussionPattern", 
                    "reason": "Enable multi-agent discussion and collaboration",
                    "category": "pattern"
                })
            
            # Flatten all recommendations
            all_recs = []
            for priority in ["high", "medium", "low"]:
                all_recs.extend(predictions["priorities"][priority])
            predictions["recommendations"] = all_recs
            
            return predictions
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Prediction error: {str(e)}"
            }
    
    @tframex_app.tool(
        name="Flow Optimizer",
        description="Suggest optimizations and improvements for existing flows"
    )
    async def optimize_flow(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        optimization_goals: List[str] = None
    ) -> Dict[str, Any]:
        """Suggest optimizations for a flow."""
        try:
            optimizations = {
                "success": True,
                "optimizations": [],
                "performance_improvements": [],
                "structural_improvements": [],
                "best_practices": []
            }
            
            if optimization_goals is None:
                optimization_goals = ["performance", "maintainability", "reliability"]
            
            # Analyze current structure
            agent_count = sum(1 for n in nodes if n.get('data', {}).get('component_category') == 'agent')
            pattern_count = sum(1 for n in nodes if n.get('data', {}).get('component_category') == 'pattern')
            tool_count = sum(1 for n in nodes if n.get('data', {}).get('component_category') == 'tool')
            
            # Performance optimizations
            if "performance" in optimization_goals:
                if agent_count > 2 and pattern_count == 0:
                    optimizations["performance_improvements"].append({
                        "type": "add_pattern",
                        "description": "Add coordination patterns to reduce sequential bottlenecks",
                        "impact": "high",
                        "suggestion": "Use ParallelPattern for independent tasks or SequentialPattern for dependent tasks"
                    })
                
                if tool_count == 0 and agent_count > 0:
                    optimizations["performance_improvements"].append({
                        "type": "add_tools",
                        "description": "Add specialized tools to reduce agent computational load",
                        "impact": "medium", 
                        "suggestion": "Connect relevant tools to agents for specific operations"
                    })
            
            # Structural improvements
            if "maintainability" in optimization_goals:
                # Check for long sequential chains
                chain_length = 0
                for node in nodes:
                    if node.get('data', {}).get('component_category') == 'agent':
                        outgoing = sum(1 for e in edges if e.get('source') == node['id'])
                        if outgoing == 1:
                            chain_length += 1
                
                if chain_length > 3:
                    optimizations["structural_improvements"].append({
                        "type": "break_chain",
                        "description": f"Long sequential chain detected ({chain_length} agents)",
                        "impact": "medium",
                        "suggestion": "Consider breaking into smaller logical groups with patterns"
                    })
            
            # Best practices
            if "reliability" in optimization_goals:
                # Check for error handling
                has_error_handling = any(
                    "error" in node.get('data', {}).get('label', '').lower() 
                    for node in nodes
                )
                
                if not has_error_handling and agent_count > 1:
                    optimizations["best_practices"].append({
                        "type": "error_handling",
                        "description": "No explicit error handling detected",
                        "impact": "medium",
                        "suggestion": "Consider adding error handling agents or validation steps"
                    })
                
                # Check for input validation
                has_input_validation = any(
                    "validation" in node.get('data', {}).get('label', '').lower()
                    for node in nodes
                )
                
                if not has_input_validation:
                    optimizations["best_practices"].append({
                        "type": "input_validation", 
                        "description": "No input validation detected",
                        "impact": "low",
                        "suggestion": "Add input validation at flow entry points"
                    })
            
            # Compile all optimizations
            all_opts = []
            all_opts.extend(optimizations["performance_improvements"])
            all_opts.extend(optimizations["structural_improvements"]) 
            all_opts.extend(optimizations["best_practices"])
            optimizations["optimizations"] = all_opts
            
            return optimizations
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Optimization error: {str(e)}"
            }
    
    return 3  # Number of tools registered