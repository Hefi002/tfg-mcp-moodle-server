"""MCP Server for Moodle API integration."""
import os
import json
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from .protocol import MoodleClient
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
async def get_courses(ctx: Context[ServerSession, MoodleClient]) -> list[dict[str, Any]]:
    """Get all courses from Moodle.

    Returns a list of all courses available in the Moodle instance.
    Each course includes details like id, shortname, fullname, category, etc.

    Returns:
        List of course dictionaries with course information
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info("Fetching courses from Moodle...")

    try:
        courses = await client.get_courses()

        # Filter out the Docker Moodle default course (id=1) if you want
        # courses = [c for c in courses if c.get('id') != 1]

        await ctx.info(f"Successfully retrieved {len(courses)} courses")
        return courses

    except Exception as e:
        await ctx.error(f"Error fetching courses: {str(e)}")
        raise


@mcp.resource("moodle://courses")
async def list_courses_resource() -> str:
    """Resource that provides a formatted list of all Moodle courses.

    Returns:
        JSON string with course information
    """
    # Note: Resources don't have access to context, so we need to create a client here
    # This is a limitation - ideally we'd reuse the lifespan client
    moodle_url = os.getenv("MOODLE_URL")
    moodle_token = os.getenv("MOODLE_TOKEN")

    if not moodle_url or not moodle_token:
        raise RuntimeError("Moodle configuration not found")

    client = MoodleClient(moodle_url, moodle_token)

    try:
        courses = await client.get_courses()

        # Format courses for better readability
        formatted_courses = []
        for course in courses:
            formatted_courses.append({
                "id": course.get("id"),
                "shortname": course.get("shortname"),
                "fullname": course.get("fullname"),
                "category": course.get("categoryid"),
                "visible": course.get("visible"),
            })

        return json.dumps(formatted_courses, indent=2)
    finally:
        await client.close()


def run_server():
    """Entry point to run the MCP server."""
    logger.info("Starting Moodle MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()