# fairlib.modules.agent/multi_agent_runner.py
"""
================================================================================
                    Hierarchical Multi-Agent Orchestrator
================================================================================

**Purpose:**
This module implements an advanced, hierarchical multi-agent collaboration pattern,
often referred to as the "manager-worker" or "dispatcher" model. This pattern is
designed for solving complex problems that require multiple, distinct steps or
areas of expertise that would be difficult for a single agent to handle alone.

**How it Works:**
The system is composed of a central "manager" agent that acts as a project
lead or dispatcher. The manager analyzes a complex task, breaks it down into
smaller, logical sub-tasks, and delegates each sub-task to a specialized
"worker" agent. The workers execute their tasks and report the results back to
the manager, who then synthesizes the information into a final, comprehensive
answer.

This approach mimics how effective human teams operate and leads to more robust
and reliable solutions for complex problems.

**Key Components in this Module:**
1.  **`ManagerPlanner`:** A specialized planner for the manager agent. Its sole
    purpose is to instruct the manager on how to delegate tasks. It uses a
    custom prompt designed to make the LLM think like a dispatcher.

2.  **`HierarchicalAgentRunner`:** The central orchestrator that manages the
    entire workflow. It sits above the manager and the workers, passing tasks
    down and routing results back up, ensuring the collaborative process runs
    smoothly.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Union, Tuple

# --- Core Framework Imports ---
from fairlib.core.interfaces.llm import AbstractChatModel
from fairlib.core.interfaces.planner import AbstractPlanner
from fairlib.core.base_agent import BaseAgent
from fairlib.core.message import Message, Thought, Action, FinalAnswer

# --- Prompt Engineering Imports ---
from fairlib.core.prompts import (
    PromptBuilder,
    RoleDefinition,
    FormatInstruction,
    Example
)

logger = logging.getLogger(__name__)


def _create_default_manager_prompt_builder() -> PromptBuilder:
    """
    Creates a robust, algorithm-driven prompt builder for the ManagerPlanner.
    """
    builder = PromptBuilder()
    builder.role_definition = RoleDefinition(
        "You are a manager agent. Your job is to analyze a user's request and delegate sub-tasks to your team of worker agents until the request is fully answered. You must follow the decision process and format rules perfectly."
    )
    builder.format_instructions.extend([
        FormatInstruction(
            "# --- RESPONSE FORMAT ---\n"
            "Your response MUST contain EXACTLY ONE 'Thought' and ONE 'Action' block.\n"
            "The Action MUST be a single JSON object with 'tool_name' and 'tool_input'."
        ),
        FormatInstruction(
            "# --- YOUR DECISION PROCESS ---\n"
            "On every turn, you must follow these steps:\n"
            "1. Look at the original 'User Request' to understand the overall goal.\n"
            "2. Look at the MOST RECENT message in the history. It will be a 'Tool Observation' from a worker if you have delegated a task.\n"
            "3. **Decide:** Based on the observation and the overall goal, what is the very next logical step? \n"
            "   - If you need more information to meet the goal, delegate the next sub-task to the correct worker.\n"
            "   - If the observation gives you all the information needed to complete the goal, use the 'final_answer' tool to provide the complete, synthesized answer."
        )
    ])
    builder.examples.append(
        Example(
            "User Request: Find the current price of gold and calculate how much 10 ounces would cost.\n\n"
            "Thought: The user request has two parts. I must delegate the FIRST step. The 'Researcher' is best for finding prices.\n"
            "Action: {\"tool_name\": \"delegate\", \"tool_input\": {\"worker_name\": \"Researcher\", \"task\": \"Find the current price of one ounce of gold.\"}}\n\n"
            "Tool Observation: Result from Researcher: The current price of one ounce of gold is $2,300.\n\n"
            "Thought: I have the price. I must delegate the NEXT step. The 'Analyst' is best for calculations.\n"
            "Action: {\"tool_name\": \"delegate\", \"tool_input\": {\"worker_name\": \"Analyst\", \"task\": \"Calculate 2300 * 10.\"}}\n\n"
            "Tool Observation: Result from Analyst: The result of '2300 * 10' is 23000.\n\n"
            "Thought: I have all the pieces. I will synthesize the final answer.\n"
            "Action: {\"tool_name\": \"final_answer\", \"tool_input\": \"Based on the current price of $2,300 per ounce, 10 ounces of gold would cost $23,000.\"}"
        )
    )
    return builder


class ManagerPlanner(AbstractPlanner):
    """
    A specialized planner for a manager agent that delegates tasks.
    This version uses robust JSON parsing and is truly asynchronous.
    """
    def __init__(self, llm: AbstractChatModel,
                 workers: Dict[str, BaseAgent], 
                 prompt_builder: PromptBuilder = None):
        self.llm = llm
        self.workers = workers
        self.prompt_builder = prompt_builder or _create_default_manager_prompt_builder()

    async def aplan(self, history: List[Message], user_input: str) -> Union[FinalAnswer, Tuple[Thought, Action]]:
        """
        Asynchronously generates the manager's next plan.
        """
        local_builder = self.prompt_builder.clone()
        local_builder.add_worker_dict(self.workers)
        messages = local_builder.build_message_list(history, user_input)
        
        # Use the proper async LLM call
        response_message = await self.llm.ainvoke(messages)
        
        # Use the robust JSON parser
        return self._parse_json_response(response_message.content)

    def plan(self, history: List[Message], user_input: str) -> Union[FinalAnswer, Tuple[Thought, Action]]:
        """Synchronous wrapper for aplan."""
        return asyncio.run(self.aplan(history, user_input))

    def _parse_json_response(self, response_text: str) -> Union[FinalAnswer, Tuple[Thought, Action]]:
        """
        Parses the raw JSON response from the LLM, assuming the entire response
        is a JSON object, with a fallback for conversational answers.
        """
        print(f"\n\nMANAGER STRING: {response_text}\n\n")
        try:
            # First, try to find a JSON blob in the text, as manager prompts
            # can sometimes elicit conversational text before the JSON.
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in the response.")
        
            action_json_str = json_match.group(0)
            thought_text = response_text.split(action_json_str)[0].strip()
            thought_text = re.sub(r'\*?\s*Thought\s*\*?:\s*', '', thought_text, flags=re.IGNORECASE).strip()
            action_data = json.loads(action_json_str)

            if thought_text:    
                tool_name = action_data.get("tool_name")
                tool_input = action_data.get("tool_input")
                if not tool_name or tool_input is None:
                    raise KeyError("Parsed action JSON is missing 'tool_name' or 'tool_input'.")
            else:
                # CODE ADDED BECAUSE MANAGER OUTPUT ISN'T ALWAYS CORRECT
                # Sometimes returns thought action as a json response, as opposed to Thought: blah blah \n Action: {blah blah} \n
                thought_json = action_data.get("Thought")
                action_json = action_data.get("Action")

                if not thought_json or action_json is None:
                    raise KeyError("Parsed response text is formatted incorrectly.")
                else:
                    tool_name = action_json.get("tool_name")
                    tool_input = action_json.get("tool_input")
                    thought_text = thought_json
                    
                if not tool_name or tool_input is None:
                    raise KeyError("Parsed action JSON is missing 'tool_name' or 'tool_input'.")
                
            # Manager will sometimes use a worker as a tool instead of delegating to it
            if(tool_name.lower() != "delegate"):
                print("TRIED TO USE A WORKER AS A TOOL")
                input = {"worker_name":tool_name, "task":tool_input}
                tool_name = "delegate"
                tool_input = input
            # =======================================================

            print(f"\n\nPARSED OUTPUT- toolname = {tool_name} toolinput = {tool_input}\n\n")
            thought = Thought(text=thought_text if thought_text else "No thought provided.")
            
            if tool_name == "final_answer":
                return FinalAnswer(text=str(tool_input))
                
            return thought, Action(tool_name=tool_name, tool_input=tool_input)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"ManagerPlanner could not parse response due to '{e}'. Treating as Final Answer. Response: '{response_text}'"
            )
            return FinalAnswer(text=response_text)


class HierarchicalAgentRunner:
    """Orchestrates a team of agents with a central manager and multiple workers."""
    def __init__(self, manager_agent: BaseAgent, workers: Dict[str, BaseAgent], max_steps: int = 15):
        self.manager = manager_agent
        self.workers = workers
        self.max_steps = max_steps
        
    async def arun(self, user_input: str) -> str:
        """Runs the hierarchical multi-agent workflow from start to finish."""
        logger.info(f"\n--- Running Hierarchical Team for Request: '{user_input}' ---")
        self.manager.memory.add_message(Message(role="user", content=user_input))
        
        current_request = user_input

        for i in range(self.max_steps):
            logger.info(f"\n--- Manager Turn {i+1}/{self.max_steps} ---")
            
            plan_result = await self.manager.planner.aplan(self.manager.memory.get_history(), current_request)

            if isinstance(plan_result, FinalAnswer):
                logger.info(f"Manager has concluded the task with a final answer.")
                return plan_result.text

            thought, action = plan_result
            self.manager.memory.add_message(Message(role="assistant", content=thought.text))
            logger.info(f"Manager Thought: {thought.text}")

            if action.tool_name == "delegate":
                if not isinstance(action.tool_input, dict):
                    error_msg = f"Error: Manager's delegate input was not a valid dictionary."
                    self.manager.memory.add_message(Message(role="tool", content=error_msg, name="delegate"))
                    continue
                worker_name = action.tool_input.get("worker_name")
                task = action.tool_input.get("task")
                
                if worker_name in self.workers and task:
                    logger.info(f"Manager Action: Delegating task to '{worker_name}': '{task}'")
                    worker = self.workers[worker_name]
                    worker_result = await worker.arun(task)
                    observation = f"Result from {worker_name}: {worker_result}"
                    logger.info(f"Observation for Manager: {observation}")
                    # Use the 'system' role to provide observations from workers
                    self.manager.memory.add_message(Message(role="system", content=observation))

                else:
                    error_msg = f"Error: Manager delegation failed. Worker '{worker_name}' not found or task not specified."
                    logger.error(error_msg)
                    self.manager.memory.add_message(Message(role="tool", content=error_msg, name="delegate"))
            else:
                error_msg = f"Error: Manager attempted an invalid action '{action.tool_name}'."
                logger.error(error_msg)
                self.manager.memory.add_message(Message(role="tool", content=error_msg, name="delegate"))
            
            current_request = ""

        logger.warning("Agent team stopped after reaching max steps.")
        return "The team could not complete the request in the maximum number of steps."


if __name__ == "__main__":
    planner = ManagerPlanner(None, None)

    planner._parse_json_response('Thought: Proceed to obtain Fairbanks hotel options for the remaining 7 nights (2026-01-20 to 2026-01-27) for 3 adults, city-wide search, mid-range to upscale with hiking/outdoor access in mind, so I can select a pairing after reviewing options. Action: {"tool_name": "hotel_researcher", "tool_input": "Search Fairbanks hotels for 7 nights (check-in 2026-01-20, check-out 2026-01-27) for 3 adults, city-wide (no neighborhoods), mid-range to upscale, with good access to hiking and outdoor activities."}')