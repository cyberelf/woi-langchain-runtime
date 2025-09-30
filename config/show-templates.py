#!/usr/bin/env python3
"""Show available agent templates and their configuration schemas.

This script displays all discovered agent templates and their configuration
options, since templates are discovered from code rather than configured in JSON.

Usage:
    python config/show-templates.py
    python config/show-templates.py --template simple-test
    python config/show-templates.py --schemas
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add runtime to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from runtime.infrastructure.frameworks.langgraph.templates import (
        get_langgraph_templates,
        get_langgraph_template_classes
    )
    from runtime.infrastructure.frameworks.langgraph.templates.base import BaseLangGraphAgent
    RUNTIME_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Runtime modules not fully available: {e}")
    print("Showing static template information instead...")
    RUNTIME_AVAILABLE = False


def show_template_details(template_id: str):
    """Show detailed information about a specific template."""
    if not RUNTIME_AVAILABLE:
        print("Runtime modules not available - cannot load template details")
        return
        
    template_classes = get_langgraph_template_classes()
    
    if template_id not in template_classes:
        print(f"❌ Template '{template_id}' not found")
        print(f"Available templates: {list(template_classes.keys())}")
        return
    
    template_class = template_classes[template_id]
    
    print(f"🤖 Template: {template_id}")
    print("=" * 50)
    
    # Basic info
    print(f"Name: {getattr(template_class, 'template_name', 'N/A')}")
    print(f"Version: {getattr(template_class, 'template_version', 'N/A')}")
    print(f"Description: {getattr(template_class, 'template_description', 'N/A')}")
    print(f"Framework: {getattr(template_class, 'framework', 'N/A')}")
    
    # Configuration schema
    config_schema = getattr(template_class, 'config_schema', None)
    if config_schema and hasattr(config_schema, 'model_json_schema'):
        print("\n📋 Configuration Schema:")
        try:
            schema = config_schema.model_json_schema()
            
            if 'properties' in schema:
                properties = schema['properties']
                required_fields = schema.get('required', [])
                
                for field_name, field_info in properties.items():
                    field_type = field_info.get('type', 'unknown')
                    field_desc = field_info.get('description', 'No description')
                    default_val = field_info.get('default')
                    
                    required_marker = " (required)" if field_name in required_fields else ""
                    default_marker = f" [default: {default_val}]" if default_val is not None else ""
                    
                    print(f"  • {field_name}: {field_type}{required_marker}")
                    print(f"    {field_desc}{default_marker}")
            else:
                print("    No configuration properties defined")
        except Exception as e:
            print(f"    ⚠️  Could not load schema: {e}")
    else:
        print("\n📋 Configuration Schema: Not available")
    
    # Example configuration
    print(f"\n💡 Example Agent Creation:")
    print("POST /v1/agents")
    example_config = {
        "name": f"My {template_class.template_name}",
        "template_id": template_id,
        "template_version": getattr(template_class, 'template_version', 'v1.0.0'),
        "configuration": {}
    }
    
    # Add some common example config based on template type
    if template_id == "simple-test":
        example_config["configuration"] = {
            "system_message": "You are a helpful assistant",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    elif template_id == "workflow":
        example_config["configuration"] = {
            "steps": [
                {
                    "name": "Step 1",
                    "prompt": "Analyze the user's request",
                    "depends_on": [],
                    "timeout": 60
                },
                {
                    "name": "Step 2", 
                    "prompt": "Generate a response based on the analysis",
                    "depends_on": ["Step 1"],
                    "timeout": 60
                }
            ],
            "max_parallel_steps": 2,
            "retry_failed_steps": True
        }
    
    print(json.dumps(example_config, indent=2))


def show_all_templates():
    """Show all available templates."""
    if not RUNTIME_AVAILABLE:
        show_static_templates()
        return
        
    templates = get_langgraph_templates()
    
    if not templates:
        print("❌ No templates found!")
        return
    
    print("🤖 Available Agent Templates")
    print("=" * 50)
    
    for template in templates:
        template_id = template.get('template_id', 'unknown')
        template_name = template.get('template_name', 'Unknown')
        template_version = template.get('template_version', '1.0.0')
        description = template.get('description', 'No description available')
        
        print(f"\n📋 {template_id}")
        print(f"   Name: {template_name}")
        print(f"   Version: v{template_version}")
        print(f"   Description: {description}")
        
        # Show configuration hints
        template_class = template.get('class')
        if template_class:
            config_schema = getattr(template_class, 'config_schema', None)
            if config_schema and hasattr(config_schema, 'model_json_schema'):
                try:
                    schema = config_schema.model_json_schema()
                    prop_count = len(schema.get('properties', {}))
                    if prop_count > 0:
                        print(f"   Configuration: {prop_count} configurable field(s)")
                    else:
                        print(f"   Configuration: No custom fields")
                except:
                    print(f"   Configuration: Schema available")
            else:
                print(f"   Configuration: Basic template")
    
    print(f"\n📊 Summary: {len(templates)} template(s) available")
    print("\n💡 Use --template <template-id> to see detailed configuration")


def show_schemas_only():
    """Show just the configuration schemas as JSON."""
    if not RUNTIME_AVAILABLE:
        print('{"error": "Runtime modules not available - cannot load schemas"}')
        return
        
    template_classes = get_langgraph_template_classes()
    schemas = {}
    
    for template_id, template_class in template_classes.items():
        config_schema = getattr(template_class, 'config_schema', None)
        if config_schema and hasattr(config_schema, 'model_json_schema'):
            try:
                schemas[template_id] = config_schema.model_json_schema()
            except Exception as e:
                schemas[template_id] = {"error": str(e)}
        else:
            schemas[template_id] = {"note": "No custom configuration schema"}
    
    print(json.dumps(schemas, indent=2))


def show_static_templates():
    """Show static template information when runtime is not available."""
    print("🤖 Available Agent Templates (Static Info)")
    print("=" * 50)
    print("⚠️  Runtime not available - showing static template information")
    print("   Install dependencies to see live template discovery\n")
    
    static_templates = [
        {
            "template_id": "simple-test",
            "template_name": "Simple Test Agent",
            "template_version": "1.0.0",
            "description": "Basic conversational agent for testing and development",
            "config_fields": 3
        },
        {
            "template_id": "workflow",
            "template_name": "Workflow Agent",
            "template_version": "1.0.0", 
            "description": "Sequential step execution agent with state management",
            "config_fields": 4
        }
    ]
    
    for template in static_templates:
        print(f"\n📋 {template['template_id']}")
        print(f"   Name: {template['template_name']}")
        print(f"   Version: v{template['template_version']}")
        print(f"   Description: {template['description']}")
        print(f"   Configuration: {template['config_fields']} configurable field(s)")
        
    print(f"\n📊 Summary: {len(static_templates)} template(s) available")
    print("\n💡 Use --template <template-id> to see detailed configuration")
    print("🔧 Install runtime dependencies to see live template discovery")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Show available agent templates and their configuration schemas"
    )
    parser.add_argument(
        "--template", 
        help="Show detailed info for a specific template"
    )
    parser.add_argument(
        "--schemas", 
        action="store_true",
        help="Output only the JSON schemas"
    )
    
    args = parser.parse_args()
    
    if args.schemas:
        show_schemas_only()
    elif args.template:
        show_template_details(args.template)
    else:
        show_all_templates()


if __name__ == "__main__":
    main()
