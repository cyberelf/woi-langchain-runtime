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
        
        # Ask user for mode: compose or manual
        print("\n🎯 Agent Creation Mode:")
        print("  1. Manual Configuration (traditional)")
        print("  2. AI-Powered Compose (let AI configure the agent)")
        mode_choice = input("Select mode (1-2) [default: 1]: ").strip() or "1"
        
        if mode_choice == "2":
            # AI Compose Mode
            print("\n✨ AI-Powered Agent Composition")
            print("=" * 60)
            
            # List available templates
            print("\n📋 Available Templates:")
            templates = await client.list_templates()
            if not templates:
                print("  ❌ No templates found. Please ensure the runtime is running.")
                return
                
            template_map = {}
            for idx, template in enumerate(templates, 1):
                print(f"  {idx}. {template.id} v{template.version} ({template.framework})")
                print(f"     {template.description}")
                template_map[str(idx)] = template
            
            print(f"\nFound {len(templates)} template(s)")
            
            # Let user select template
            print("\n🔧 Select Agent Template:")
            template_choice = input(f"Enter choice (1-{len(templates)}) [default: 1]: ").strip() or "1"
            
            if template_choice not in template_map:
                print(f"❌ Invalid choice. Defaulting to template 1.")
                template_choice = "1"
            
            selected_template = template_map[template_choice]
            template_id = selected_template.id
            
            # Get AI composition instructions
            print("\n💬 Describe the agent you want to create:")
            print("   (e.g., 'Create an agent that analyzes log files and identifies errors')")
            instructions = input("Instructions: ").strip()
            
            if not instructions:
                print("❌ Instructions cannot be empty")
                return
            
            # Optional: suggest name
            suggested_name = input("\nSuggested agent name (optional): ").strip() or None
            
            # Compose agent configuration
            print(f"\n🤖 Composing agent configuration with AI...")
            try:
                composed = await client.compose_agent(
                    template_id=template_id,
                    instructions=instructions,
                    suggested_name=suggested_name,
                    llm_config_id="deepseek"
                )
                
                # Display composed configuration
                print(f"\n✨ AI-Generated Agent Configuration:")
                print(f"   ID: {composed.agent_id}")
                print(f"   Name: {composed.name}")
                print(f"   Description: {composed.description}")
                print(f"\n📝 System Prompt:")
                print(f"   {composed.system_prompt[:200]}{'...' if len(composed.system_prompt) > 200 else ''}")
                if composed.toolsets:
                    print(f"\n🛠️  Tools: {', '.join(composed.toolsets)}")
                if composed.reasoning:
                    print(f"\n💭 AI Reasoning:")
                    print(f"   {composed.reasoning[:300]}{'...' if len(composed.reasoning) > 300 else ''}")
                
                # Confirm creation
                print("\n")
                confirm = input("Create agent with this configuration? (Y/n): ").strip().lower()
                if confirm and confirm != 'y':
                    print("❌ Agent creation cancelled")
                    return
                
                # Create the agent
                agent_data = CreateAgentRequest(
                    id=composed.agent_id,
                    name=composed.name,
                    description=composed.description,
                    avatar_url=None,
                    template_id=composed.template_id,
                    template_version_id=composed.template_version_id,
                    template_config=composed.template_config,
                    system_prompt=composed.system_prompt,
                    llm_config_id="deepseek",
                    toolsets=composed.toolsets,
                    conversation_config={},
                    agent_line_id=None,
                    version_type="beta",
                    version_number="v1", 
                    owner_id="cli-example",
                    status="draft"
                )
                
                agent_info = await client.create_agent(agent_data)
                print(f"\n✅ Agent created: {agent_info.name}")
                
            except Exception as e:
                print(f"\n❌ Composition failed: {e}")
                print("Falling back to manual mode...")
                mode_choice = "1"  # Fall back to manual mode
        
        if mode_choice == "1":
            # Manual Configuration Mode (existing code)
            # List available templates
            print("\n📋 Available Templates:")
            templates = await client.list_templates()
            if not templates:
                print("  ❌ No templates found. Please ensure the runtime is running.")
                return
                
            template_map = {}
            for idx, template in enumerate(templates, 1):
                print(f"  {idx}. {template.id} v{template.version} ({template.framework})")
                print(f"     {template.description}")
                template_map[str(idx)] = template
            
            print(f"\nFound {len(templates)} template(s)")
            
            # Let user select template type
            print("\n🔧 Select Agent Template:")
            template_choice = input(f"Enter choice (1-{len(templates)}) [default: 1]: ").strip() or "1"
            
            if template_choice not in template_map:
                print(f"❌ Invalid choice. Defaulting to template 1.")
                template_choice = "1"
            
            selected_template = template_map[template_choice]
            template_id = selected_template.id
            
            # Available tools for selection
            available_tools = [
                "read-lines",
                "create-file", 
                "grep-file",
                "delete-file",
                "fetch-url",
                "parse-url"
            ]
            
            print("\n🛠️  Available Tools:")
            print("  0. None (no tools)")
            for idx, tool in enumerate(available_tools, 1):
                print(f"  {idx}. {tool}")
            
            print("\nSelect tools to enable (comma-separated numbers, or 0 for none) [default: 0]: ")
            tool_input = input("Tools: ").strip() or "0"
            
            selected_toolsets = []
            if tool_input != "0":
                try:
                    tool_indices = [int(x.strip()) for x in tool_input.split(",")]
                    for idx in tool_indices:
                        if 1 <= idx <= len(available_tools):
                            selected_toolsets.append(available_tools[idx - 1])
                except ValueError:
                    print("❌ Invalid tool selection. No tools will be enabled.")
            
            if selected_toolsets:
                print(f"✅ Enabled tools: {', '.join(selected_toolsets)}")
            else:
                print("✅ No tools enabled")
            
            # Configure agent based on selected template
            agent_id = f"{template_id}-cli-example"
            agent_name = f"{selected_template.id.replace('-', ' ').title()} CLI Agent"
            agent_description = f"CLI demonstration agent using {template_id} template"
            
            # Build template config based on template type
            if template_id == "langgraph-workflow":
                template_config = {
                    "workflow_responsibility": "Analyzing and responding to user questions with multi-step processing.",
                    "steps": [
                        {
                            "name": "Step 1: Analyze Request",
                            "prompt": "Analyze the user's request and identify key requirements.",
                            "tools": selected_toolsets,
                            "timeout": 60,
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
                system_prompt = "You are a helpful workflow assistant that processes requests step by step."
            elif template_id == "simple-test":
                template_config = {
                    "response_prefix": "🤖 ",
                    "system_prompt": "You are a helpful assistant that responds to user questions."
                }
                system_prompt = "You are a helpful assistant that responds to user questions."
            elif template_id == "test-plugin-agent":
                template_config = {
                    "greeting": "Hello from plugin agent!",
                    "max_iterations": 10
                }
                system_prompt = "You are a test plugin agent demonstrating the plugin system."
            else:
                # Generic config for unknown templates
                template_config = {}
                system_prompt = "You are a helpful assistant."
            
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
                
                # Ask if user wants to recreate with new config
                recreate = input("Do you want to recreate with new configuration? (y/N): ").strip().lower()
                if recreate == 'y':
                    print(f"🗑️  Deleting existing agent...")
                    await client.delete_agent(agent_id)
                    existing_agent = None
                else:
                    agent_info = existing_agent
            
            if not existing_agent:
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
                    toolsets=selected_toolsets,
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
        
        # Get toolsets from configuration
        toolsets = agent_info.configuration.get('toolsets', [])
        if toolsets:
            print(f"   Tools: {', '.join(toolsets)}")
        else:
            print(f"   Tools: None")
        
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