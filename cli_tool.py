#!/usr/bin/env python3
"""
LangChain Agent Runtime CLI Tool

A comprehensive command-line interface for the LangChain Agent Runtime,
providing template discovery, agent management, and interactive chat sessions.

Usage:
    cli_tool.py templates list                  # List all available templates
    cli_tool.py agents list                     # List all existing agents  
    cli_tool.py agents create <template_id>     # Create a new agent
    cli_tool.py agents delete <agent_id>        # Delete an agent
    cli_tool.py chat <agent_id>                 # Start interactive chat session
    cli_tool.py health                          # Show runtime health status
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import click
from tabulate import tabulate

from client_sdk import RuntimeClient, RuntimeClientContext
from runtime.infrastructure.web.models.requests import CreateAgentRequest as AgentCreateRequest
from runtime.domain.value_objects.chat_message import ChatMessage, MessageRole


# Global client instance  
client = None  # type: Optional[RuntimeClient]


async def get_client():
    """Get or create the global client instance."""
    global client
    if client is None:
        client = RuntimeClient()
        await client.initialize()
    return client


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--json-output', is_flag=True, help='Output results in JSON format')
@click.pass_context
def cli(ctx, debug: bool, json_output: bool):
    """LangChain Agent Runtime CLI Tool"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['json_output'] = json_output
    
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.group()
def templates():
    """Template management commands"""
    pass


@templates.command('list')
@click.option('--framework', help='Filter by framework (langchain, custom, etc.)')
@click.pass_context
async def list_templates(ctx, framework: Optional[str]):
    """List all available templates"""
    try:
        async with RuntimeClientContext() as runtime_client:
            template_list = await runtime_client.list_templates(framework)
            
            if ctx.obj['json_output']:
                template_data = [
                    {
                        'template_id': t.template_id,
                        'name': t.template_name,
                        'version': t.version,
                        'framework': t.framework,
                        'description': t.description
                    }
                    for t in template_list
                ]
                click.echo(json.dumps(template_data, indent=2))
            else:
                if not template_list:
                    click.echo("No templates found")
                    return
                
                headers = ['Template ID', 'Name', 'Version', 'Framework', 'Description']
                table_data = [
                    [t.template_id, t.template_name, t.version, t.framework, t.description[:50] + '...' if len(t.description) > 50 else t.description]
                    for t in template_list
                ]
                
                click.echo(f"\nFound {len(template_list)} template(s):")
                click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
                
    except Exception as e:
        click.echo(f"Error listing templates: {e}", err=True)
        sys.exit(1)


@templates.command('show')
@click.argument('template_id')
@click.option('--version', help='Template version (uses latest if not specified)')
@click.pass_context
async def show_template(ctx, template_id: str, version: Optional[str]):
    """Show detailed information about a template"""
    try:
        async with RuntimeClientContext() as runtime_client:
            template = await runtime_client.get_template(template_id, version)
            
            if not template:
                click.echo(f"Template '{template_id}' not found", err=True)
                sys.exit(1)
            
            if ctx.obj['json_output']:
                template_data = {
                    'template_id': template.template_id,
                    'name': template.template_name,
                    'version': template.version,
                    'framework': template.framework,
                    'description': template.description,
                    'metadata': template.metadata
                }
                click.echo(json.dumps(template_data, indent=2))
            else:
                click.echo(f"\nTemplate Details:")
                click.echo(f"  ID: {template.template_id}")
                click.echo(f"  Name: {template.template_name}")
                click.echo(f"  Version: {template.version}")
                click.echo(f"  Framework: {template.framework}")
                click.echo(f"  Description: {template.description}")
                
                if template.metadata:
                    click.echo(f"  Metadata:")
                    for key, value in template.metadata.items():
                        click.echo(f"    {key}: {value}")
                        
    except Exception as e:
        click.echo(f"Error showing template: {e}", err=True)
        sys.exit(1)


@cli.group()
def agents():
    """Agent management commands"""
    pass


@agents.command('list')
@click.pass_context
async def list_agents(ctx):
    """List all existing agents"""
    try:
        async with RuntimeClientContext() as runtime_client:
            agent_list = await runtime_client.list_agents()
            
            if ctx.obj['json_output']:
                agent_data = [
                    {
                        'agent_id': a.agent_id,
                        'name': a.name,
                        'description': a.description,
                        'template_id': a.template_id,
                        'template_version': a.template_version,
                        'status': a.status,
                        'created_at': a.created_at
                    }
                    for a in agent_list
                ]
                click.echo(json.dumps(agent_data, indent=2))
            else:
                if not agent_list:
                    click.echo("No agents found")
                    return
                
                headers = ['Agent ID', 'Name', 'Template', 'Version', 'Status']
                table_data = [
                    [a.agent_id, a.name, a.template_id, a.template_version, a.status]
                    for a in agent_list
                ]
                
                click.echo(f"\nFound {len(agent_list)} agent(s):")
                click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
                
    except Exception as e:
        click.echo(f"Error listing agents: {e}", err=True)
        sys.exit(1)


