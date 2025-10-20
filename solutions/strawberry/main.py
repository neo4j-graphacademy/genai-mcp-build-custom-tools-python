from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Strawbrerry")

@mcp.tool()
def count_letters(text: str, search: str) -> int:
    """Count occurrences of a letter in the text"""
    return text.lower().count(search.lower())

# Run the server when executed directly
if __name__ == "__main__":
    mcp.run(
      transport="streamable-http"
    )