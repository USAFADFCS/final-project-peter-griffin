# travel_agent.py
"""
This script demonstrates how to assemble a single intelligent agent that can reason,
respond, and use tools in a mathematically rich environment.

The agent supports:
    1. Basic arithmetic calculations using SafeCalculatorTool
    2. Symbolic calculus operations (derivatives and integrals) using AdvancedCalculusTool

This serves as a practical tutorial for combining multiple tools under the FAIR-LLM framework.
"""
import asyncio
import os

# --- Step 1: Import necessary framework components ---
from fairlib import (
    ToolRegistry,
    ToolExecutor,
    WorkingMemory,
    SimpleAgent,
    RoleDefinition, 
    HuggingFaceAdapter,
    SimpleReActPlanner
)

# --- Step 2: Import the additiojnal tools we want this agent to use ---
# NOTE: SafeCalculatorTool is a built-in tool while AdvancedCalculusTool 
# is a tool we built to extend beyond our basic built-in tools.
from hotel_tool import HotelTool
from flight_tool import FlightTool

async def main():
    """
    Main entry point for the demo agent.
    This sets up the brain, memory, planner, tools, and interaction loop.
    """
    print("🔧 Initializing the Flight Tool + Flight Agent...")

    # === (a) Brain: Language Model ===
    # Uses dolphin3-qwen25-3b for reasoning and decision making
    llm = HuggingFaceAdapter("dolphin3-qwen25-3b", auth_token=os.getenv("HF_WRITE_TOKEN"))
    
    # === (b) Toolbelt: Register both calculator and calculus tools ===
    tool_registry = ToolRegistry()

    flight_tool = FlightTool()
    hotel_tool = HotelTool()

    # Register tools with the registry
    tool_registry.register_tool(flight_tool)
    tool_registry.register_tool(hotel_tool)

    print(f"✅ Registered tools: {[tool.name for tool in tool_registry.get_all_tools().values()]}")

    # === (c) Hands: Tool Executor ===
    executor = ToolExecutor(tool_registry)

    # === (d) Memory: Conversation Context ===
    memory = WorkingMemory()

    # === (e) Mind: Reasoning Engine ===
    #planner = ReActPlanner(llm, tool_registry)
        # For use with simple, local models
    
    planner = SimpleReActPlanner(llm, tool_registry)

    # modify the default role a bit:
    planner.prompt_builder.role_definition = \
    RoleDefinition(
        "You are an advanced travel agent whose job it is to find the best flights.\n"
        "You must adhere to the user's constraints for time, budget, and destinations."
    )

    # === (f) Assemble the Agent ===
    agent = SimpleAgent(
        llm=llm,
        planner=planner,
        tool_executor=executor,
        memory=memory,
        max_steps=10  # Limit reasoning loops to prevent runaway execution
    )

    print("🎓 Agent is ready to work.")
    print("💬 You can enter origin, destination, departure date, and max price.")

    # === (g) Interaction Loop ===
    while True:
        try:
            user_input = input("👤 You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("🤖 Agent: Goodbye! 👋")
                break

            # Run the agent’s full Reason+Act cycle
            agent_response = await agent.arun(user_input)
            print(f"🤖 Agent: {agent_response}")

        except KeyboardInterrupt:
            print("\n🤖 Agent: Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Agent error: {e}")


# Entrypoint for script execution
if __name__ == "__main__":
    asyncio.run(main())
