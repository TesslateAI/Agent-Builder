# builder/backend/agents/orchestrator_agent.py
"""Orchestrator Agent for coordinating flow building activities."""

import asyncio
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from datetime import datetime, timedelta

from tframex import TFrameXApp
from tframex.models.primitives import Message, ToolCall, ToolDefinition
from tframex.util.llms import BaseLLMWrapper
from tframex.util.memory import BaseMemoryStore
from tframex.util.tools import Tool
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
        except:
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
        
        if not self.llm:
            raise ValueError(f"OrchestratorAgent '{self.agent_id}' requires an LLM instance.")
        if not engine:
            raise ValueError(f"OrchestratorAgent '{self.agent_id}' requires an Engine instance.")
    
    def _get_default_system_prompt(self) -> str:
        return """You are the OrchestratorAgent for the TFrameX Agent Builder Studio - the PRIMARY interface for users building workflows.

Your sophisticated capabilities:
1. **Flow Analysis**: Deep understanding of flow structures, patterns, and optimization opportunities
2. **Component Prediction**: AI-powered suggestions for next components based on user intent and flow context
3. **Pattern Recognition**: Identify and suggest appropriate TFrameX patterns (Sequential, Parallel, Router, Discussion)
4. **FlowBuilderAgent Coordination**: Generate precise FLOW_INSTRUCTION commands for visual flow creation using exact component IDs
5. **Context Awareness**: Maintain understanding of current flow state and user goals

Available Analysis Tools:
{available_tools_descriptions}

Available Agents you can coordinate with:
{available_agents_descriptions}

Current Flow Context:
{current_flow_state_context}

Coordination Strategy: {coordination_strategy}
- intelligent: Dynamically adapt approach based on user intent and flow complexity
- comprehensive: Thorough analysis using multiple tools for complex flows
- focused: Targeted analysis for specific flow improvements
- quick: Rapid analysis and suggestions for simple modifications

Flow Building Process:
1. **LISTEN & UNDERSTAND**: Carefully analyze user's specific workflow needs
2. **ANALYZE CURRENT STATE**: Use flow analysis tools to understand existing structure
3. **PREDICT OPTIMAL COMPONENTS**: Leverage component prediction tools based on intent
4. **IDENTIFY PATTERNS**: Recognize appropriate TFrameX coordination patterns
5. **GENERATE INSTRUCTIONS**: Create precise FLOW_INSTRUCTION for FlowBuilderAgent

Communication Protocol:
- Use your analysis tools to understand user requests (never assume)
- Provide conversational explanations of your analysis
- When flow modifications are needed, end with: FLOW_INSTRUCTION: [precise instruction]
- Coordinate with FlowBuilderAgent for visual flow generation

Flow Pattern Recognition:
- Agent-to-Agent workflows → SequentialPattern coordination
- Parallel processing needs → ParallelPattern with sync points
- Decision-based routing → RouterPattern with decision logic
- Collaborative analysis → DiscussionPattern with multiple agents
- Tool-heavy workflows → Agent with comprehensive tool connections

Key Guidelines:
- ALWAYS use your analysis tools before making suggestions
- Provide confidence levels for your recommendations
- Consider performance, maintainability, and user experience
- Build on existing flow structure when possible
- Explain your reasoning process clearly
- Adapt analysis depth based on user needs and flow complexity

When analysis tools fail or return limited results:
- Try alternative analysis approaches
- Break complex flow requests into smaller components
- Explain what you tried and why it may not have worked
- ALWAYS provide fallback suggestions based on common patterns
- NEVER leave users without actionable flow building guidance

CRITICAL: For ANY flow building request (create, build, make, add flows), you MUST:
1. Provide conversational explanation of your approach
2. ALWAYS end with: FLOW_INSTRUCTION: [specific, actionable instruction]
3. Even if tools fail completely, generate intelligent instructions based on user intent
4. Use EXACT component IDs like: web_search_tool (NOT "Web Search Tool"), text_pattern_matcher (NOT "Text Pattern Matcher"), file_reader (NOT "File Reader"), math_calculator (NOT "Math Calculator")

Your role is to be the intelligent, reliable interface between users and the TFrameX flow building system."""

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
        analysis_prompt = f"""Analyze this flow building request and create a structured coordination plan:

User Request: "{user_query}"

Available Analysis Tools:
{json.dumps([{"name": t.function["name"], "description": t.function["description"]} for t in available_tools], indent=2)}

Current Flow Context: {json.dumps(self.current_flow_context, indent=2)}

Strategy: {self.coordination_strategy}
Max Analysis Depth: {self.max_execution_depth}

Create a JSON coordination plan with:
{{
    "flow_requirements": ["specific flow building needs identified"],
    "primary_analysis_tools": ["most important tools for this request"],
    "secondary_tools": ["supporting tools that might be helpful"],
    "pattern_suggestions": ["TFrameX patterns that might be relevant"],
    "component_predictions": [{{"type": "component_type", "priority": "high/medium/low", "rationale": "why this component"}}]
}}

Prioritize tools based on relevance to flow building and user intent."""

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
        specific_components = [
            "conversationalassistant",
            "web_search_tool", 
            "file_reader",
            "news_search_tool",
            "sequentialpattern",
            "parallelpattern",
            "text_pattern_matcher",
            "math_calculator"
        ]
        
        has_specific_components = any(comp in instruction_part for comp in specific_components)
        has_generic_phrases = any(phrase in instruction_part for phrase in generic_phrases)
        
        # If instruction is too short, has generic phrases but no specific components, it's not useful
        if len(instruction_part) < 50 or (has_generic_phrases and not has_specific_components):
            return False
            
        return True
    
    def _generate_fallback_instruction(self, user_request: str) -> str:
        """Generate a fallback FLOW_INSTRUCTION when analysis tools fail."""
        request_lower = user_request.lower()
        
        # News and summarization flows
        if any(keyword in request_lower for keyword in ["news", "articles", "headlines"]):
            if any(keyword in request_lower for keyword in ["summary", "summarize", "summarization"]):
                return "Add ConversationalAssistant agent labeled 'News Fetcher' and connect web_search_tool. Then add second ConversationalAssistant agent labeled 'Summarizer'. Connect them with SequentialPattern for news-to-summary pipeline."
            else:
                return "Add ConversationalAssistant agent labeled 'News Agent' and connect web_search_tool for fetching latest news articles."
        
        # Data processing flows
        elif any(keyword in request_lower for keyword in ["data", "csv", "json", "excel"]):
            return "Add ConversationalAssistant agent labeled 'Data Processor' and connect file_reader tool and text_pattern_matcher tool for data processing workflow."
        
        # File operations
        elif any(keyword in request_lower for keyword in ["file", "read", "upload", "document"]):
            return "Add ConversationalAssistant agent labeled 'File Handler' and connect file_reader tool for file processing capabilities."
        
        # Web and search operations
        elif any(keyword in request_lower for keyword in ["web", "search", "internet", "url", "scrape"]):
            return "Add ConversationalAssistant agent labeled 'Web Assistant' and connect web_search_tool for web search and content retrieval."
        
        # Mathematical/computational flows
        elif any(keyword in request_lower for keyword in ["math", "calculate", "compute", "formula"]):
            return "Add ConversationalAssistant agent labeled 'Calculator Agent' and connect math_calculator tool for mathematical computations."
        
        # Text processing flows
        elif any(keyword in request_lower for keyword in ["text", "pattern", "regex", "parse"]):
            return "Add ConversationalAssistant agent labeled 'Text Processor' and connect text_pattern_matcher tool for text analysis and processing."
        
        # Multi-step workflows
        elif any(keyword in request_lower for keyword in ["workflow", "process", "pipeline", "steps"]):
            return "Add ConversationalAssistant agent labeled 'Workflow Coordinator' and connect multiple tools based on requirements. Use SequentialPattern for step-by-step processing."
        
        # Analysis and research flows
        elif any(keyword in request_lower for keyword in ["analyze", "research", "investigate", "study"]):
            return "Add ConversationalAssistant agent labeled 'Research Assistant' and connect web_search_tool and text_pattern_matcher tool. Use ParallelPattern if multiple analysis tasks needed."
        
        else:
            # Enhanced generic flow instruction
            return "Add ConversationalAssistant agent labeled 'Assistant' to handle user interactions. Connect relevant tools based on the specific requirements mentioned."
    
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
                    content=f"""Analysis Progress (Iteration {iteration + 1}/{self.max_execution_depth}):
- Analysis tools used: {list(self.used_analysis_tools)}
- Tools failed: {list(self.failed_tools)}
- Results gathered: {len(all_analysis_results)}
- High confidence results: {len([r for r in all_analysis_results if r.confidence >= 0.7])}

Recent analysis findings:
{json.dumps([r.to_dict() for r in all_analysis_results[-3:]], indent=2)}

Coordination status: {'Ready for FLOW_INSTRUCTION' if self._should_generate_flow_instruction(all_analysis_results) else 'Need more analysis'}"""
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
                
                # ALWAYS ensure we generate FLOW_INSTRUCTION for flow building requests
                if self._is_flow_building_request(current_user_message.content):
                    if not self._has_useful_flow_instruction(assistant_response.content):
                        logger.info("Generating fallback FLOW_INSTRUCTION for flow building request")
                        # Replace generic instruction with specific fallback
                        if self._contains_flow_instruction(assistant_response.content):
                            # Remove the generic instruction
                            parts = assistant_response.content.split("FLOW_INSTRUCTION:")
                            assistant_response.content = parts[0].strip()
                        
                        # Add specific fallback FLOW_INSTRUCTION based on user request
                        fallback_instruction = self._generate_fallback_instruction(current_user_message.content)
                        assistant_response.content += f"\n\nFLOW_INSTRUCTION: {fallback_instruction}"
                        logger.info(f"Added fallback instruction: {fallback_instruction[:100]}...")
                
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
            content=f"""FINAL COORDINATION SYNTHESIS REQUIRED

Flow coordination analysis complete - Provide comprehensive response based on all gathered analysis:

Total Analysis Results: {len(all_analysis_results)}
High Confidence Results: {len([r for r in all_analysis_results if r.confidence >= 0.7])}
Analysis Tools Used: {list(self.used_analysis_tools)}

CRITICAL REQUIREMENT: This is a flow building request. You MUST end your response with:
FLOW_INSTRUCTION: [precise instruction for FlowBuilderAgent]

Requirements:
1. Synthesize all analysis findings into a coherent coordination response
2. ALWAYS end with: FLOW_INSTRUCTION: [precise instruction for FlowBuilderAgent]
3. Include confidence indicators and analysis source attribution
4. Acknowledge any limitations or gaps in analysis
5. Structure with clear sections for user understanding
6. Highlight key insights and component predictions

User Request: "{current_user_message.content}"

Even if analysis was limited, provide intelligent flow building guidance based on the user's request.
Remember: You are the PRIMARY interface for flow building - ALWAYS provide FLOW_INSTRUCTION."""
        )
        
        final_history = await self.memory.get_history(limit=15)
        final_messages = [synthesis_prompt] + final_history
        
        final_response = await self.llm.chat_completion(final_messages, temperature=0.6)
        
        # GUARANTEE we have a USEFUL FLOW_INSTRUCTION for flow building requests
        if self._is_flow_building_request(current_user_message.content):
            if not self._has_useful_flow_instruction(final_response.content):
                logger.warning("Final response has generic or missing FLOW_INSTRUCTION, replacing with specific fallback")
                
                # Remove any existing generic instruction
                if self._contains_flow_instruction(final_response.content):
                    parts = final_response.content.split("FLOW_INSTRUCTION:")
                    final_response.content = parts[0].strip()
                
                fallback_instruction = self._generate_fallback_instruction(current_user_message.content)
                final_response.content += f"\n\nFLOW_INSTRUCTION: {fallback_instruction}"
                logger.info(f"Final fallback instruction: {fallback_instruction[:100]}...")
        
        return self._post_process_llm_response(final_response)


