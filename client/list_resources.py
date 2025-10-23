#!/usr/bin/env python3
"""
Simple script to list MCP resources from a server.
Usage: python list_resources.py [server_url]
"""
import asyncio
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def list_resources(server_url: str = "http://localhost:8000/mcp"):
    """List all resources from an MCP server."""
    print(f"Connecting to: {server_url}")
    
    async with streamablehttp_client(server_url) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List direct resources
            resources = await session.list_resources()
            
            print(f"\n📦 Found {len(resources.resources)} direct resource(s):\n")
            for resource in resources.resources:
                print(f"• {resource.name}")
                print(f"  URI: {resource.uri}")
                if resource.description:
                    print(f"  {resource.description}")
            
            # List resource templates (parametrized resources)
            templates = await session.list_resource_templates()
            
            print(f"\n📋 Found {len(templates.resourceTemplates)} resource template(s):\n")
            for template in templates.resourceTemplates:
                print(f"• {template.name}")
                print(f"  URI Template: {template.uriTemplate}")
                if template.description:
                    print(f"  {template.description}")


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    
    try:
        asyncio.run(list_resources(server_url))
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure the server is running:")
        print("  cd solutions/server && uv run main.py")
        sys.exit(1)

