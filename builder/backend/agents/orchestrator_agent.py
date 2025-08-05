# builder/backend/agents/orchestrator_agent.py
"""Orchestrator Agent for coordinating flow building activities."""

import asyncio
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union, Set
from datetime import datetime, timedelta

from tframex import TFrameXApp
from tframex.models.primitives import Message, ToolCall, ToolDefinition
from tframex.util.llms import BaseLLMWrapper
from tframex.util.memory import BaseMemoryStore
from tframex.util.tools import Tool

# Type import for Engine
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from tframex.engine import Engine
from tframex.agents import BaseAgent

logger = logging.getLogger(__name__)


class FlowPlan:
    """Structured flow building plan for organizing tool usage and flow construction."""
    
    def __init__(self):
        self.flow_requirements: List[str] = []
        self.primary_analysis_tools: List[str] = []
        self.secondary_tools: List[str] = []
        self.flow_steps: List[Dict[str, Any]] = []
        self.parallel_analysis_groups: List[List[str]] = []
        self.optimization_targets: Dict[str, float] = {}
        self.pattern_suggestions: List[str] = []
        self.component_predictions: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_requirements": self.flow_requirements,
            "primary_analysis_tools": self.primary_analysis_tools,
            "secondary_tools": self.secondary_tools,
            "flow_steps": self.flow_steps,
            "parallel_analysis_groups": self.parallel_analysis_groups,
            "optimization_targets": self.optimization_targets,
            "pattern_suggestions": self.pattern_suggestions,
            "component_predictions": self.component_predictions
        }


