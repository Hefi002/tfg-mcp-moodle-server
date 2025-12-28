"""MCP Server for Moodle API integration."""
import os
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from .protocol import MoodleClient
from .models import Course, CourseUpdate, CourseContentsOption, EnrolledUsersOption, ManualEnrolment, UserCreate
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
    WARNING: When a course is created through this method, no user is enroled
    by default. You need to manually enrol users after creation.
    Use of method `manual_enrol_users` is recommended for that.

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


@mcp.tool()
async def get_enrolled_users(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int,
    options: EnrolledUsersOption | None = None
) -> list[dict[str, Any]]:
    """Get list of users enrolled in a course.

    Returns the list of users enrolled in a course by its ID.
    Optionally filter and sort results using the options parameter.

    Args:
        courseid: Course ID (required).
        options: Optional EnrolledUsersOption object to filter results.
                Available filters:
                - withcapability: Return only users with this capability
                  (requires moodle/role:review permission)
                - groupid: Return only users in this group
                  (requires moodle/site:accessallgroups if querying user not in group)
                - onlyactive: 1 to return only users with active enrolments
                  (requires moodle/course:enrolreview, incompatible with onlysuspended)
                - onlysuspended: 1 to return only suspended users
                  (requires moodle/course:enrolreview, incompatible with onlyactive)
                - userfields: Comma-separated list of user fields to return
                  (e.g., "id,firstname,lastname,email")
                - limitfrom: SQL offset for pagination
                - limitnumber: Maximum number of users to return
                - sortby: Field to sort by (id, firstname, lastname, siteorder)
                - sortdirection: Sort direction (ASC or DESC)

    Returns:
        List of enrolled user dictionaries. Each user object contains:
        - id: User ID
        - fullname: Full name
        - username, firstname, lastname, email (optional)
        - profileimageurl, profileimageurlsmall (optional)
        - customfields: List of custom profile fields (optional)
        - groups: List of course groups the user belongs to (optional)
        - roles: List of user roles in this course (optional)
        - And other optional fields depending on userfields parameter
    """
    client = ctx.request_context.lifespan_context

    if options:
        await ctx.info(f"Fetching enrolled users for course {courseid} with filters from Moodle...")
    else:
        await ctx.info(f"Fetching all enrolled users for course {courseid} from Moodle...")

    try:
        users = await client.get_enrolled_users(courseid, options)

        await ctx.info(f"Successfully retrieved {len(users)} enrolled user(s)")
        return users

    except Exception as e:
        await ctx.error(f"Error fetching enrolled users: {str(e)}")
        raise


@mcp.tool()
async def manual_enrol_users(
    ctx: Context[ServerSession, MoodleClient],
    enrolments: list[ManualEnrolment]
) -> dict[str, Any]:
    """Manually enrol users in courses.

    Performs manual enrolment of one or more users in courses.
    Each enrolment operation specifies a user, course, and role.

    Args:
        enrolments: List of ManualEnrolment objects. Each must have:
                   Required fields:
                   - roleid: Role ID to assign to the user in the course
                   - userid: User ID to enrol
                   - courseid: Course ID in which to enrol the user
                   
                   Optional fields:
                   - timestart: Enrolment start timestamp (Unix timestamp).
                               0 means immediate or use default configuration
                   - timeend: Enrolment end timestamp (Unix timestamp).
                             0 means no time restriction
                   - suspend: Set to 1 to create enrolment in suspended state.
                             0 or omit for active enrolment

    Returns:
        Result dictionary. An empty result ({}) indicates success.
        On error, raises an exception (e.g., invalid_parameter_exception).

    Examples:
        # Enrol user 5 in course 10 with role 5 (student)
        enrolments = [ManualEnrolment(roleid=5, userid=5, courseid=10)]
        
        # Enrol with time restrictions
        enrolments = [ManualEnrolment(
            roleid=5, userid=5, courseid=10,
            timestart=1640000000, timeend=1672000000
        )]
        
        # Enrol in suspended state
        enrolments = [ManualEnrolment(
            roleid=5, userid=5, courseid=10, suspend=1
        )]
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Enrolling {len(enrolments)} user(s) in Moodle courses...")

    try:
        result = await client.manual_enrol_users(enrolments)

        # Empty result or dict without errors means success
        if not result or (isinstance(result, dict) and not result.get('exception')):
            await ctx.info(f"Successfully enrolled {len(enrolments)} user(s)")
        else:
            await ctx.info(f"Enrolment completed with response: {result}")
        
        return result

    except Exception as e:
        await ctx.error(f"Error enrolling users: {str(e)}")
        raise


@mcp.tool()
async def create_users(
    ctx: Context[ServerSession, MoodleClient],
    users: list[UserCreate]
) -> list[dict[str, Any]]:
    """Create one or more users in Moodle.

    Creates new user accounts in the Moodle instance.
    Each user must have unique username and email.

    Args:
        users: List of UserCreate objects. Each must have:
              Required fields:
              - username: Username (unique). Must follow Moodle security policy
              - firstname: First name(s) of the user
              - lastname: Last name(s) of the user
              - email: Valid and unique email address
              
              Password options (mutually exclusive):
              - createpassword: Set to 1 to have system create and email password
              - password: Plain text password
              
              Common optional fields:
              - auth: Authentication plugin (default: 'manual', e.g., 'ldap')
              - idnumber: Arbitrary ID code (default: empty string)
              - lang: Language code (default: 'en', e.g., 'es')
              - calendartype: Calendar type (default: 'gregorian')
              - city: User's city
              - country: Country code (e.g., 'ES', 'MX')
              - timezone: Timezone (e.g., 'America/Mexico_City', '99' for site default)
              - maildisplay: Email visibility (privacy setting)
              - mailformat: Email format preference (0=plain text, 1=HTML)
              - description: Profile description (no HTML)
              - firstnamephonetic, lastnamephonetic: Phonetic name variants
              - middlename, alternatename: Additional name fields
              - interests: Comma-separated interests
              - institution, department: Organizational info
              - phone1, phone2: Contact numbers
              - address: Postal address
              - theme: Theme name (must exist in Moodle)
              - customfields: List of custom profile fields (type, value)
              - preferences: List of user preferences (type, value)

    Returns:
        List of created user dictionaries. Each contains:
        - id: Assigned user ID in Moodle
        - username: Username of the new user

    Examples:
        # Create basic user with auto-generated password
        users = [UserCreate(
            username="jdoe",
            firstname="John",
            lastname="Doe",
            email="jdoe@example.com",
            createpassword=1
        )]
        
        # Create user with specific password and additional info
        users = [UserCreate(
            username="jsmith",
            firstname="Jane",
            lastname="Smith",
            email="jsmith@example.com",
            password="SecurePass123!",
            city="Barcelona",
            country="ES",
            lang="es",
            institution="Example University",
            department="Computer Science"
        )]
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Creating {len(users)} user(s) in Moodle...")

    try:
        created_users = await client.create_users(users)

        await ctx.info(f"Successfully created {len(created_users)} user(s)")
        return created_users

    except Exception as e:
        await ctx.error(f"Error creating users: {str(e)}")
        raise


def run_server():
    """Entry point to run the MCP server."""
    logger.info("Starting Moodle MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
