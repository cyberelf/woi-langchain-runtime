#!/usr/bin/env python3
"""
Command line example for using the Simple Test Agent.

This demonstrates how to use the new template agent system with the simplified LLM interface.
"""

import asyncio
import sys
from typing import Optional

from runtime.llm.langgraph import LangGraphLLMService, get_langgraph_llm_service
from runtime.models import AgentCreateRequest, ChatMessage, MessageRole
from runtime.template_agent.langgraph.simple import SimpleTestAgent
from runtime.toolset.langgraph import get_toolset_service


async def main():
    """Run the simple agent CLI example."""
    
    # Create agent configuration
    agent_data = AgentCreateRequest(
        id="simple-test-example",
        name="Simple Test CLI Agent",
        description="A simple test agent for CLI demonstration",
        type="simple-test",
        template_id="simple-test",
        template_version_id="1.0.0",
        template_config={
            "response_prefix": "🤖 ",
            "system_prompt": "You are a helpful assistant that responds to user questions."
        },
        system_prompt="You are a helpful assistant that responds to user questions.",
        llm_config_id="deepseek",
        toolsets=[],
        conversation_config={}
    )

    # get services
    llm_service = get_langgraph_llm_service()
    toolset_service = get_toolset_service()
    
    # Create agent instance
    print("Creating Simple Test Agent...")
    agent = SimpleTestAgent.create_instance(agent_data, llm_service, toolset_service)
    
    print(f"Agent created: {agent.name}")
    print(f"Template: {agent.template_name} v{agent.template_version}")
    print(f"Description: {agent.template_description}")
    print()
    
    # Interactive CLI loop
    print("Enter your messages (type 'exit' to quit, 'stream' to toggle streaming):")
    print("=" * 50)
    
    streaming = False
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            if user_input.lower() == 'stream':
                streaming = not streaming
                print(f"Streaming mode: {'ON' if streaming else 'OFF'}")
                continue
            
            if not user_input:
                continue
            
            # Create message
            message = ChatMessage(role=MessageRole.USER, content=user_input)
            conversation_history.append(message)
            
            # Execute agent
            print(f"\nAgent ({streaming and 'streaming' or 'standard'}):", end="")
            
            if streaming:
                # Stream response
                print(" ", end="")
                async for chunk in agent.stream_execute(conversation_history):
                    if chunk.choices and chunk.choices[0].get("delta", {}).get("content"):
                        content = chunk.choices[0]["delta"]["content"]
                        print(content, end="", flush=True)
                print()  # New line after streaming
            else:
                # Regular response
                response = await agent.execute(conversation_history)
                content = response.choices[0].message.content
                print(f" {content}")
                
                # Add response to history
                conversation_history.append(
                    ChatMessage(role=MessageRole.ASSISTANT, content=content)
                )
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == "__main__":
    # Check if we need to provide OpenAI API key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-api-key-here'")
        print()
    
    asyncio.run(main()) 