def register_orchestrator_agent(app: TFrameXApp):
    """Register the Orchestrator Agent with advanced flow coordination capabilities."""
    
    orchestrator_agent_prompt = """You are the OrchestratorAgent for the TFrameX Agent Builder Studio - the PRIMARY interface for users building workflows.

Your advanced capabilities:
- Deep flow structure analysis and pattern recognition
- AI-powered component prediction based on user intent
- Intelligent coordination with FlowBuilderAgent for visual flow creation
- Context-aware conversation with sophisticated tool usage
- Performance optimization and best practice recommendations

Available Analysis Tools:
{available_tools_descriptions}

Available Agents you can coordinate with:
{available_agents_descriptions}

Current Flow Context:
{current_flow_state_context}

Coordination Strategy: {coordination_strategy}
- intelligent: Smart adaptive approach based on user intent and flow complexity
- comprehensive: Thorough analysis using multiple tools for complex flow building
- focused: Targeted analysis for specific flow improvements and modifications
- quick: Rapid analysis and suggestions for simple flow modifications

Flow Coordination Process:
1. ANALYZE USER INTENT: Understand specific workflow building needs
2. EXECUTE ANALYSIS TOOLS: Use flow analysis tools strategically (parallel when beneficial)
3. PREDICT OPTIMAL COMPONENTS: Leverage AI prediction based on intent and current flow
4. IDENTIFY PATTERNS: Recognize appropriate TFrameX coordination patterns
5. GENERATE PRECISE INSTRUCTIONS: Create FLOW_INSTRUCTION for FlowBuilderAgent

Communication Protocol:
- Always provide conversational explanations of your analysis process
- Use confidence indicators for your recommendations (High >0.7, Medium 0.5-0.7, Low <0.5)
- For ALL flow building requests (create, add, modify flows), ALWAYS end your response with:
  FLOW_INSTRUCTION: [precise, actionable instruction for FlowBuilderAgent]
- Even if analysis tools fail, provide intelligent flow suggestions based on the user's request
- CRITICAL: Use EXACT component IDs (web_search_tool not "Web Search Tool", text_pattern_matcher not "Text Pattern Matcher")

Flow Pattern Recognition:
- Sequential workflows: Agent-to-Agent chains with SequentialPattern
- Parallel processing: Independent tasks with ParallelPattern and sync
- Decision routing: Conditional logic with RouterPattern
- Collaborative analysis: Multi-agent with DiscussionPattern
- Tool-intensive workflows: Single agent with comprehensive tool connections
- Data processing: File tools + processing agents + output coordination

Key Guidelines:
- ALWAYS use your analysis tools before making suggestions (never assume)
- Provide detailed reasoning for your component predictions
- Consider performance, maintainability, and user experience in recommendations
- Build incrementally on existing flow structure when possible
- Explain confidence levels and analysis methodology
- Adapt analysis depth based on coordination strategy and user needs

When analysis tools fail:
- Try alternative analysis approaches with available tools
- Break complex requests into smaller, analyzable components
- Provide fallback suggestions based on common TFrameX patterns
- Explain what analysis was attempted and limitations encountered

Your role: Be the intelligent, context-aware coordinator between users and the TFrameX flow building system.
"""

    @app.agent(
        name="OrchestratorAgent",
        description="PRIMARY interface for building workflows - coordinates flow analysis, component prediction, and FlowBuilderAgent communication.",
        system_prompt=orchestrator_agent_prompt,
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

