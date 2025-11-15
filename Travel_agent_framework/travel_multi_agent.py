import asyncio
import os



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

from dotenv import load_dotenv
load_dotenv()

# LOAD API KEYS AND SETTNGS FROM ENV VARS
settings.api_keys.openai_api_key = os.getenv("OPENAI_API_KEY")

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


async def main():
    """
    The main function to set up and run the multi-agent system.
    """
    

    # --- Step 2: Initialize Core Components ---
    print("\n📚 Initializing fairlib.core.components...")
    llm = OpenAIAdapter(
        api_key=settings.api_keys.openai_api_key,
        model_name="gpt-5-nano"
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
        "A research agent that uses a flight tool to find current, real-time information on flights."
    )
    print("   ✓ Flight Researcher agent created")
    
    # Hotel researcher
    hotel_researcher = create_agent(
        llm, 
        [hotel_tool],
        "A research agent that uses a hotel tool to find current, real-time information on hotel options."
    )
    print("   ✓ Flight Researcher agent created")

    # The Analyst: Its only tool is the SafeCalculator
    analyst = create_agent(
        llm,
        [SafeCalculatorTool()],
        "An analyst agent that performs mathematical calculations using a safe calculator."
    )
    print("   ✓ Analyst agent created")



    # We organize the workers in a dictionary so the manager can find them by name.
    workers = {"Flight_researcher": flight_researcher, "Analyst": analyst, "Hotel_researcher": hotel_researcher}

    # --- Step 4: Create the Manager Agent ---
    manager_memory = WorkingMemory()
    manager_planner = ManagerPlanner(llm, workers)
    manager_agent = SimpleAgent(llm, manager_planner, None, manager_memory)
    print("   ✓ Manager agent created")

    # --- Step 5: Initialize the Hierarchical Runner ---
    team_runner = HierarchicalAgentRunner(manager_agent, workers)
    print("\n🚀 Agent team ready!\n")
    
    # === (g) Interaction Loop ===
    # Please plan me a week long trip to Berlin starting December 22nd. I want you to find flights, hotels, and general activities to do while there. I'm leaving from Boston and want the flight and hotel costs to be reasonable. 
    while True:
        try:
            user_input = input("👤 You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("🤖 Agent: Goodbye! 👋")
                break

            # Run the agent’s full Reason+Act cycle
            agent_response = await team_runner.arun(user_input)
            print(f"🤖 Agent: {agent_response}")

        except KeyboardInterrupt:
            print("\n🤖 Agent: Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Agent error: {e}")



if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())