# tag::imports[]
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from neo4j import AsyncGraphDatabase, AsyncDriver
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
# end::imports[]


# tag::appcontext[]
@dataclass
class AppContext:
    """Application context with Neo4j driver."""
    driver: AsyncDriver
    database: str
# end::appcontext[]


# tag::lifespan[]
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage Neo4j driver lifecycle."""

    # Read connection details from environment
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    # Initialize driver on startup
    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

    try:
        # Yield context with driver
        yield AppContext(driver=driver, database=database)
    finally:
        # Close driver on shutdown
        await driver.close()
# end::lifespan[]

# tag::server[]
# Create server with lifespan
mcp = FastMCP("Movies GraphRAG Server", lifespan=app_lifespan)
# end::server[]


# tag::tool[]
from mcp.server.fastmcp import Context

@mcp.tool()
async def graph_statistics(ctx: Context) -> dict[str, int]:
    """Count the number of nodes and relationships in the graph."""

    # Access the driver from lifespan context
    driver = ctx.request_context.lifespan_context.driver
    database = ctx.request_context.lifespan_context.database

    # Use the driver to query Neo4j with the correct database
    records, summary, keys = await driver.execute_query(
        r"RETURN COUNT {()} AS nodes, COUNT {()-[]-()} AS relationships",
        database_=database
    )

    # Process the results
    if records:
        return dict(records[0])
    return {"nodes": 0, "relationships": 0}
# end::tool[]

# tag::main[]
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
# end::main[]
