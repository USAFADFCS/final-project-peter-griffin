import asyncio
import os
import json
import sys

os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding='utf-8')

# --- Step 1: Import all necessary components ---
from fairlib import (
    settings,
    OpenAIAdapter,
    ToolRegistry,
    SafeCalculatorTool,
    WebSearcherTool,
    ToolExecutor,
    WorkingMemory,
    ReActPlanner,
    SimpleAgent,
    ManagerPlanner,
    HierarchicalAgentRunner
)
from hotel_tool import HotelTool
from flight_tool import FlightTool

# LOAD API KEYS AND SETTNGS FROM ENV VARS
from dotenv import load_dotenv
load_dotenv()
settings.api_keys.openai_api_key = os.getenv("OPENAI_API_KEY")

# helper function to create agents to work for the manager
# written by fairllm in the demo_multi_agent.py
def create_agent(llm, tools, role_description):
    """
    A helper factory function to simplify the creation of worker agents.
    Each agent gets its own tool registry, planner, executor, and memory.
    """
    tool_registry = ToolRegistry()
    for tool in tools:
        tool_registry.register_tool(tool)
    
    planner = ReActPlanner(llm, tool_registry)
    executor = ToolExecutor(tool_registry)
    memory = WorkingMemory()
    
    # create a stateless agent
    agent = SimpleAgent(llm, planner, executor, memory, stateless=True)

    # This custom attribute helps the manager understand the worker's purpose.
    agent.role_description = role_description
    return agent

# main function to set up agents and produce an itinerary
async def main():
    """
    The main function to set up and run the multi-agent system.
    """
    

    # --- Step 2: Initialize Core Components ---
    print("\n📚 Initializing fairlib.core.components...")
    llm = OpenAIAdapter(
        api_key=settings.api_keys.openai_api_key,
        model_name="gpt-4.1-2025-04-14"
    )

    # --- Step 3: Create Specialized Worker Agents ---
    print("👥 Building the agent team...")
    
    # The get_web_searcher_tool function automatically chooses the right implementation

    flight_tool = FlightTool()
    hotel_tool = HotelTool()
    
    # The Researcher: Its only tool is the flight tool
    flight_researcher = create_agent(
        llm, 
        [flight_tool],
        "A research agent that uses a flight tool to find current, real-time information on flights. If you cannot meet set requirements you will return the closest options."
    )
    print("   ✓ Flight Researcher agent created")
    
    # Hotel researcher
    hotel_researcher = create_agent(
        llm, 
        [hotel_tool],
        "A research agent that uses a hotel tool to find current, real-time information on hotel options given a city and dates. Cannot search for specific neighborhoods"
    )
    print("   ✓ Hotel Researcher agent created")

    # The Analyst: Its only tool is the SafeCalculator
    analyst = create_agent(
        llm,
        [SafeCalculatorTool()],
        "An analyst agent that performs mathematical calculations using a safe calculator. Numbers and exchange rates must be directly provided to the analyst to make calculations."
    )
    print("   ✓ Analyst agent created")
    

    # We organize the workers in a dictionary so the manager can find them by name.
    workers = {"flight_researcher": flight_researcher, "Analyst": analyst, "hotel_researcher": hotel_researcher}

    # --- Step 4: Create the Manager Agent ---
    manager_memory = WorkingMemory()
    manager_planner = ManagerPlanner(llm, workers)
    manager_tool_registry = ToolRegistry()
    manager_tool_registry.register_tool(FlightTool())
    manager_tool_registry.register_tool(HotelTool())
    manager_tool_registry.register_tool(SafeCalculatorTool())
    manager_executor = ToolExecutor(manager_tool_registry)
    manager_agent = SimpleAgent(llm, manager_planner, manager_executor, manager_memory)
    manager_agent.role_description = "The manager of a travel agency who helps people plan vacations."
    print("   ✓ Manager agent created")

    # --- Step 5: Initialize the Hierarchical Runner ---
    team_runner = HierarchicalAgentRunner(manager_agent, workers)
    print("\n🚀 Agent team ready!\n")
    
    # === (g) Interaction Loop ===
    #     try:
    #         user_input = input("👤 You: ")
    #         if user_input.lower() in ["exit", "quit"]:
    #             print("🤖 Agent: Goodbye! 👋")
    #             break

    #         # Run the agent’s full Reason+Act cycle
    #         agent_response = await team_runner.arun(user_input)
    #         print(f"🤖 Agent: {agent_response}")

    #     except KeyboardInterrupt:
    #         print("\n🤖 Agent: Session ended by user.")
    #         break
    #     except Exception as e:
    #         print(f"❌ Agent error: {e}")
    
    # ======== Prompt and response ==============
    user_request = input("Where do you want to go and when: ")
    workflow_steps = [
        "Delegate to the 'flight_researcher' to find flight options, pick a flight based on user constraints. The returned price will be for 1 adult, and so total cost will need to be calculated for more than one adult.",
        "Delegate to the the 'hotel_researcher' to find hotel options, pick a hotel based on user constraints. You WILL NOT request locations more specific than a city, DO NOT request specific neighboorhoods or attractions.",
        "Come up with activites for each day",
    ]
    master_prompt = f"""
    Coordinate with your team to produce a vacation plan for the user.\n
    Use the user's request as a guide for planning. If the request is specific you will follow their request, if it is non-specific you will still plan a specific trip based on their request, selecting locations and activities you believe the user will enjoy.\n 
    After locations have been selected
    for each location in the trip you will:\n
    {"".join([f"{i+1}. {step}\n" for i, step in enumerate(workflow_steps)])}
    You will then select one flight and hotel pairing for the trip\n
    Finally, Delegate to the analyst to calculate the total cost of flights (ensure you multiply the ticket cost by the number of travelers) and hotels (this means the tool name will be "delegate", and tool input will be json containing the "worker_name" and the "task", you WILL NOT attempt to use the Analyst as the tool name, this WILL NOT WORK). If the user defined a budget ensure the total price is within that, or the lowest cost flights and hotels were chosen if the user's budget is too low to be met.\n
    Then you will produce a easy to read, well formatted itinerary with flight info (including flight number), hotel info, and activites for each day of the trip.
    You will NOT produce conversational text or questions in the final answer, you will just include the information relevant to the trip.
    \n\n
    USER REQUEST:\n
    {user_request}
    """
    
    try:
        final_evaluation = await team_runner.arun(master_prompt)
        print("\n\n==============TRAVEL ITINERARY==============\n\n")
        print(final_evaluation)
    except Exception as e:
        print(json.dumps({"error": f"A an error occurred: {e}"}))



if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())