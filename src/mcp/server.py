"""MCP Server for Moodle API integration."""
import os
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from .protocol import MoodleClient
from .models import Course, CourseUpdate, CourseContentsOption
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
        List of course dictionaries, each containing:
        - id: Course ID
        - shortname: Short course name
        - fullname: Full course name
        - categoryid: Category ID
        - idnumber: Course identification number
        - summary: Course description (HTML)
        - summaryformat: Format of summary (1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN)
        - format: Course format (topics, weeks, etc.)
        - visible: Course visibility (1=visible, 0=hidden)
        - startdate: Course start timestamp
        - enddate: Course end timestamp
        - And many other fields...
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
        courses: List of Course objects to create. Each Course must have:
                Required fields:
                - fullname: Full course name (e.g., "Advanced Mathematics 2024")
                - shortname: Unique short name (e.g., "MAT-ADV-2024")
                - categoryid: Category ID (must be > 0)
                
                Optional fields:
                - idnumber: Course identification number
                - summary: HTML description of the course
                - summaryformat: Format (1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN)
                - format: Course format ("topics", "weeks", "social", etc.)
                - visible: Visibility (1=visible, 0=hidden)
                - startdate/enddate: Unix timestamps
                - showgrades: Show grades (1=yes, 0=no)
                - maxbytes: Max file size (0=no limit)
                - groupmode: Group mode (0=no groups, 1=separate, 2=visible)
                - And many other optional fields...

    Returns:
        List of created course dictionaries with their assigned IDs and all fields
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
        courses: List of CourseUpdate objects with course ID and fields to update.
                Each CourseUpdate must have:
                Required field:
                - id: Course ID to update (must be > 0)
                
                Optional fields (only specify what you want to change):
                - fullname: Full course name
                - shortname: Unique short name
                - categoryid: Category ID
                - idnumber: Course identification number
                - summary: HTML description
                - summaryformat: Format (1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN)
                - format: Course format ("topics", "weeks", etc.)
                - visible: Visibility (1=visible, 0=hidden)
                - startdate/enddate: Unix timestamps
                - showgrades: Show grades (1=yes, 0=no)
                - maxbytes: Max file size
                - groupmode: Group mode (0=no groups, 1=separate, 2=visible)
                - And any other course field...

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
        courseids: List of course IDs to delete. Each ID must be a valid course ID
                   that exists in the Moodle instance.

    Returns:
        Result dictionary containing:
        - warnings: Array of warning messages if any issues occurred during deletion
                   (e.g., if a course ID doesn't exist or user lacks permissions)
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


@mcp.tool()
async def get_course_contents(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int,
    options: CourseContentsOption | None = None
) -> list[dict[str, Any]]:
    """Get course contents (sections and modules) from Moodle.

    Returns the complete course structure including sections, modules (activities),
    and optionally their contents (files, descriptions, etc.).

    Args:
        courseid: Course ID to retrieve contents from
        options: Optional CourseContentsOption object to filter results.
                Available filters:
                - excludemodules: Don't return modules, only sections
                - excludecontents: Don't return module contents (files)
                - includestealthmodules: Include stealth modules for students
                - sectionid: Return only specific section by ID
                - sectionnumber: Return only section by its number/order
                - cmid: Return only specific course module by ID
                - modname: Return only modules of specific type (e.g., "forum", "assign")
                - modid: Return only module with specific ID (use with modname)

    Returns:
        List of section dictionaries, each containing:
        - Section information (id, name, summary, etc.)
        - List of modules (activities) in each section
        - Module contents (files, URLs, etc.) if not excluded
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching contents for course {courseid} from Moodle...")

    try:
        contents = await client.get_course_contents(courseid, options)

        await ctx.info(f"Successfully retrieved {len(contents)} section(s)")
        return contents

    except Exception as e:
        await ctx.error(f"Error fetching course contents: {str(e)}")
        raise


@mcp.tool()
async def view_course(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int,
    sectionnumber: int = 0
) -> dict[str, Any]:
    """Log that the course was viewed (core_course_view_course).

    Calls `MoodleClient.view_course` to notify Moodle that a course (or a specific
    section) has been viewed and logs that action via the MCP context. The tool
    returns the raw Moodle response for callers that need to inspect status or
    warnings.

    Args:
        courseid: ID of the course that was viewed (required).
        sectionnumber: Section number within the course that was viewed
                       (defaults to 0, which is the main page of the course).

    Returns:
        Dictionary with the Moodle response. Expected to contain at least a
        `status` field and optionally a `warnings` list of warning objects.
    """
    # Access Moodle client from lifespan context
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching view for course {courseid}, section {sectionnumber} from Moodle...")

    try:
        result = await client.view_course(courseid, sectionnumber)

        # Inform about success; include status if available
        status_repr = result.get("status") if isinstance(result, dict) else None
        await ctx.info(f"Successfully viewed course {courseid} (status={status_repr})")
        return result

    except Exception as e:
        await ctx.error(f"Error viewing course: {str(e)}")
        raise


@mcp.tool()
async def get_recent_courses(
    ctx: Context[ServerSession, MoodleClient],
    userid: int = 0,
    limit: int = 0,
    offset: int = 0,
    sort: str | None = None
) -> list[dict[str, Any]]:
    """Get the list of courses a user accessed by recency, most recent first.

    Calls `MoodleClient.get_recent_courses` and returns the list of recent courses.

    Args:
        userid (Optional): User ID. If 0 (default), the requesting user is used.
        limit (Optional): Maximum number of results. 0 returns all courses.
        offset (Optional): Result offset for courses.
        sort (Optional): Field to sort by (e.g., "fullname", "shortname").

    Returns:
        List of recent course dictionaries.
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching recent courses for userid={userid}, limit={limit}, offset={offset}, sort={sort}...")

    try:
        courses = await client.get_recent_courses(userid=userid, limit=limit, offset=offset, sort=sort)

        await ctx.info(f"Successfully retrieved {len(courses)} recent course(s)")
        return courses

    except Exception as e:
        await ctx.error(f"Error fetching recent courses: {str(e)}")
        raise


@mcp.tool()
async def get_course_enrolment_methods(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int
) -> list[dict[str, Any]]:
    """Get enrolment methods available for a course.
    Warning: Moodle currently only returns [] for this call, so shouln't be used.

    Calls `MoodleClient.get_course_enrolment_methods` which invokes
    the Moodle webservice function `core_enrol_get_course_enrolment_methods`.

    Args:
        courseid: ID of the course (required).

    Returns:
        List of objects describing the course's enrolment instances.
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching enrolment methods for course {courseid} from Moodle...")

    try:
        methods = await client.get_course_enrolment_methods(courseid)

        await ctx.info(f"Successfully retrieved {len(methods)} enrolment method(s)")
        return methods

    except Exception as e:
        await ctx.error(f"Error fetching course enrolment methods: {str(e)}")
        raise


def run_server():
    """Entry point to run the MCP server."""
    logger.info("Starting Moodle MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
