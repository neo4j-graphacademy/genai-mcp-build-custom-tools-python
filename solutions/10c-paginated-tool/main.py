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

# tag::get_movie[]
@mcp.resource("movie://{tmdb_id}")
async def get_movie(tmdb_id: str, ctx: Context) -> str:
    """
    Get detailed information about a specific movie by TMDB ID.

    Args:
        tmdb_id: The TMDB ID of the movie (e.g., "603" for The Matrix)

    Returns:
        Formatted string with movie details including title, plot, cast, and genres
    """
    await ctx.info(f"Fetching movie details for TMDB ID: {tmdb_id}")

    context = ctx.request_context.lifespan_context

    try:
        records, _, _ = await context.driver.execute_query(
            """
            MATCH (m:Movie {tmdbId: $tmdb_id})
            RETURN m.title AS title,
               m.released AS released,
               m.tagline AS tagline,
               m.runtime AS runtime,
               m.plot AS plot,
               [ (m)-[:IN_GENRE]->(g:Genre) | g.name ] AS genres,
               [ (p)-[r:ACTED_IN]->(m) | {name: p.name, role: r.role} ] AS actors,
               [ (d)-[:DIRECTED]->(m) | d.name ] AS directors
            """,
            tmdb_id=tmdb_id,
            database_=context.database
        )

        if not records:
            await ctx.warning(f"Movie with TMDB ID {tmdb_id} not found")
            return f"Movie with TMDB ID {tmdb_id} not found in database"

        movie = records[0].data()

        # Format the output
        output = []
        output.append(f"# {movie['title']} ({movie['released']})")
        output.append("")

        if movie['tagline']:
            output.append(f"_{movie['tagline']}_")
            output.append("")

        output.append(f"**Runtime:** {movie['runtime']} minutes")
        output.append(f"**Genres:** {', '.join(movie['genres'])}")

        if movie['directors']:
            output.append(f"**Director(s):** {', '.join(movie['directors'])}")

        output.append("")
        output.append("## Plot")
        output.append(movie['plot'])

        if movie['actors']:
            output.append("")
            output.append("## Cast")
            for actor in movie['actors']:
                if actor['role']:
                    output.append(f"- {actor['name']} as {actor['role']}")
                else:
                    output.append(f"- {actor['name']}")

        result = "\n".join(output)

        await ctx.info(f"Successfully fetched details for '{movie['title']}'")

        return result

    except Exception as e:
        await ctx.error(f"Failed to fetch movie: {str(e)}")
        raise
# end::get_movie[]

# tag::list_movies_by_genre[]
# tag::list_movies_by_genre_def[]
@mcp.tool()
async def list_movies_by_genre(
    genre: str,
    page_size: int = 10,
    cursor: int = 0,
    ctx: Context = None
) -> dict:
    """
    Browse movies in a genre with pagination support.

    Args:
        genre: Genre name (e.g., "Action", "Comedy", "Drama")
        cursor: Pagination cursor - position in the result set (default "0")
        page_size: Number of movies to return per page (default 10)

    Returns:
        Dictionary containing:
        - movies: List of movie objects with title, released, and rating
        - next_cursor: Cursor for the next page (null if no more pages)
        - page: Current page number (1-indexed)
        - has_more: Boolean indicating if more pages are available
    """
    # end::list_movies_by_genre_def[]

    # tag::list_movies_by_genre_cursor[]
    # Calculate skip value from cursor
    skip = cursor * page_size

    # Log the request
    page_num = (skip // page_size) + 1
    await ctx.info(f"Fetching {genre} movies, page {page_num} (showing {page_size} per page)...")
    # end::list_movies_by_genre_cursor[]

    # tag::list_movies_by_genre_execute[]
    try:
        # Access driver from lifespan context
        driver = ctx.request_context.lifespan_context.driver

        # Execute paginated query
        records, summary, keys = await driver.execute_query(
            """
            MATCH (m:Movie)-[:IN_GENRE]->(g:Genre {name: $genre})
            RETURN m.title AS title,
                   m.released AS released,
                   m.imdbRating AS rating
            ORDER BY m.title ASC
            SKIP $skip
            LIMIT $limit
            """,
            genre=genre,
            skip=skip,
            limit=page_size
        )

        # Convert to list of dictionaries
        movies = [record.data() for record in records]
        # end::list_movies_by_genre_execute[]

        # tag::list_movies_by_genre_return[]
        # Calculate next cursor
        next_cursor = None
        if len(movies) == page_size:
            next_cursor = skip + page_size

        # Log results
        await ctx.info(f"Returned {len(movies)} movies from page {page_num}")
        if next_cursor is None:
            await ctx.info("This is the last page")

        # Return structured response
        return {
            "genre": genre,
            "movies": movies,
            "next_cursor": next_cursor,
            "page": page_num,
            "page_size": page_size,
            "has_more": next_cursor is not None
        }

    except Exception as e:
        await ctx.error(f"Query failed: {str(e)}")
        raise
    # end::list_movies_by_genre_return[]
# end::list_movies_by_genre[]

# tag::main[]
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
# end::main[]
