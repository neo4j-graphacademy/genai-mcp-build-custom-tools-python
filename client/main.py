#!/usr/bin/env python3
"""
MCP Client that connects to the MCP server and allows interactive tool execution.
"""
import asyncio
import json
import re
from typing import Any, Dict
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def build_arguments_from_schema(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prompt the user to build arguments based on the tool's input schema.
    """
    arguments = {}
    
    if not input_schema or "properties" not in input_schema:
        return arguments
    
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    print("\n📝 Please provide the following parameters:")
    print("-" * 60)
    
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        param_desc = param_info.get("description", "")
        is_required = param_name in required
        
        # Display parameter info
        required_marker = " (required)" if is_required else " (optional)"
        print(f"\n{param_name}{required_marker}")
        if param_desc:
            print(f"  Description: {param_desc}")
        print(f"  Type: {param_type}")
        
        # Get user input
        while True:
            user_input = input(f"  Enter value: ").strip()
            
            # Allow skipping optional parameters
            if not user_input and not is_required:
                break
            
            # Require value for required parameters
            if not user_input and is_required:
                print("  ⚠️  This parameter is required. Please provide a value.")
                continue
            
            # Type conversion
            try:
                if param_type == "integer":
                    arguments[param_name] = int(user_input)
                elif param_type == "number":
                    arguments[param_name] = float(user_input)
                elif param_type == "boolean":
                    arguments[param_name] = user_input.lower() in ("true", "yes", "1", "y")
                elif param_type == "object" or param_type == "array":
                    arguments[param_name] = json.loads(user_input)
                else:
                    arguments[param_name] = user_input
                break
            except (ValueError, json.JSONDecodeError) as e:
                print(f"  ⚠️  Invalid input for type {param_type}: {e}")
                print("  Please try again.")
    
    return arguments


async def interactive_tool_client():
    """
    Interactive MCP client that allows users to select and execute tools.
    """
    server_url = "http://localhost:8000/mcp"
    
    print(f"🔌 Connecting to MCP server at {server_url}...\n")
    
    try:
        async with streamablehttp_client(server_url) as (read, write, get_session_id):
            print(f"✅ Connected! Session ID: {get_session_id()}\n")

            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Display server info if available
                if hasattr(session, 'server_info') and session.server_info:
                    print(f"📋 Server: {session.server_info.name}")
                    print(f"   Version: {session.server_info.version}\n")
                else:
                    print("📋 Server connected\n")
                
                # Main interactive loop
                while True:
                    # List available tools, resources, and resource templates
                    tools_result = await session.list_tools()
                    tools = tools_result.tools
                    
                    resources_result = await session.list_resources()
                    resources = resources_result.resources
                    
                    templates_result = await session.list_resource_templates()
                    templates = templates_result.resourceTemplates
                    
                    if not tools and not resources and not templates:
                        print("❌ No tools or resources available on the server.")
                        break
                    
                    print("\n" + "=" * 60)
                    print("🔧 Available Tools:")
                    print("=" * 60)
                    
                    if tools:
                        for i, tool in enumerate(tools, 1):
                            print(f"\n{i}. {tool.name}")
                            print(f"   {tool.description}")
                    else:
                        print("\n(No tools available)")
                    
                    print("\n" + "=" * 60)
                    print("📦 Available Resources:")
                    print("=" * 60)
                    
                    if resources:
                        for i, resource in enumerate(resources, len(tools) + 1):
                            print(f"\n{i}. {resource.name}")
                            print(f"   URI: {resource.uri}")
                            if resource.description:
                                print(f"   {resource.description}")
                    else:
                        print("\n(No direct resources available)")
                    
                    print("\n" + "=" * 60)
                    print("📋 Available Resource Templates:")
                    print("=" * 60)
                    
                    if templates:
                        for i, template in enumerate(templates, len(tools) + len(resources) + 1):
                            print(f"\n{i}. {template.name}")
                            print(f"   URI Template: {template.uriTemplate}")
                            if template.description:
                                print(f"   {template.description}")
                    else:
                        print("\n(No resource templates available)")
                    
                    print(f"\n0. Exit")
                    print("=" * 60)
                    
                    # Get user choice
                    try:
                        choice = input("\nSelect a tool, resource, or template (enter number): ").strip()
                        
                        if choice == "0" or choice == "":
                            print("\n👋 Goodbye!")
                            break
                        
                        selection_index = int(choice) - 1
                        total_items = len(tools) + len(resources) + len(templates)
                        
                        if selection_index < 0 or selection_index >= total_items:
                            print("❌ Invalid selection. Please try again.")
                            continue
                        
                        # Check if it's a tool, resource, or template
                        if selection_index < len(tools):
                            # It's a tool
                            selected_tool = tools[selection_index]
                            
                            print(f"\n🚀 Executing tool: {selected_tool.name}")
                            print("=" * 60)
                            
                            # Build arguments from input schema
                            input_schema = selected_tool.inputSchema
                            arguments = build_arguments_from_schema(input_schema)
                            
                            print(f"\n⚙️  Calling {selected_tool.name} with arguments:")
                            print(f"{json.dumps(arguments, indent=2)}")
                            print()
                            
                            # Execute the tool
                            result = await session.call_tool(selected_tool.name, arguments=arguments)
                            
                            # Display results
                            print("\n✨ Result:")
                            print("-" * 60)
                            
                            if result.content:
                                for item in result.content:
                                    if hasattr(item, 'text'):
                                        print(item.text)
                                    else:
                                        print(item)
                            else:
                                print("(No content returned)")
                            
                            if result.isError:
                                print("\n⚠️  Tool returned an error")
                            
                            print("-" * 60)
                        elif selection_index < len(tools) + len(resources):
                            # It's a direct resource
                            resource_index = selection_index - len(tools)
                            selected_resource = resources[resource_index]
                            
                            print(f"\n📖 Reading resource: {selected_resource.name}")
                            print("=" * 60)
                            print(f"URI: {selected_resource.uri}")
                            print()
                            
                            # Read the resource
                            result = await session.read_resource(selected_resource.uri)
                            
                            # Display results
                            print("\n✨ Resource Contents:")
                            print("-" * 60)
                            
                            if result.contents:
                                for item in result.contents:
                                    if hasattr(item, 'text'):
                                        print(item.text)
                                    elif hasattr(item, 'blob'):
                                        print(f"[Binary data: {len(item.blob)} bytes]")
                                    else:
                                        print(item)
                            else:
                                print("(No content returned)")
                            
                            print("-" * 60)
                        else:
                            # It's a resource template
                            template_index = selection_index - len(tools) - len(resources)
                            selected_template = templates[template_index]
                            
                            print(f"\n📋 Reading resource template: {selected_template.name}")
                            print("=" * 60)
                            print(f"URI Template: {selected_template.uriTemplate}")
                            
                            # Extract parameters from URI template
                            params = re.findall(r'{(\w+)}', selected_template.uriTemplate)
                            
                            # Prompt for parameter values
                            param_values = {}
                            print("\n📝 Please provide the following parameters:")
                            print("-" * 60)
                            for param in params:
                                value = input(f"  {param}: ").strip()
                                if not value:
                                    print(f"  ⚠️  Parameter '{param}' is required.")
                                    break
                                param_values[param] = value
                            
                            if len(param_values) != len(params):
                                print("\n❌ Missing required parameters. Skipping.")
                                continue
                            
                            # Construct the URI from the template
                            uri = selected_template.uriTemplate
                            for param, value in param_values.items():
                                uri = uri.replace(f'{{{param}}}', value)
                            
                            print(f"\nConstructed URI: {uri}")
                            print()
                            
                            # Read the resource
                            result = await session.read_resource(uri)
                            
                            # Display results
                            print("\n✨ Resource Contents:")
                            print("-" * 60)
                            
                            if result.contents:
                                for item in result.contents:
                                    if hasattr(item, 'text'):
                                        print(item.text)
                                    elif hasattr(item, 'blob'):
                                        print(f"[Binary data: {len(item.blob)} bytes]")
                                    else:
                                        print(item)
                            else:
                                print("(No content returned)")
                            
                            print("-" * 60)
                        
                        # Ask if user wants to continue
                        continue_choice = input("\nPress Enter to continue or 'q' to quit: ").strip().lower()
                        if continue_choice == 'q':
                            print("\n👋 Goodbye!")
                            break
                        
                    except ValueError:
                        print("❌ Invalid input. Please enter a number.")
                    except KeyboardInterrupt:
                        print("\n\n👋 Goodbye!")
                        break
                    except Exception as e:
                        print(f"\n❌ Error executing tool: {e}")
                        print("Please try again.")
                    
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("\nMake sure the MCP server is running on port 8000")
        print("You can start it with: cd solutions/server && uv run main.py")
        raise


def main():
    """Main entry point."""
    print("=" * 60)
    print("MCP Client - Interactive Tool Executor")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(interactive_tool_client())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    
    print("\n" + "=" * 60)
    print("✨ Session ended")
    print("=" * 60)


if __name__ == "__main__":
    main()

