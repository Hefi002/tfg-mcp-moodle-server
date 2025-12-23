"""MCP Server for Moodle API integration."""
import os
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from .protocol import MoodleClient
from .models import Course, CourseUpdate
from .utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


# Lifespan context manager
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[MoodleClient]:
    """Manage application lifecycle with Moodle client."""
    # Get configuration from environment
    moodle_url = os.getenv("MOODLE_URL")
    moodle_token = os.getenv("MOODLE_TOKEN")

    if not moodle_url or not moodle_token:
        raise ValueError(
            "MOODLE_URL and MOODLE_TOKEN must be set in environment or .env file"
        )

    logger.info(f"Initializing Moodle client for {moodle_url}")

    # Initialize Moodle client
    client = MoodleClient(moodle_url, moodle_token)

    try:
        yield client
    finally:
        # Cleanup
        logger.info("Closing Moodle client")
        await client.close()


# Initialize FastMCP server with lifespan
mcp = FastMCP(
    name="Moodle MCP Server",
    instructions="A Model Context Protocol server for interacting with Moodle LMS",
    json_response=True,
    lifespan=app_lifespan
)


@mcp.tool()
async def get_courses(
    ctx: Context[ServerSession, MoodleClient],
    courseids: list[int] | None = None
) -> list[dict[str, Any]]:
    """Get courses from Moodle.

    Returns a list of courses from the Moodle instance.
    Each course includes details like id, shortname, fullname, category, etc.

    Args:
        courseids: Optional list of course IDs to retrieve specific courses.
                   If not provided or empty, returns all courses.

    Returns:
        List of course dictionaries with course information
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    if courseids:
        await ctx.info(f"Fetching {len(courseids)} specific course(s) from Moodle...")
    else:
        await ctx.info("Fetching all courses from Moodle...")

    try:
        courses = await client.get_courses(courseids)

        # Filter out the Docker Moodle default course (id=1) if you want
        # courses = [c for c in courses if c.get('id') != 1]

        await ctx.info(f"Successfully retrieved {len(courses)} courses")
        return courses

    except Exception as e:
        await ctx.error(f"Error fetching courses: {str(e)}")
        raise


@mcp.tool()
async def create_courses(
    ctx: Context[ServerSession, MoodleClient], 
    courses: list[Course]
) -> list[dict[str, Any]]:
    """Create one or more courses in Moodle.

    Args:
        courses: List of Course objects to create

    Returns:
        List of created course dictionaries with their assigned IDs
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Creating {len(courses)} course(s) in Moodle...")

    try:
        created_courses = await client.create_courses(courses)

        await ctx.info(f"Successfully created {len(created_courses)} course(s)")
        return created_courses

    except Exception as e:
        await ctx.error(f"Error creating courses: {str(e)}")
        raise


@mcp.tool()
async def update_courses(
    ctx: Context[ServerSession, MoodleClient], 
    courses: list[CourseUpdate]
) -> dict[str, Any]:
    """Update one or more courses in Moodle.

    Args:
        courses: List of CourseUpdate objects with course ID and fields to update

    Returns:
        Result dictionary (usually contains warnings array if any issues occurred)
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Updating {len(courses)} course(s) in Moodle...")

    try:
        result = await client.update_courses(courses)

        await ctx.info(f"Successfully updated {len(courses)} course(s)")
        return result

    except Exception as e:
        await ctx.error(f"Error updating courses: {str(e)}")
        raise


@mcp.tool()
async def delete_courses(ctx: Context[ServerSession, MoodleClient], courseids: list[int]) -> dict[str, Any]:
    """Delete one or more courses from Moodle.

    Deletes courses permanently from the Moodle instance.
    Warning: This action cannot be undone!

    Args:
        courseids: List of course IDs to delete

    Returns:
        Result dictionary (usually contains warnings array if any issues occurred)
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Deleting {len(courseids)} course(s) from Moodle...")

    try:
        result = await client.delete_courses(courseids)

        await ctx.info(f"Successfully deleted {len(courseids)} course(s)")
        return result

    except Exception as e:
        await ctx.error(f"Error deleting courses: {str(e)}")
        raise


def run_server():
    """Entry point to run the MCP server."""
    logger.info("Starting Moodle MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