@agents.command('show')
@click.argument('agent_id')
@click.pass_context
async def show_agent(ctx, agent_id: str):
    """Show detailed information about an agent"""
    try:
        async with RuntimeClientContext() as runtime_client:
            agent = await runtime_client.get_agent(agent_id)
            
            if not agent:
                click.echo(f"Agent '{agent_id}' not found", err=True)
                sys.exit(1)
            
            if ctx.obj['json_output']:
                agent_data = {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'description': agent.description,
                    'template_id': agent.template_id,
                    'template_version': agent.template_version,
                    'status': agent.status,
                    'created_at': agent.created_at
                }
                click.echo(json.dumps(agent_data, indent=2))
            else:
                click.echo(f"\nAgent Details:")
                click.echo(f"  ID: {agent.agent_id}")
                click.echo(f"  Name: {agent.name}")
                click.echo(f"  Description: {agent.description}")
                click.echo(f"  Template: {agent.template_id}")
                click.echo(f"  Template Version: {agent.template_version}")
                click.echo(f"  Status: {agent.status}")
                click.echo(f"  Created: {agent.created_at}")
                        
    except Exception as e:
        click.echo(f"Error showing agent: {e}", err=True)
        sys.exit(1)


@agents.command('create')
@click.argument('template_id')
@click.option('--agent-id', help='Agent ID (auto-generated if not provided)')
@click.option('--name', help='Agent name')
@click.option('--description', help='Agent description')
@click.option('--version', help='Template version (uses latest if not specified)')
@click.option('--llm-config', default='deepseek', help='LLM configuration ID')
@click.option('--system-prompt', help='System prompt for the agent')
@click.pass_context
async def create_agent(ctx, template_id: str, agent_id: Optional[str], name: Optional[str], 
                      description: Optional[str], version: Optional[str], llm_config: str,
                      system_prompt: Optional[str]):
    """Create a new agent from a template"""
    try:
        async with RuntimeClientContext() as runtime_client:
            # Auto-generate missing fields
            if not agent_id:
                agent_id = f"{template_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            if not name:
                name = f"Agent {agent_id}"
            
            if not description:
                description = f"Agent created from template {template_id}"
                
            if not system_prompt:
                system_prompt = "You are a helpful assistant that responds to user questions."
            
            if not version:
                version = "1.0.0"  # Default version
            
            # Create agent request
            agent_request = AgentCreateRequest(
                id=agent_id,
                name=name,
                description=description,
                type=template_id,
                template_id=template_id,
                template_version_id=version,
                template_config={},
                system_prompt=system_prompt,
                llm_config_id=llm_config,
                toolsets=[],
                conversation_config={}
            )
            
            # Create the agent
            agent = await runtime_client.create_agent(agent_request)
            
            if ctx.obj['json_output']:
                agent_data = {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'description': agent.description,
                    'template_id': agent.template_id,
                    'template_version': agent.template_version,
                    'status': agent.status,
                    'created_at': agent.created_at
                }
                click.echo(json.dumps(agent_data, indent=2))
            else:
                click.echo(f"\n✅ Agent created successfully!")
                click.echo(f"  ID: {agent.agent_id}")
                click.echo(f"  Name: {agent.name}")
                click.echo(f"  Template: {agent.template_id} v{agent.template_version}")
                click.echo(f"\nYou can now chat with this agent using:")
                click.echo(f"  python cli_tool.py chat {agent.agent_id}")
                        
    except Exception as e:
        click.echo(f"Error creating agent: {e}", err=True)
        sys.exit(1)


