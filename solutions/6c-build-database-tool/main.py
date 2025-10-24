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


# tag::graph_statistics[]
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
# end::graph_statistics[]

# tag::get_movies_by_genre[]
@mcp.tool()
async def get_movies_by_genre(genre: str, limit: int = 10, ctx: Context = None) -> list[dict]:
    """
    Get movies by genre from the Neo4j database.

    Args:
        genre: The genre to search for (e.g., "Action", "Drama", "Comedy")
        limit: Maximum number of movies to return (default: 10)
        ctx: Context object (injected automatically)

    Returns:
        List of movies with title, tagline, and release year
    """

    # Log the request
    await ctx.info(f"Searching for {genre} movies (limit: {limit})...")

    # Access the Neo4j driver from lifespan context
    driver = ctx.request_context.lifespan_context.driver

    # Log the query execution
    await ctx.debug(f"Executing Cypher query for genre: {genre}")

    try:
        # Execute the query
        records, summary, keys = await driver.execute_query(
            """
            MATCH (m:Movie)-[:IN_GENRE]->(g:Genre {name: $genre})
            RETURN m.title AS title,
                   m.imdbRating AS imdbRating,
                   m.released AS released
            ORDER BY coalesce(m.imdbRating, 0) DESC
            LIMIT $limit
            """,
            genre=genre,
            limit=limit
        )

        # Convert records to list of dictionaries
        movies = [record.data() for record in records]

        # Log the result
        await ctx.info(f"Found {len(movies)} {genre} movies")

        if len(movies) == 0:
            await ctx.warning(f"No movies found for genre: {genre}")

        return movies

    except Exception as e:
        # Log any errors
        await ctx.error(f"Query failed: {str(e)}")
        raise
# end::get_movies_by_genre[]

# tag::main[]
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
# end::main[]
