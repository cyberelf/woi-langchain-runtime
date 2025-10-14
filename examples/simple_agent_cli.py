#!/usr/bin/env python3
"""
Command line example for using agents with the new Client SDK.

This demonstrates how to use the client SDK to interact with agents through
the runtime system, supporting both simple and workflow agents with task management.
"""

import asyncio
import dotenv
import os

from client_sdk import RuntimeClientContext, CreateAgentRequest, ChatMessage, MessageRole

dotenv.load_dotenv()

async def main():
    """Run the agent CLI example using the client SDK."""
    base_url = os.getenv("RUNTIME_BASE_URL", "http://localhost:8000/v1/")
    api_key = os.getenv("RUNTIME_TOKEN")

    # Get timeout from env or use server default (300s)
    timeout = float(os.getenv("RUNTIME_CLIENT_TIMEOUT", "300"))

    async with RuntimeClientContext(base_url=base_url, api_key=api_key, timeout=timeout) as client:
        print(f"🚀 Agent CLI Example (using Client SDK, timeout={timeout}s)")
        print("=" * 60)
        
        # List available templates
        print("\n📋 Available Templates:")
        templates = await client.list_templates()
        for template in templates:
            print(f"  • {template.id} v{template.version} ({template.framework})")
            print(f"    {template.description}")
        
        print(f"\nFound {len(templates)} template(s)")
        
        # Let user select template type
        print("\n🔧 Select Agent Type:")
        print("  1. Simple Test Agent")
        print("  2. Workflow Agent")
        
        agent_type = input("\nEnter choice (1 or 2) [default: 1]: ").strip() or "1"
        
        if agent_type == "2":
            # Create workflow agent
            agent_id = "workflow-example"
            template_id = "langgraph-workflow"
            template_config = {
                "workflow_responsibility": "Analyzing and responding to technical questions about programming, coding, software development, and computer science topics. This workflow is designed for multi-step technical analysis and code generation tasks.",
                "steps": [
                    {
                        "name": "Step 1: Analyze Request",
                        "prompt": "Analyze the user's request and identify key requirements.",
                        "tools": [],
                        "timeout": 60 ,
                        "retry_count": 1
                    },
                    {
                        "name": "Step 2: Generate Response",
                        "prompt": "Generate a comprehensive response based on the analysis.",
                        "tools": [],
                        "timeout": 60,
                        "retry_count": 0
                    }
                ],
                "max_retries": 2,
                "step_timeout": 60,
                "fail_on_error": False
            }
            agent_name = "Workflow CLI Agent"
            agent_description = "A workflow agent for CLI demonstration"
            system_prompt = "You are a helpful workflow assistant that processes requests step by step."
        else:
            # Create simple test agent
            agent_id = "simple-test-example"
            template_id = "simple-test"
            template_config = {
                "response_prefix": "🤖 ",
                "system_prompt": "You are a helpful assistant that responds to user questions."
            }
            agent_name = "Simple Test CLI Agent"
            agent_description = "A simple test agent for CLI demonstration"
            system_prompt = "You are a helpful assistant that responds to user questions."
        
        # Check existing agents
        print("\n🤖 Existing Agents:")
        agents = await client.list_agents()
        if agents:
            for agent in agents:
                print(f"  • {agent.agent_id} ({agent.name}) - {agent.template_id}")
        else:
            print("  No existing agents found")
        
        # Create or use existing agent
        existing_agent = None
        
        for agent in agents:
            if agent.agent_id == agent_id:
                existing_agent = agent
                break
        
        if existing_agent:
            print(f"\n✅ Using existing agent: {existing_agent.name}")
            agent_info = existing_agent
        else:
            print(f"\n🔧 Creating new {agent_name}...")
            
            # Create agent configuration
            agent_data = CreateAgentRequest(
                id=agent_id,
                name=agent_name,
                description=agent_description,
                avatar_url=None,
                template_id=template_id,
                template_version_id="1.0.0",
                template_config=template_config,
                system_prompt=system_prompt,
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
        print("  'clear' - Clear conversation history and reset task")
        print("  'newtask' - Start a new task (resets task ID)")
        print("=" * 60)
        
        streaming = False
        conversation_history = []

        # task and context id for workflow agent
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
                    task_id = None
                    context_id = None
                    print("🧹 Conversation history cleared and task reset")
                    continue
                if user_input.lower() == 'newtask':
                    task_id = None
                    context_id = None
                    print("🆕 Task reset - next message will start a new task")
                    continue
                if not user_input:
                    continue
                # Create message
                message = ChatMessage(role=MessageRole.USER, content=user_input)
                conversation_history.append(message)
                # Prepare metadata with task_id and context_id
                metadata = {}
                if task_id:
                    metadata["task_id"] = task_id
                    print(f"\n[📋 Task ID: {task_id}]", flush=True)
                if context_id:
                    metadata["context_id"] = context_id
                    print(f"[🔗 Context ID: {context_id}]", flush=True)
                # Execute agent using client SDK
                agent_name = agent_info.name
                if streaming:
                    # Stream response
                    print(f"{agent_name}: ", end="", flush=True)
                    response_content = ""
                    stream = client.stream_chat_with_agent(
                        agent_info.agent_id,
                        conversation_history,
                        metadata=metadata if metadata else None
                    )
                    # Track task_id and context_id from every chunk (always update if present)
                    async for chunk in stream:
                        if hasattr(chunk, 'metadata') and chunk.metadata:
                            if 'task_id' in chunk.metadata:
                                if task_id != chunk.metadata['task_id']:
                                    task_id = chunk.metadata['task_id']
                                    print(f"\n[📋 Task ID: {task_id}]", flush=True)
                            if 'context_id' in chunk.metadata:
                                if context_id != chunk.metadata['context_id']:
                                    context_id = chunk.metadata['context_id']
                                    print(f"[🔗 Context ID: {context_id}]", flush=True)
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
                    response = await client.chat_with_agent(
                        agent_info.agent_id,
                        conversation_history,
                        metadata=metadata if metadata else None
                    )
                    content = response.choices[0].message.content
                    # Always update task_id/context_id from every response
                    if hasattr(response, 'metadata') and response.metadata:
                        if 'task_id' in response.metadata:
                            if task_id != response.metadata['task_id']:
                                task_id = response.metadata['task_id']
                                print(f"[📋 Task ID: {task_id}]")
                        if 'context_id' in response.metadata:
                            if context_id != response.metadata['context_id']:
                                context_id = response.metadata['context_id']
                                print(f"[🔗 Context ID: {context_id}]")
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