@agents.command('delete')
@click.argument('agent_id')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
async def delete_agent(ctx, agent_id: str, yes: bool):
    """Delete an existing agent"""
    try:
        async with RuntimeClientContext() as runtime_client:
            # Check if agent exists
            agent = await runtime_client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent '{agent_id}' not found", err=True)
                sys.exit(1)
            
            # Confirm deletion
            if not yes:
                click.echo(f"Agent to delete:")
                click.echo(f"  ID: {agent.agent_id}")
                click.echo(f"  Name: {agent.name}")
                if not click.confirm("Are you sure you want to delete this agent?"):
                    click.echo("Deletion cancelled")
                    return
            
            # Delete the agent
            success = await runtime_client.delete_agent(agent_id)
            
            if success:
                if ctx.obj['json_output']:
                    click.echo(json.dumps({"status": "deleted", "agent_id": agent_id}))
                else:
                    click.echo(f"✅ Agent '{agent_id}' deleted successfully")
            else:
                click.echo(f"❌ Failed to delete agent '{agent_id}'", err=True)
                sys.exit(1)
                        
    except Exception as e:
        click.echo(f"Error deleting agent: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('agent_id')
@click.option('--stream/--no-stream', default=True, help='Enable/disable streaming mode')
@click.pass_context
async def chat(ctx, agent_id: str, stream: bool):
    """Start an interactive chat session with an agent"""
    try:
        async with RuntimeClientContext() as runtime_client:
            # Check if agent exists
            agent = await runtime_client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent '{agent_id}' not found", err=True)
                sys.exit(1)
            
            # Display agent info
            click.echo(f"\n🤖 Starting chat session with agent: {agent.name}")
            click.echo(f"   ID: {agent.agent_id}")
            click.echo(f"   Template: {agent.template_id} v{agent.template_version}")
            click.echo(f"   Streaming: {'ON' if stream else 'OFF'}")
            click.echo("\nCommands:")
            click.echo("  /exit - Exit chat session")
            click.echo("  /stream - Toggle streaming mode")
            click.echo("  /clear - Clear conversation history")
            click.echo("=" * 60)
            
            conversation_history = []
            
            while True:
                try:
                    # Get user input
                    user_input = input(f"\n{click.style('You', fg='green')}: ").strip()
                    
                    if user_input.lower() in ['/exit', '/quit']:
                        click.echo("👋 Goodbye!")
                        break
                    
                    if user_input.lower() == '/stream':
                        stream = not stream
                        click.echo(f"Streaming mode: {'ON' if stream else 'OFF'}")
                        continue
                    
                    if user_input.lower() == '/clear':
                        conversation_history = []
                        click.echo("🧹 Conversation history cleared")
                        continue
                    
                    if not user_input:
                        continue
                    
                    # Create message
                    message = ChatMessage(role=MessageRole.USER, content=user_input)
                    conversation_history.append(message)
                    
                    # Execute agent
                    agent_prefix = click.style(f"{agent.name}", fg='blue')
                    
                    if stream:
                        # Stream response
                        click.echo(f"{agent_prefix}: ", nl=False)
                        response_content = ""
                        async for chunk in runtime_client.stream_chat_with_agent(agent_id, conversation_history):
                            if chunk.choices and chunk.choices[0].get("delta", {}).get("content"):
                                content = chunk.choices[0]["delta"]["content"]
                                response_content += content
                                click.echo(content, nl=False)
                        click.echo()  # New line after streaming
                        
                        # Add response to history
                        if response_content:
                            conversation_history.append(
                                ChatMessage(role=MessageRole.ASSISTANT, content=response_content)
                            )
                    else:
                        # Regular response
                        response = await runtime_client.chat_with_agent(agent_id, conversation_history)
                        content = response.choices[0].message.content
                        click.echo(f"{agent_prefix}: {content}")
                        
                        # Add response to history
                        conversation_history.append(
                            ChatMessage(role=MessageRole.ASSISTANT, content=content)
                        )
                
                except KeyboardInterrupt:
                    click.echo("\n\n👋 Chat session interrupted. Goodbye!")
                    break
                except Exception as e:
                    click.echo(f"\n❌ Error: {e}")
                    click.echo("Please try again.")
            
    except Exception as e:
        click.echo(f"Error starting chat session: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
async def health(ctx):
    """Show runtime health status"""
    try:
        async with RuntimeClientContext() as runtime_client:
            health_status = runtime_client.get_health_status()
            
            if ctx.obj['json_output']:
                click.echo(json.dumps(health_status, indent=2))
            else:
                status = health_status.get('status', 'unknown')
                status_icon = "✅" if status == "healthy" else "❌"
                
                click.echo(f"\n{status_icon} Runtime Status: {status}")
                click.echo(f"   Initialized: {health_status.get('initialized', False)}")
                click.echo(f"   Templates Loaded: {health_status.get('templates_loaded', 0)}")
                click.echo(f"   Total Agents: {health_status.get('total_agents', 0)}")
                click.echo(f"   Active Agents: {health_status.get('active_agents', 0)}")
                
                if 'error' in health_status:
                    click.echo(f"   Error: {health_status['error']}")
                        
    except Exception as e:
        click.echo(f"Error getting health status: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point - handle async CLI commands"""
    # Convert click commands to async
    def async_cmd(f):
        def wrapper(*args, **kwargs):
            return asyncio.run(f(*args, **kwargs))
        return wrapper
    
    # Apply async wrapper to commands that need it
    list_templates.callback = async_cmd(list_templates.callback)
    show_template.callback = async_cmd(show_template.callback)
    list_agents.callback = async_cmd(list_agents.callback)
    show_agent.callback = async_cmd(show_agent.callback)
    create_agent.callback = async_cmd(create_agent.callback)
    delete_agent.callback = async_cmd(delete_agent.callback)
    chat.callback = async_cmd(chat.callback)
    health.callback = async_cmd(health.callback)
    
    # Handle environment
    if not os.getenv("OPENAI_API_KEY"):
        click.echo("⚠️  Warning: OPENAI_API_KEY environment variable not set.", err=True)
        click.echo("   Set it with: export OPENAI_API_KEY='your-api-key-here'", err=True)
        click.echo()
    
    # Run CLI
    cli()


if __name__ == "__main__":
    main()