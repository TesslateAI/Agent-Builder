# builder/backend/agents/research_agent.py
"""Research Agent registration for TFrameX Agent Builder."""

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


class ResearchPlan:
    """Structured research plan for organizing tool usage."""
    
    def __init__(self):
        self.information_needs: List[str] = []
        self.primary_tools: List[str] = []
        self.secondary_tools: List[str] = []
        self.research_steps: List[Dict[str, Any]] = []
        self.parallel_groups: List[List[str]] = []
        self.confidence_targets: Dict[str, float] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "information_needs": self.information_needs,
            "primary_tools": self.primary_tools,
            "secondary_tools": self.secondary_tools,
            "research_steps": self.research_steps,
            "parallel_groups": self.parallel_groups,
            "confidence_targets": self.confidence_targets
        }


class ResearchResult:
    """Container for research findings with metadata."""
    
    def __init__(self, tool_name: str, query: str, result: Any, confidence: float = 0.5):
        self.tool_name = tool_name
        self.query = query
        self.result = result
        self.confidence = confidence
        self.timestamp = datetime.now()
        self.result_hash = self._hash_result(result)
    
    def _hash_result(self, result: Any) -> str:
        """Create a hash of the result for deduplication."""
        try:
            result_str = json.dumps(result, sort_keys=True) if isinstance(result, (dict, list)) else str(result)
            return hashlib.md5(result_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return hashlib.md5(str(result).encode()).hexdigest()
    
    def is_expired(self, max_age_minutes: int = 30) -> bool:
        """Check if result is expired based on age."""
        return datetime.now() - self.timestamp > timedelta(minutes=max_age_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "query": self.query,
            "result": self.result,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.result_hash
        }


class ResearchAgent(BaseAgent):
    """
    General-purpose tool-using agent that can accomplish various tasks.
    
    Key capabilities:
    - Dynamic task analysis and planning
    - Parallel tool execution when beneficial  
    - Result caching and intelligent reuse
    - Clear reasoning and result synthesis
    - Adaptive approach based on available tools
    - Robust error handling and alternative strategies
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
        execution_strategy: str = "adaptive", 
        enable_parallel_execution: bool = True,
        cache_results: bool = True,
        **config: Any,
    ):
        """
        Initialize the agent with tool-using capabilities.
        """
        if not system_prompt_template:
            system_prompt_template = self._get_default_system_prompt()
            
        if not description:
            description = "General-purpose agent that intelligently uses available tools to help users accomplish various tasks and goals"
            
        # Log tools for debugging
        if isinstance(tools, list):
            logger.info(f"ResearchAgent {agent_id}: Received tools list with {len(tools)} items")
            for i, tool in enumerate(tools):
                logger.info(f"  Tool {i}: {type(tool)} - {getattr(tool, 'name', 'NO_NAME_ATTR')}")
        else:
            logger.info(f"ResearchAgent {agent_id}: Received tools dict: {tools}")
        
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
        self.execution_strategy = execution_strategy  
        self.enable_parallel_execution = enable_parallel_execution
        self.cache_results = cache_results
        
        # Initialize caches and tracking
        self.result_cache: Dict[str, ResearchResult] = {}
        self.used_tools: Set[str] = set()
        self.failed_tools: Set[str] = set()
        
        if not self.llm:
            raise ValueError(f"ResearchAgent '{self.agent_id}' requires an LLM instance.")
        if not engine:
            raise ValueError(f"ResearchAgent '{self.agent_id}' requires an Engine instance.")
    
    def _get_default_system_prompt(self) -> str:
        return """You are an intelligent assistant that can use available tools to help users accomplish their goals.

Your approach:
1. **Understand** the user's request and identify what needs to be done
2. **Plan** which tools might be helpful, considering their capabilities and limitations  
3. **Execute** tools thoughtfully, using parallel execution when tasks are independent
4. **Adapt** your strategy based on results and try alternative approaches if needed
5. **Synthesize** information from multiple sources into a clear, helpful response

Available tools:
{available_tools_descriptions}

Available agents you can call:
{available_agents_descriptions}

Execution Strategy: {execution_strategy}
- adaptive: Dynamically adjust approach based on results and available tools
- comprehensive: Use multiple tools and sources for thorough analysis
- focused: Target specific objectives efficiently with selected tools
- quick: Accomplish goals with minimal tool usage for fast results

General Guidelines:
- Read tool descriptions carefully and use them appropriately
- Try multiple approaches if initial attempts don't succeed
- Use parallel execution when working on independent tasks
- Provide clear explanations of your reasoning and process
- Cite sources and acknowledge limitations when relevant
- Build on previous results rather than repeating work
- Choose tools based on their described capabilities, not assumptions

When tools fail or return limited results:
- Try alternative tools that might accomplish similar goals
- Break complex tasks into smaller, more manageable pieces
- Explain what you tried and why it may not have worked
- Adapt your approach based on what tools are actually available"""

    def _get_all_available_tool_definitions(self) -> List[ToolDefinition]:
        """Get all available tool definitions for the LLM."""
        all_defs: List[ToolDefinition] = []
        
        if self.tools:
            logger.debug(f"ResearchAgent {self.agent_id}: Processing {len(self.tools)} tools")
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
            
        logger.info(f"ResearchAgent {self.agent_id}: Found {len(all_defs)} tool definitions")
        return all_defs
    
    async def _analyze_and_plan_research(self, user_query: str, available_tools: List[ToolDefinition]) -> ResearchPlan:
        """
        Analyze the user's query and create a structured research plan.
        """
        analysis_prompt = f"""Analyze this research query and create a structured plan:

Query: "{user_query}"

Available Tools:
{json.dumps([{"name": t.function["name"], "description": t.function["description"]} for t in available_tools], indent=2)}

Strategy: {self.execution_strategy}
Max Depth: {self.max_execution_depth}

Create a JSON research plan with:
{{
    "information_needs": ["specific information categories needed"],
    "primary_tools": ["most important tools for this query"],
    "secondary_tools": ["supporting tools that might be helpful"]
}}

Prioritize tools based on relevance to query and information quality potential."""

        analysis_message = Message(role="user", content=analysis_prompt)
        
        try:
            response = await self.llm.chat_completion(
                [Message(role="system", content="You are a research planning specialist. Respond with valid JSON only."),
                 analysis_message],
                temperature=0.3
            )
            
            plan_data = json.loads(response.content)
            plan = ResearchPlan()
            
            plan.information_needs = plan_data.get("information_needs", [])
            plan.primary_tools = plan_data.get("primary_tools", [])
            plan.secondary_tools = plan_data.get("secondary_tools", [])
            
            return plan
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse research plan, using fallback: {e}")
            return self._create_fallback_plan(available_tools)
    
    def _create_fallback_plan(self, available_tools: List[ToolDefinition]) -> ResearchPlan:
        """Create a simple fallback research plan."""
        plan = ResearchPlan()
        tool_names = [t.function["name"] for t in available_tools]
        
        plan.information_needs = ["General information about the query"]
        plan.primary_tools = tool_names[:3]  # Use first 3 tools
        plan.secondary_tools = tool_names[3:6]  # Next 3 as secondary
        
        return plan
    
    def _get_cache_key(self, tool_name: str, args: str) -> str:
        """Generate a cache key for tool results."""
        return hashlib.md5(f"{tool_name}:{args}".encode()).hexdigest()
    
    async def _execute_tools_parallel(self, tool_calls: List[ToolCall]) -> List[ResearchResult]:
        """Execute multiple tool calls in parallel when possible."""
        if not self.enable_parallel_execution or len(tool_calls) <= 1:
            return await self._execute_tools_sequential(tool_calls)
        
        async def execute_single_tool(tool_call: ToolCall) -> ResearchResult:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            
            # Check cache first
            cache_key = self._get_cache_key(tool_name, tool_args)
            if self.cache_results and cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                if not cached_result.is_expired():
                    logger.debug(f"Using cached result for {tool_name}")
                    return cached_result
            
            try:
                result = await self.engine.execute_tool_by_llm_definition(tool_name, tool_args)
                confidence = self._estimate_confidence(tool_name, result)
                
                research_result = ResearchResult(tool_name, tool_args, result, confidence)
                
                # Cache result
                if self.cache_results:
                    self.result_cache[cache_key] = research_result
                
                self.used_tools.add(tool_name)
                return research_result
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                self.failed_tools.add(tool_name)
                return ResearchResult(
                    tool_name, 
                    tool_args, 
                    {"error": str(e)}, 
                    0.0
                )
        
        # Execute tools in parallel
        tasks = [execute_single_tool(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, ResearchResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Parallel execution exception: {result}")
        
        return valid_results
    
    async def _execute_tools_sequential(self, tool_calls: List[ToolCall]) -> List[ResearchResult]:
        """Execute tool calls sequentially."""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            
            # Check cache first
            cache_key = self._get_cache_key(tool_name, tool_args)
            if self.cache_results and cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                if not cached_result.is_expired():
                    logger.debug(f"Using cached result for {tool_name}")
                    results.append(cached_result)
                    continue
            
            try:
                result = await self.engine.execute_tool_by_llm_definition(tool_name, tool_args)
                confidence = self._estimate_confidence(tool_name, result)
                
                research_result = ResearchResult(tool_name, tool_args, result, confidence)
                
                # Cache result
                if self.cache_results:
                    self.result_cache[cache_key] = research_result
                
                results.append(research_result)
                self.used_tools.add(tool_name)
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                self.failed_tools.add(tool_name)
                results.append(ResearchResult(
                    tool_name, 
                    tool_args, 
                    {"error": str(e)}, 
                    0.0
                ))
        
        return results
    
    def _estimate_confidence(self, tool_name: str, result: Any) -> float:
        """Estimate confidence level of a tool result."""
        # Basic heuristics for confidence estimation
        if isinstance(result, dict) and "error" in result:
            return 0.0
        
        if result is None or result == "":
            return 0.1
        
        # Tool-specific confidence estimation
        if "search" in tool_name.lower():
            if isinstance(result, list) and len(result) > 0:
                return 0.8  # Search results are generally reliable
            return 0.3
        
        if "file" in tool_name.lower() or "read" in tool_name.lower():
            return 0.9  # File operations are highly reliable
        
        if "api" in tool_name.lower() or "request" in tool_name.lower():
            return 0.7  # API calls are generally reliable
        
        # Default confidence
        return 0.6
    
    def _should_continue_research(self, results: List[ResearchResult], iteration: int) -> bool:
        """Determine if more research is needed."""
        if iteration >= self.max_execution_depth:
            return False
        
        if self.execution_strategy == "quick":
            return len(results) < 2
        elif self.execution_strategy == "focused":
            return len(results) < 3
        elif self.execution_strategy == "comprehensive":
            return len(results) < 5
        else:  # adaptive
            unique_sources = len(set(r.tool_name for r in results))
            return unique_sources < 2 and len(results) < 3
    
    async def run(self, input_message: Union[str, Message], **kwargs: Any) -> Message:
        """
        Execute advanced research based on user input.
        """
        # Reset state for new research session
        self.used_tools.clear()
        self.failed_tools.clear()
        
        if isinstance(input_message, str):
            current_user_message = Message(role="user", content=input_message)
        elif isinstance(input_message, Message):
            current_user_message = input_message
        else:
            return Message(role="assistant", content="Error: Invalid input type provided to research agent.")
        
        await self.memory.add_message(current_user_message)
        
        template_vars = kwargs.get("template_vars", {})
        template_vars["execution_strategy"] = self.execution_strategy
        
        available_tools = self._get_all_available_tool_definitions()
        
        if not available_tools:
            return Message(
                role="assistant", 
                content="I don't have any research tools available. Please connect tools to enable research capabilities."
            )
        
        # Create research plan
        research_plan = await self._analyze_and_plan_research(current_user_message.content, available_tools)
        logger.info(f"Research plan created: {research_plan.to_dict()}")
        
        all_research_results: List[ResearchResult] = []
        iteration = 0
        
        while iteration < self.max_execution_depth:
            history = await self.memory.get_history(limit=15)
            messages_for_llm: List[Message] = []
            
            # Add system message with research context
            system_message = self._render_system_prompt(**template_vars)
            if system_message:
                messages_for_llm.append(system_message)
            
            # Add research progress context
            if all_research_results:
                context_msg = Message(
                    role="system",
                    content=f"""Progress (Iteration {iteration + 1}/{self.max_execution_depth}):
- Tools used: {list(self.used_tools)}
- Tools failed: {list(self.failed_tools)}
- Results gathered: {len(all_research_results)}
- Useful results: {len([r for r in all_research_results if r.confidence >= 0.6])}

Previous findings summary:
{json.dumps([r.to_dict() for r in all_research_results[-5:]], indent=2)}"""
                )
                messages_for_llm.append(context_msg)
            
            messages_for_llm.extend(history)
            
            # Determine tool choice strategy
            if iteration >= self.max_execution_depth - 1:
                tool_choice = "none"  # Force final response
            elif not self._should_continue_research(all_research_results, iteration):
                tool_choice = "none"  # Sufficient information gathered
            else:
                tool_choice = "auto"
            
            llm_params = {
                "tools": [td.model_dump(exclude_none=True) for td in available_tools],
                "tool_choice": tool_choice,
                "temperature": 0.7
            }
            
            assistant_response = await self.llm.chat_completion(messages_for_llm, **llm_params)
            await self.memory.add_message(assistant_response)
            
            if not assistant_response.tool_calls:
                logger.info(f"Research complete after {iteration + 1} iterations with {len(all_research_results)} results")
                return self._post_process_llm_response(assistant_response)
            
            # Execute tool calls (parallel when possible)
            logger.info(f"Iteration {iteration + 1}: Executing {len(assistant_response.tool_calls)} tool calls")
            
            research_results = await self._execute_tools_parallel(assistant_response.tool_calls)
            all_research_results.extend(research_results)
            
            # Add tool responses to memory
            for i, (tool_call, result) in enumerate(zip(assistant_response.tool_calls, research_results)):
                tool_response = Message(
                    role="tool",
                    tool_call_id=tool_call.id,
                    name=result.tool_name,
                    content=json.dumps({
                        "result": result.result,
                        "confidence": result.confidence,
                        "timestamp": result.timestamp.isoformat()
                    })
                )
                await self.memory.add_message(tool_response)
            
            iteration += 1
        
        # Final synthesis with all research results
        synthesis_prompt = Message(
            role="system",
            content=f"""FINAL SYNTHESIS REQUIRED

Research Complete - Provide comprehensive response based on all gathered information:

Total Results: {len(all_research_results)}
High Confidence Results: {len([r for r in all_research_results if r.confidence >= self.confidence_threshold])}
Tools Used: {list(self.used_tools)}

Requirements:
1. Synthesize all findings into a coherent response
2. Include confidence indicators and source attribution
3. Acknowledge any limitations or gaps
4. Structure with clear sections
5. Highlight key insights and evidence"""
        )
        
        final_history = await self.memory.get_history(limit=20)
        final_messages = [synthesis_prompt] + final_history
        
        final_response = await self.llm.chat_completion(final_messages, temperature=0.6)
        
        return self._post_process_llm_response(final_response)


def register_research_agent(app: TFrameXApp):
    """Register the Research Agent with advanced capabilities."""
    
    research_agent_prompt = """You are an advanced AI research assistant that helps users by intelligently gathering and analyzing information using available tools.

Your capabilities:
- Analyze queries to understand information needs
- Create structured research plans
- Execute tools strategically (in parallel when beneficial)
- Synthesize findings from multiple sources
- Provide confidence scores and source attribution
- Adapt research depth based on query complexity

Available tools:
{available_tools_descriptions}

Available agents you can call:
{available_agents_descriptions}

Execution Strategy: {execution_strategy}
- adaptive: Adjust approach based on query complexity and available tools
- comprehensive: Gather extensive information from multiple sources with high confidence
- focused: Target specific information needs efficiently with medium confidence
- quick: Get essential information with minimal tool calls and basic confidence

Research Process:
1. ANALYZE the query to identify key information needs
2. PLAN tool usage considering parallel execution opportunities
3. EXECUTE tools strategically, starting with highest-value sources
4. EVALUATE results for completeness and confidence
5. SYNTHESIZE findings into a comprehensive, well-sourced response

Guidelines:
- Always cite sources when available
- Provide confidence indicators for key findings
- Acknowledge limitations or gaps in information
- Use parallel execution for independent research tasks
- Avoid redundant tool calls through intelligent caching
- Structure responses with clear sections and evidence
- Progressively build understanding through iterative research

Quality Standards:
- High confidence (>0.8): Multiple sources confirm findings
- Medium confidence (0.5-0.8): Single reliable source or partial confirmation
- Low confidence (<0.5): Uncertain or conflicting information

Current Context:
{current_flow_state_context}

Remember to provide comprehensive, well-researched responses that cite sources and indicate confidence levels for key findings.
"""

    @app.agent(
        name="SmartResearchAgent",
        description="Adaptive research agent that balances speed and thoroughness. Automatically adjusts its approach based on query complexity.",
        system_prompt=research_agent_prompt,
        agent_class=ResearchAgent,
        can_use_tools=True,
        max_execution_depth=4,
        execution_strategy="adaptive",
        enable_parallel_execution=True,
        cache_results=True,
        strip_think_tags=True
    )
    async def _research_agent_placeholder():
        """
        General-purpose tool-using agent for various tasks.
        
        Key Features:
        - Dynamic task analysis and planning
        - Parallel tool execution for efficiency
        - Result caching and intelligent reuse
        - Adaptive execution depth based on task complexity
        - Robust error handling and alternative strategies
        
        Execution Strategies:
        - adaptive: Smart approach based on task and available tools
        - comprehensive: Thorough approach with multiple tools
        - focused: Targeted approach for specific objectives
        - quick: Fast approach with minimal tool usage
        
        Works with any available tools:
        - Web search and scraping tools
        - File processing tools
        - Data analysis tools
        - Code execution tools
        - Text processing tools
        """
        pass

    # Register a faster variant for quick responses
    @app.agent(
        name="QuickResearchAgent",
        description="Fast research agent that provides quick answers using minimal tool calls. Best for simple queries or when speed is important.",
        system_prompt=research_agent_prompt,
        agent_class=ResearchAgent,
        can_use_tools=True,
        max_execution_depth=2,
        execution_strategy="quick",
        enable_parallel_execution=True,
        cache_results=True,
        strip_think_tags=True
    )
    async def _quick_researcher_placeholder():
        """Quick research variant optimized for speed with minimal tool usage."""
        pass

    @app.agent(
        name="DeepResearchAgent", 
        description="Thorough research agent that gathers comprehensive information from multiple sources. Best for complex queries requiring detailed analysis.",
        system_prompt=research_agent_prompt,
        agent_class=ResearchAgent,
        can_use_tools=True,
        max_execution_depth=6,
        execution_strategy="comprehensive",
        enable_parallel_execution=True,
        cache_results=True,
        strip_think_tags=True
    )
    async def _deep_researcher_placeholder():
        """Deep research variant for thorough analysis with extensive tool usage."""
        pass