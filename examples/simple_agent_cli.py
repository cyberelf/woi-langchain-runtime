#!/usr/bin/env python3
"""
Command line example for using the Simple Test Agent with the new Client SDK.

This demonstrates how to use the client SDK to interact with agents through
the runtime system.
"""

import asyncio
import dotenv
import os

from client_sdk import RuntimeClientContext, CreateAgentRequest, ChatMessage, MessageRole

dotenv.load_dotenv()

async def main():
    """Run the simple agent CLI example using the client SDK."""
    base_url = os.getenv("RUNTIME_BASE_URL", "http://localhost:8000/v1/")
    api_key = os.getenv("RUNTIME_TOKEN")

    async with RuntimeClientContext(base_url=base_url, api_key=api_key) as client:
        print("🚀 Simple Agent CLI Example (using Client SDK)")
        print("=" * 60)
        
        # List available templates
        print("\n📋 Available Templates:")
        templates = await client.list_templates()
        for template in templates:
            print(f"  • {template.id} v{template.version} ({template.framework})")
            print(f"    {template.description}")
        
        print(f"\nFound {len(templates)} template(s)")
        
        # Check if we have the simple-test template
        simple_template = None
        for template in templates:
            if template.id == "simple-test":
                simple_template = template
                break
        
        if not simple_template:
            print("\n❌ Simple test template not found. Creating agent with default template...")
            # Use the first available template as fallback
            if templates:
                simple_template = templates[0]
                print(f"   Using template: {simple_template.id}")
            else:
                print("❌ No templates available. Cannot proceed.")
                return
        
        # Check existing agents
        print("\n🤖 Existing Agents:")
        agents = await client.list_agents()
        if agents:
            for agent in agents:
                print(f"  • {agent.agent_id} ({agent.name}) - {agent.template_id}")
        else:
            print("  No existing agents found")
        
        # Create or use existing agent
        agent_id = "simple-test-example"
        existing_agent = None
        
        for agent in agents:
            if agent.agent_id == agent_id:
                existing_agent = agent
                break
        
        if existing_agent:
            print(f"\n✅ Using existing agent: {existing_agent.name}")
            agent_info = existing_agent
        else:
            print("\n🔧 Creating new agent...")
            
            # Create agent configuration
            agent_data = CreateAgentRequest(
                id=agent_id,
                name="Simple Test CLI Agent",
                description="A simple test agent for CLI demonstration",
                avatar_url=None,
                template_id=simple_template.id,
                template_version_id=simple_template.version,  # Updated: removed template_version
                template_config={
                    "response_prefix": "🤖 ",
                    "system_prompt": "You are a helpful assistant that responds to user questions."
                },
                system_prompt="You are a helpful assistant that responds to user questions.",
                llm_config_id="deepseek",
                toolsets=[],
                conversation_config={},
                agent_line_id=None,  # Will be auto-populated from id by validator
                version_type="beta",
                version_number="v1", 
                owner_id="cli-example",  # Optional but provided
                status="draft"
            )
            
            # Create agent using client SDK
            agent_info = await client.create_agent(agent_data)
            print(f"✅ Agent created: {agent_info.name}")
        
        print("\n🎯 Agent Details:")
        print(f"   ID: {agent_info.agent_id}")
        print(f"   Name: {agent_info.name}")
        print(f"   Template: {agent_info.template_id} v{agent_info.template_version}")
        print(f"   Status: {agent_info.status}")
        
        # Interactive CLI loop
        print("\n💬 Interactive Chat Session")
        print("Commands:")
        print("  'exit' - Exit the chat")
        print("  'stream' - Toggle streaming mode")
        print("  'clear' - Clear conversation history")
        print("=" * 60)
        
        streaming = False
        conversation_history = []

        # task and context id
        task_id = None
        context_id = None
        
        while True:
            try:
                # Get user input
                user_input = input(f"\n{'You'}: ").strip()
                
                if user_input.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'stream':
                    streaming = not streaming
                    print(f"🌊 Streaming mode: {'ON' if streaming else 'OFF'}")
                    continue
                
                if user_input.lower() == 'clear':
                    conversation_history = []
                    print("🧹 Conversation history cleared")
                    continue
                
                if not user_input:
                    continue
                
                # Create message
                message = ChatMessage(role=MessageRole.USER, content=user_input)
                conversation_history.append(message)
                
                # Execute agent using client SDK
                agent_name = agent_info.name
                
                if streaming:
                    # Stream response
                    print(f"{agent_name}: ", end="", flush=True)
                    response_content = ""
                    stream = client.stream_chat_with_agent(
                        agent_info.agent_id, conversation_history
                    )
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            response_content += content
                            print(content, end="", flush=True)
                    print()  # New line after streaming
                    
                    # Add response to history
                    if response_content:
                        conversation_history.append(
                            ChatMessage(role=MessageRole.ASSISTANT, content=response_content)
                        )
                else:
                    # Regular response
                    response = await client.chat_with_agent(agent_info.agent_id, conversation_history)
                    content = response.choices[0].message.content
                    print(f"{agent_name}: {content}")
                    
                    # Add response to history
                    conversation_history.append(
                        ChatMessage(role=MessageRole.ASSISTANT, content=content)
                    )
            
            except KeyboardInterrupt:
                print("\n\n👋 Exiting...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again.")


if __name__ == "__main__":
    # Check if we need to provide OpenAI API key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-api-key-here'")
        print()
    
    asyncio.run(main()) 