class FlowResult:
    """Container for flow analysis results with metadata and confidence scoring."""
    
    def __init__(self, tool_name: str, analysis_type: str, result: Any, confidence: float = 0.5):
        self.tool_name = tool_name
        self.analysis_type = analysis_type
        self.result = result
        self.confidence = confidence
        self.timestamp = datetime.now()
        self.result_hash = self._hash_result(result)
        self.flow_instruction_generated = False
    
    def _hash_result(self, result: Any) -> str:
        """Create a hash of the result for deduplication."""
        try:
            result_str = json.dumps(result, sort_keys=True) if isinstance(result, (dict, list)) else str(result)
            return hashlib.md5(result_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return hashlib.md5(str(result).encode()).hexdigest()
    
    def is_expired(self, max_age_minutes: int = 15) -> bool:
        """Check if result is expired based on age (shorter for flow analysis)."""
        return datetime.now() - self.timestamp > timedelta(minutes=max_age_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "analysis_type": self.analysis_type,
            "result": self.result,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.result_hash,
            "flow_instruction_generated": self.flow_instruction_generated
        }


class OrchestratorAgent(BaseAgent):
    """
    Sophisticated flow coordination agent for TFrameX Agent Builder Studio.
    
    Key capabilities:
    - Advanced flow analysis and pattern recognition
    - Intelligent component prediction and optimization
    - Parallel tool execution for flow analysis tasks
    - Result caching and intelligent reuse
    - Dynamic coordination with FlowBuilderAgent
    - Context-aware conversation and instruction generation
    - Adaptive execution strategies based on user needs
    """
    
    def __init__(
        self,
        agent_id: str,
        llm: BaseLLMWrapper,
        engine: "Engine",
        description: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        memory: Optional[BaseMemoryStore] = None,
        system_prompt_template: Optional[str] = None,
        callable_agent_definitions: Optional[List[ToolDefinition]] = None,
        strip_think_tags: bool = True,
        max_execution_depth: int = 4,
        coordination_strategy: str = "intelligent", 
        enable_parallel_analysis: bool = True,
        cache_results: bool = True,
        flow_instruction_threshold: float = 0.7,
        **config: Any,
    ):
        """
        Initialize the orchestrator agent with flow coordination capabilities.
        """
        if not system_prompt_template:
            system_prompt_template = self._get_default_system_prompt()
            logger.info(f"OrchestratorAgent {agent_id}: Using default system prompt (concise version)")
        else:
            logger.info(f"OrchestratorAgent {agent_id}: Using provided system prompt, length: {len(system_prompt_template)}")
            
        if not description:
            description = "PRIMARY interface for building workflows - coordinates flow analysis, component prediction, and FlowBuilderAgent communication"
            
        # Log tools for debugging
        if isinstance(tools, list):
            logger.info(f"OrchestratorAgent {agent_id}: Received tools list with {len(tools)} items")
            for i, tool in enumerate(tools):
                logger.info(f"  Tool {i}: {type(tool)} - {getattr(tool, 'name', 'NO_NAME_ATTR')}")
        else:
            logger.info(f"OrchestratorAgent {agent_id}: Received tools dict: {tools}")
        
        # Pass tools directly to BaseAgent - it will handle the list->dict conversion
        super().__init__(
            agent_id=agent_id,
            description=description,
            llm=llm,
            tools=tools,  # Pass original tools parameter
            memory=memory,
            system_prompt_template=system_prompt_template,
            callable_agent_definitions=callable_agent_definitions,
            strip_think_tags=strip_think_tags,
            **config
        )
        
        self.engine = engine
        self.max_execution_depth = max_execution_depth
        self.coordination_strategy = coordination_strategy  
        self.enable_parallel_analysis = enable_parallel_analysis
        self.cache_results = cache_results
        self.flow_instruction_threshold = flow_instruction_threshold
        
        # Initialize caches and tracking
        self.analysis_cache: Dict[str, FlowResult] = {}
        self.used_analysis_tools: Set[str] = set()
        self.failed_tools: Set[str] = set()
        self.current_flow_context: Dict[str, Any] = {}
        self.available_components: Dict[str, List[Dict[str, Any]]] = {}
        
        if not self.llm:
            raise ValueError(f"OrchestratorAgent '{self.agent_id}' requires an LLM instance.")
        if not engine:
            raise ValueError(f"OrchestratorAgent '{self.agent_id}' requires an Engine instance.")
    
    def _get_default_system_prompt(self) -> str:
        return """You are the OrchestratorAgent - the primary interface for building TFrameX workflows.

CORE FUNCTION: Analyze user requests and generate FLOW_INSTRUCTION commands for the FlowBuilderAgent.

Available Components:
{available_components_context}

Current Flow: {current_flow_state_context}

PROCESS:
1. Understand user's workflow request
2. Identify required components from available list above
3. Generate FLOW_INSTRUCTION with exact component IDs

FLOW PATTERNS:
- Multiple agents discussing → DiscussionPattern with participants: [agent1, agent2, ...]
- Sequential steps → SequentialPattern with steps_config: [agent1, agent2, ...]
- Parallel tasks → ParallelPattern with tasks: [agent1, agent2, ...]
- Decision routing → RouterPattern with router_agent_name and routes

CRITICAL RULES:
- ALWAYS end flow requests with: FLOW_INSTRUCTION: [specific instruction]
- Use EXACT component IDs from available components list
- Be specific: "Create DiscussionPattern with participants: ['ResearchAgent', 'ConversationalAssistant']"
- If unclear, ask specific questions

Your job: Convert user requests into precise, actionable FLOW_INSTRUCTION commands."""

    def _get_all_available_tool_definitions(self) -> List[ToolDefinition]:
        """Get all available tool definitions for the LLM."""
        all_defs: List[ToolDefinition] = []
        
        if self.tools:
            logger.debug(f"OrchestratorAgent {self.agent_id}: Processing {len(self.tools)} tools")
            for tool_name, tool_obj in self.tools.items():
                logger.debug(f"  Tool '{tool_name}': {type(tool_obj)}")
                try:
                    if hasattr(tool_obj, 'get_openai_tool_definition'):
                        all_defs.append(tool_obj.get_openai_tool_definition())
                    else:
                        logger.error(f"Tool '{tool_name}' ({type(tool_obj)}) has no get_openai_tool_definition method")
                except Exception as e:
                    logger.error(f"Error getting tool definition for '{tool_name}': {e}")
                
        if self.callable_agent_definitions:
            all_defs.extend(self.callable_agent_definitions)
            
        logger.info(f"OrchestratorAgent {self.agent_id}: Found {len(all_defs)} tool definitions")
        return all_defs
    
    async def _analyze_and_plan_coordination(self, user_query: str, available_tools: List[ToolDefinition]) -> FlowPlan:
        """
        Analyze the user's request and create a structured coordination plan.
        """
        analysis_prompt = f"""Create coordination plan for: "{user_query}"

Available Tools: {json.dumps([{"name": t.function["name"], "description": t.function["description"]} for t in available_tools], indent=2)}

Return JSON:
{{
    "flow_requirements": ["needs identified"],
    "primary_analysis_tools": ["most relevant tools"],
    "secondary_tools": ["supporting tools"],
    "pattern_suggestions": ["relevant TFrameX patterns"],
    "component_predictions": [{{"type": "component_type", "priority": "high/medium/low"}}]
}}"""

        analysis_message = Message(role="user", content=analysis_prompt)
        
        try:
            response = await self.llm.chat_completion(
                [Message(role="system", content="You are a flow coordination planning specialist. Respond with valid JSON only."),
                 analysis_message],
                temperature=0.3
            )
            
            plan_data = json.loads(response.content)
            plan = FlowPlan()
            
            plan.flow_requirements = plan_data.get("flow_requirements", [])
            plan.primary_analysis_tools = plan_data.get("primary_analysis_tools", [])
            plan.secondary_tools = plan_data.get("secondary_tools", [])
            plan.pattern_suggestions = plan_data.get("pattern_suggestions", [])
            plan.component_predictions = plan_data.get("component_predictions", [])
            
            return plan
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse coordination plan, using fallback: {e}")
            return self._create_fallback_plan(available_tools)
    
    def _create_fallback_plan(self, available_tools: List[ToolDefinition]) -> FlowPlan:
        """Create a simple fallback coordination plan."""
        plan = FlowPlan()
        tool_names = [t.function["name"] for t in available_tools]
        
        plan.flow_requirements = ["General flow building assistance"]
        plan.primary_analysis_tools = tool_names[:2]  # Use first 2 tools
        plan.secondary_tools = tool_names[2:4]  # Next 2 as secondary
        plan.pattern_suggestions = ["SequentialPattern", "ParallelPattern"]
        
        return plan
    
    def _get_cache_key(self, tool_name: str, args: str) -> str:
        """Generate a cache key for analysis results."""
        return hashlib.md5(f"{tool_name}:{args}".encode()).hexdigest()
    
    async def _execute_analysis_parallel(self, tool_calls: List[ToolCall]) -> List[FlowResult]:
        """Execute multiple analysis tool calls in parallel when possible."""
        if not self.enable_parallel_analysis or len(tool_calls) <= 1:
            return await self._execute_analysis_sequential(tool_calls)
        
        async def execute_single_analysis(tool_call: ToolCall) -> FlowResult:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            
            # Check cache first
            cache_key = self._get_cache_key(tool_name, tool_args)
            if self.cache_results and cache_key in self.analysis_cache:
                cached_result = self.analysis_cache[cache_key]
                if not cached_result.is_expired():
                    logger.debug(f"Using cached analysis result for {tool_name}")
                    return cached_result
            
            try:
                result = await self.engine.execute_tool_by_llm_definition(tool_name, tool_args)
                confidence = self._estimate_analysis_confidence(tool_name, result)
                analysis_type = self._determine_analysis_type(tool_name)
                
                flow_result = FlowResult(tool_name, analysis_type, result, confidence)
                
                # Cache result
                if self.cache_results:
                    self.analysis_cache[cache_key] = flow_result
                
                self.used_analysis_tools.add(tool_name)
                return flow_result
                
            except Exception as e:
                logger.error(f"Analysis tool {tool_name} failed: {e}")
                self.failed_tools.add(tool_name)
                return FlowResult(
                    tool_name, 
                    "error",
                    {"error": str(e)}, 
                    0.0
                )
        
        # Execute analysis tools in parallel
        tasks = [execute_single_analysis(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, FlowResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Parallel analysis execution exception: {result}")
        
        return valid_results
    
    async def _execute_analysis_sequential(self, tool_calls: List[ToolCall]) -> List[FlowResult]:
        """Execute analysis tool calls sequentially."""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            
            # Check cache first
            cache_key = self._get_cache_key(tool_name, tool_args)
            if self.cache_results and cache_key in self.analysis_cache:
                cached_result = self.analysis_cache[cache_key]
                if not cached_result.is_expired():
                    logger.debug(f"Using cached analysis result for {tool_name}")
                    results.append(cached_result)
                    continue
            
            try:
                result = await self.engine.execute_tool_by_llm_definition(tool_name, tool_args)
                confidence = self._estimate_analysis_confidence(tool_name, result)
                analysis_type = self._determine_analysis_type(tool_name)
                
                flow_result = FlowResult(tool_name, analysis_type, result, confidence)
                
                # Cache result
                if self.cache_results:
                    self.analysis_cache[cache_key] = flow_result
                
                results.append(flow_result)
                self.used_analysis_tools.add(tool_name)
                
            except Exception as e:
                logger.error(f"Analysis tool {tool_name} failed: {e}")
                self.failed_tools.add(tool_name)
                results.append(FlowResult(
                    tool_name, 
                    "error",
                    {"error": str(e)}, 
                    0.0
                ))
        
        return results
    
    def _determine_analysis_type(self, tool_name: str) -> str:
        """Determine the type of analysis based on tool name."""
        tool_lower = tool_name.lower()
        if "structure" in tool_lower or "analyzer" in tool_lower:
            return "structure_analysis"
        elif "predict" in tool_lower or "drag" in tool_lower:
            return "component_prediction"
        elif "optim" in tool_lower:
            return "optimization"
        elif "pattern" in tool_lower:
            return "pattern_matching"
        else:
            return "general_analysis"
    
    def _estimate_analysis_confidence(self, tool_name: str, result: Any) -> float:
        """Estimate confidence level of an analysis tool result."""
        # Basic heuristics for confidence estimation
        if isinstance(result, dict) and "error" in result:
            return 0.0
        
        if result is None or result == "":
            return 0.1
        
        # Tool-specific confidence estimation
        tool_lower = tool_name.lower()
        
        if "structure" in tool_lower or "analyzer" in tool_lower:
            if isinstance(result, dict) and len(result) > 0:
                return 0.9  # Structure analysis is highly reliable
            return 0.3
        
        if "predict" in tool_lower or "drag" in tool_lower:
            if isinstance(result, (list, dict)) and len(result) > 0:
                return 0.8  # Predictions are generally reliable
            return 0.4
        
        if "optim" in tool_lower:
            return 0.7  # Optimization suggestions are moderately reliable
        
        # Default confidence for flow analysis
        return 0.6
    
    def _should_continue_analysis(self, results: List[FlowResult], iteration: int) -> bool:
        """Determine if more analysis is needed."""
        if iteration >= self.max_execution_depth:
            return False
        
        if self.coordination_strategy == "quick":
            return len(results) < 2
        elif self.coordination_strategy == "focused":
            return len(results) < 3
        elif self.coordination_strategy == "comprehensive":
            return len(results) < 5
        else:  # intelligent
            # Check if we have sufficient analysis coverage
            analysis_types = set(r.analysis_type for r in results)
            high_confidence_results = [r for r in results if r.confidence >= 0.7]
            
            return len(analysis_types) < 2 or len(high_confidence_results) < 2
    
    def _should_generate_flow_instruction(self, results: List[FlowResult]) -> bool:
        """Determine if we have sufficient analysis to generate a FLOW_INSTRUCTION."""
        # ALWAYS generate flow instruction for flow building requests
        # The user is asking to create/modify a flow, so we should always provide instruction
        return True
    
    def _is_flow_building_request(self, user_message: str) -> bool:
        """Detect if the user is requesting flow building/modification."""
        flow_keywords = [
            "create", "build", "make", "add", "design", "flow", "workflow", 
            "agent", "tool", "pattern", "connect", "news", "summarize", 
            "process", "analyze", "search", "fetch", "get"
        ]
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in flow_keywords)
    
    def _contains_flow_instruction(self, content: str) -> bool:
        """Check if the response already contains a FLOW_INSTRUCTION."""
        return "FLOW_INSTRUCTION:" in content
    
    def _has_useful_flow_instruction(self, content: str) -> bool:
        """Check if the response contains a useful, specific FLOW_INSTRUCTION."""
        if not self._contains_flow_instruction(content):
            return False
        
        instruction_part = content.split("FLOW_INSTRUCTION:")[1].strip().lower()
        
        # Check for generic/useless instructions
        generic_phrases = [
            "please proceed",
            "proceed with",
            "continue with", 
            "start the process",
            "begin the process",
            "create the flow",
            "build the flow",
            "start building",
            "start by",
            "you can start",
            "adding components",
            "add components",
            "by adding",
            "create a flow with",
            "following components",
            "data source component",
            "output component",
            "text summarization component"
        ]
        
        # Check if instruction mentions specific available components
        specific_components = []
        
        # Dynamically build list from available components
        for category in ["agents", "tools", "patterns"]:
            for comp in self.available_components.get(category, []):
                specific_components.append(comp["id"].lower())
        
        has_specific_components = any(comp in instruction_part for comp in specific_components)
        has_generic_phrases = any(phrase in instruction_part for phrase in generic_phrases)
        
        # If instruction is too short, has generic phrases but no specific components, it's not useful
        if len(instruction_part) < 50 or (has_generic_phrases and not has_specific_components):
            return False
            
        return True
    
    def _parse_available_components(self, components_context: str) -> None:
        """Parse available components from context string."""
        self.available_components = {"agents": [], "tools": [], "patterns": []}
        
        if not components_context:
            return
        
        current_category = None
        for line in components_context.split('\n'):
            line = line.strip()
            if line.upper().endswith(':') and line[:-1].lower() in ['agents', 'tools', 'patterns']:
                current_category = line[:-1].lower()
            elif line.startswith('- ID:') and current_category:
                # Parse component from line like: "- ID: web_search_tool, Name: web_search_tool ..."
                parts = line.split(',')
                if parts:
                    id_part = parts[0].replace('- ID:', '').strip()
                    self.available_components[current_category].append({
                        "id": id_part,
                        "line": line
                    })
    
    async def run(self, input_message: Union[str, Message], **kwargs: Any) -> Message:
        """
        Execute sophisticated flow coordination based on user input.
        """
        # Reset state for new coordination session
        self.used_analysis_tools.clear()
        self.failed_tools.clear()
        
        if isinstance(input_message, str):
            current_user_message = Message(role="user", content=input_message)
        elif isinstance(input_message, Message):
            current_user_message = input_message
        else:
            return Message(role="assistant", content="Error: Invalid input type provided to orchestrator agent.")
        
        await self.memory.add_message(current_user_message)
        
        template_vars = kwargs.get("template_vars", {})
        template_vars["coordination_strategy"] = self.coordination_strategy
        
        # Update flow context from template vars
        self.current_flow_context = template_vars.get("current_flow_state_context", {})
        
        # Parse available components from context
        self._parse_available_components(template_vars.get("available_components_context", ""))
        
        available_tools = self._get_all_available_tool_definitions()
        
        if not available_tools:
            return Message(
                role="assistant", 
                content="I don't have any flow analysis tools available. Please connect the Flow Structure Analyzer, Drag-Drop Predictor, and Flow Optimizer tools to enable my coordination capabilities."
            )
        
        # Create coordination plan
        coordination_plan = await self._analyze_and_plan_coordination(current_user_message.content, available_tools)
        logger.info(f"Coordination plan created: {coordination_plan.to_dict()}")
        
        all_analysis_results: List[FlowResult] = []
        iteration = 0
        
        while iteration < self.max_execution_depth:
            history = await self.memory.get_history(limit=10)  # Shorter history for flow context
            messages_for_llm: List[Message] = []
            
            # Add system message with coordination context
            system_message = self._render_system_prompt(**template_vars)
            if system_message:
                messages_for_llm.append(system_message)
            
            # Add analysis progress context
            if all_analysis_results:
                context_msg = Message(
                    role="system",
                    content=f"""Analysis: {len(all_analysis_results)} results, iteration {iteration + 1}/{self.max_execution_depth}
Tools used: {list(self.used_analysis_tools)}
Status: {'Ready for FLOW_INSTRUCTION' if self._should_generate_flow_instruction(all_analysis_results) else 'Need more analysis'}"""
                )
                messages_for_llm.append(context_msg)
            
            messages_for_llm.extend(history)
            
            # Determine tool choice strategy
            if iteration >= self.max_execution_depth - 1:
                tool_choice = "none"  # Force final response
            elif not self._should_continue_analysis(all_analysis_results, iteration):
                tool_choice = "none"  # Sufficient analysis gathered
            else:
                tool_choice = "auto"
            
            llm_params = {
                "tools": [td.model_dump(exclude_none=True) for td in available_tools],
                "tool_choice": tool_choice,
                "temperature": 0.6  # Slightly lower for more consistent coordination
            }
            
            assistant_response = await self.llm.chat_completion(messages_for_llm, **llm_params)
            await self.memory.add_message(assistant_response)
            
            if not assistant_response.tool_calls:
                logger.info(f"Flow coordination complete after {iteration + 1} iterations with {len(all_analysis_results)} analysis results")
                
                # If this is a flow building request but we couldn't generate a good instruction
                if self._is_flow_building_request(current_user_message.content):
                    if not self._has_useful_flow_instruction(assistant_response.content):
                        logger.info("No useful FLOW_INSTRUCTION generated, asking for clarification")
                        # Replace or append with clarification request
                        if self._contains_flow_instruction(assistant_response.content):
                            # Remove any generic instruction
                            parts = assistant_response.content.split("FLOW_INSTRUCTION:")
                            assistant_response.content = parts[0].strip()
                        
                        # Ask for clarification instead of guessing
                        assistant_response.content += "\n\nI understand you want to build a flow, but I need more specific information to help you effectively. Could you please clarify:\n\n"
                        assistant_response.content += "- What is the main purpose of your workflow?\n"
                        assistant_response.content += "- What kind of data or information will it process?\n"
                        assistant_response.content += "- What specific tasks should it perform?\n"
                        assistant_response.content += "- What output or result are you expecting?\n\n"
                        assistant_response.content += "Once you provide more details, I can suggest the exact components and structure for your flow."
                
                return self._post_process_llm_response(assistant_response)
            
            # Execute analysis tool calls (parallel when possible)
            logger.info(f"Iteration {iteration + 1}: Executing {len(assistant_response.tool_calls)} analysis tool calls")
            
            analysis_results = await self._execute_analysis_parallel(assistant_response.tool_calls)
            all_analysis_results.extend(analysis_results)
            
            # Add tool responses to memory
            for i, (tool_call, result) in enumerate(zip(assistant_response.tool_calls, analysis_results)):
                tool_response = Message(
                    role="tool",
                    tool_call_id=tool_call.id,
                    name=result.tool_name,
                    content=json.dumps({
                        "result": result.result,
                        "confidence": result.confidence,
                        "analysis_type": result.analysis_type,
                        "timestamp": result.timestamp.isoformat()
                    })
                )
                await self.memory.add_message(tool_response)
            
            iteration += 1
        
        # Final coordination synthesis with all analysis results
        synthesis_prompt = Message(
            role="system",
            content=f"""Final analysis complete. User request: "{current_user_message.content}"

Analysis: {len(all_analysis_results)} results, {len([r for r in all_analysis_results if r.confidence >= 0.7])} high confidence

Requirements:
1. If intent is CLEAR: End with FLOW_INSTRUCTION: [precise instruction]
2. If intent is UNCLEAR: Ask specific questions
3. Be helpful and conversational"""
        )
        
        final_history = await self.memory.get_history(limit=15)
        final_messages = [synthesis_prompt] + final_history
        
        final_response = await self.llm.chat_completion(final_messages, temperature=0.6)
        
        # If this is a flow building request but we still don't have a good instruction
        if self._is_flow_building_request(current_user_message.content):
            if not self._has_useful_flow_instruction(final_response.content):
                logger.warning("Final response lacks useful FLOW_INSTRUCTION, asking for clarification")
                
                # Remove any existing generic instruction
                if self._contains_flow_instruction(final_response.content):
                    parts = final_response.content.split("FLOW_INSTRUCTION:")
                    final_response.content = parts[0].strip()
                
                # Provide helpful clarification request based on what we learned
                final_response.content += "\n\nBased on my analysis, I can see you want to create a workflow, but I need more specific details to generate the exact flow structure. \n\n"
                
                # If we detected some intent, acknowledge it
                request_lower = current_user_message.content.lower()
                if any(keyword in request_lower for keyword in ["file", "data", "web", "search", "news", "text", "math"]):
                    final_response.content += f"I noticed your request mentions '{current_user_message.content}', which suggests you might want to work with specific types of data or operations.\n\n"
                
                final_response.content += "To create the most effective flow for you, please provide:\n\n"
                final_response.content += "1. **Specific Goal**: What should the workflow accomplish?\n"
                final_response.content += "2. **Input/Source**: What data or information will it start with?\n"
                final_response.content += "3. **Processing Steps**: What operations or transformations are needed?\n"
                final_response.content += "4. **Expected Output**: What should be the final result?\n\n"
                final_response.content += "With these details, I can recommend the exact agents, tools, and patterns that will best meet your needs."
        
        return self._post_process_llm_response(final_response)


def register_orchestrator_agent(app: TFrameXApp):
    """Register the Orchestrator Agent with advanced flow coordination capabilities."""
    
    # Use the concise default system prompt instead of duplicating
    orchestrator_agent_prompt = None  # Will use _get_default_system_prompt()

    @app.agent(
        name="OrchestratorAgent",
        description="PRIMARY interface for building workflows - coordinates flow analysis, component prediction, and FlowBuilderAgent communication.",
        system_prompt=orchestrator_agent_prompt,  # None, will use _get_default_system_prompt()
        agent_class=OrchestratorAgent,
        can_use_tools=True,
        native_tool_names=["flow_structure_analyzer", "drag_drop_predictor", "flow_optimizer", "text_pattern_matcher"],
        max_execution_depth=4,
        coordination_strategy="intelligent",
        enable_parallel_analysis=True,
        cache_results=True,
        flow_instruction_threshold=0.7,
        strip_think_tags=True
    )
    async def _orchestrator_agent_placeholder():
        """
        PRIMARY flow building coordinator with advanced analysis capabilities.
        
        Key Features:
        - Sophisticated flow structure analysis and pattern recognition
        - AI-powered component prediction based on user intent and context
        - Parallel tool execution for efficient analysis
        - Result caching and intelligent reuse for performance
        - Dynamic coordination with FlowBuilderAgent
        - Context-aware conversation and instruction generation
        
        Coordination Strategies:
        - intelligent: Smart approach adapting to user needs and flow complexity
        - comprehensive: Thorough multi-tool analysis for complex flows
        - focused: Targeted analysis for specific improvements
        - quick: Rapid analysis for simple modifications
        
        Works with specialized flow analysis tools:
        - Flow Structure Analyzer: Deep topology and pattern analysis
        - Drag-Drop Predictor: AI-powered component suggestions
        - Flow Optimizer: Performance and maintainability recommendations
        - math_calculator: Computational analysis support
        - text_pattern_matcher: Pattern recognition assistance
        """
        pass

