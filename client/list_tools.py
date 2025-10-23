#!/usr/bin/env python3
"""
Simple script to list MCP tools from a server.
Usage: python list_tools.py [server_url]
"""
import asyncio
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def list_tools(server_url: str = "http://localhost:8000/mcp"):
    """List all tools from an MCP server."""
    print(f"Connecting to: {server_url}")
    
    async with streamablehttp_client(server_url) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            
            print(f"\n🔧 Found {len(tools.tools)} tool(s):\n")
            for tool in tools.tools:
                print(f"• {tool.name}")
                if tool.description:
                    print(f"  {tool.description}")


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    
    try:
        asyncio.run(list_tools(server_url))
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure the server is running:")
        print("  cd solutions/server && uv run main.py")
        sys.exit(1)

