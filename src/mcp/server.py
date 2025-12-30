"""MCP Server for Moodle API integration."""
import os
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from .protocol import MoodleClient
from .models import Course, CourseUpdate, CourseContentsOption, EnrolledUsersOption, ManualEnrolment, ManualUnenrolment, UserCreate, UserSearchCriteria
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


@mcp.tool()
async def get_users(
    ctx: Context[ServerSession, MoodleClient],
    criteria: list[UserSearchCriteria]
) -> dict[str, Any]:
    """Search for users matching specified criteria.

    Searches for users in Moodle that match the given search criteria.
    Multiple criteria are combined with AND operator.

    Args:
        criteria: List of UserSearchCriterion objects (key/value pairs).
                 Each criterion must have:
                 - key: User column to search by (must be unique):
                   * 'id': Match user ID (value must be numeric string)
                   * 'lastname': Last name (can use '%' as wildcard)
                   * 'firstname': First name (can use '%' as wildcard)
                   * 'idnumber': ID number
                   * 'username': Username
                   * 'email': Email (can use '%' as wildcard)
                   * 'auth': Authentication plugin (e.g., 'manual', 'ldap')
                 - value: Value to search for (cannot be empty)
                 
                 Important notes:
                 - Each key must be unique in the criteria list
                 - Search uses AND operator between valid criteria
                 - Invalid criteria are ignored with warnings
                 - Empty criteria list not recommended (can be very slow)
                 - Use '%' as wildcard for text fields (e.g., 'John%', '%smith')

    Returns:
        Dictionary containing:
        - users: List of user dictionaries found. Each user contains:
          * id: User ID
          * username, firstname, lastname (optional)
          * fullname: Full name
          * email (optional)
          * auth: Authentication plugin (optional)
          * suspended: 1 if suspended, 0 if active (optional)
          * confirmed: 1 if confirmed (optional)
          * idnumber, institution, department (optional)
          * city, country (optional)
          * profileimageurl, profileimageurlsmall: Profile image URLs
          * customfields: List of custom profile fields (optional)
          * preferences: List of user preferences (optional)
          * And other optional fields (phone1, phone2, lang, timezone, etc.)
        - warnings: List of warning objects if any issues occurred:
          * item, itemid, warningcode, message

    Examples:
        # Search by user ID
        criteria = [UserSearchCriterion(key="id", value="5")]
        
        # Search by username
        criteria = [UserSearchCriterion(key="username", value="jdoe")]
        
        # Search by email with wildcard
        criteria = [UserSearchCriterion(key="email", value="%@example.com")]
        
        # Search by multiple criteria (AND operator)
        criteria = [
            UserSearchCriterion(key="lastname", value="Smith"),
            UserSearchCriterion(key="auth", value="manual")
        ]
        
        # Search by partial name
        criteria = [UserSearchCriterion(key="firstname", value="John%")]
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Searching for users with {len(criteria)} criterion/criteria in Moodle...")

    try:
        result = await client.get_users(criteria)
        
        users_found = len(result.get("users", []))
        warnings_count = len(result.get("warnings", []))
        
        if warnings_count > 0:
            await ctx.info(f"Found {users_found} user(s) with {warnings_count} warning(s)")
        else:
            await ctx.info(f"Successfully found {users_found} user(s)")
        
        return result

    except Exception as e:
        await ctx.error(f"Error searching users: {str(e)}")
        raise


@mcp.tool()
async def get_users_courses(
    ctx: Context[ServerSession, MoodleClient],
    userid: int,
    returnusercount: int = 1
) -> list[dict[str, Any]]:
    """Get list of courses where a user is enrolled.

    Returns all courses in which the specified user is enrolled,
    optionally including the count of enrolled users in each course.

    Args:
        userid: User ID (required).
        returnusercount: Include enrolled user count in each course.
                        1 (default) to include the count.
                        0 to omit for better performance (especially useful
                        when user is enrolled in many large courses).

    Returns:
        List of course dictionaries where the user is enrolled. Each course contains:
        - id: Course ID
        - shortname: Course short name
        - fullname: Course full name
        - displayname: Display name for lists (optional)
        - idnumber: Course ID number
        - visible: 1 if visible, 0 if hidden
        - enrolledusercount: Number of enrolled users (optional, only if returnusercount=1)
        - category: Category ID (optional)
        - format: Course format (e.g., 'weeks', 'topics', 'site') (optional)
        - summary: Course summary (optional)
        - summaryformat: Summary format (1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN) (optional)
        - lang: Forced course language (optional)
        - courseimage: Course image URL (optional)
        - startdate, enddate: Course dates as Unix timestamps (optional)
        - timemodified: Last modification timestamp (optional)
        - enablecompletion: 1 if completion tracking enabled (optional)
        - completionhascriteria: 1 if completion criteria are set (optional)
        - completionusertracked: 1 if user is tracked for completion (optional)
        - progress: User's progress percentage (optional)
        - completed: 1 if user completed the course (optional)
        - lastaccess: User's last access timestamp (optional)
        - isfavourite: 1 if user marked course as favourite (optional)
        - hidden: 1 if user hid course from dashboard (optional)
        - marker: Course section marker (optional)
        - showgrades: 1 if grades are shown (optional)
        - showactivitydates: 1 if activity dates are shown
        - showcompletionconditions: 1 if completion conditions are shown
        - overviewfiles: List of overview files attached to course (optional)
          Each file object contains: filename, filepath, filesize, fileurl,
          timemodified, mimetype, isexternalfile, repositorytype, icon

    Examples:
        # Get all courses for user 5 with user counts
        courses = get_users_courses(userid=5)
        
        # Get courses without user counts for better performance
        courses = get_users_courses(userid=5, returnusercount=0)
    """
    client = ctx.request_context.lifespan_context

    if returnusercount == 1:
        await ctx.info(f"Fetching courses for user {userid} with enrolled user counts from Moodle...")
    else:
        await ctx.info(f"Fetching courses for user {userid} (without user counts) from Moodle...")

    try:
        courses = await client.get_users_courses(userid, returnusercount)

        await ctx.info(f"Successfully retrieved {len(courses)} course(s) for user {userid}")
        return courses

    except Exception as e:
        await ctx.error(f"Error fetching user courses: {str(e)}")
        raise


@mcp.tool()
async def get_course_completion_status(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int,
    userid: int
) -> dict[str, Any]:
    """Get course completion status for a user.

    Returns the completion status of a user in a specific course,
    including all completion criteria and their individual statuses.

    Args:
        courseid: Course ID (required).
        userid: User ID (required).

    Returns:
        Dictionary containing:
        - completionstatus: Completion status object:
          * completed: 1 if course is complete for the user, 0 otherwise
          * aggregation: Aggregation method for criteria:
            - 1 (ALL): All criteria must be met
            - 2 (ANY): At least one criterion must be met
          * completions: List of detailed completion criteria:
            - type: Criterion type code (numeric)
            - title: Criterion title
            - status: Status as readable text (e.g., "Yes", "No", "50%")
            - complete: 1 if criterion is complete, 0 if not
            - timecompleted: Timestamp when criterion was completed (0 if not complete)
            - details: Additional details object:
              * type: Criterion type description
              * criteria: Specific criterion description
              * requirement: Requirement description
              * status: Extended status description (any text)
        - warnings: List of warning objects (optional):
          * item, itemid, warningcode, message

    Examples:
        # Get completion status for user 5 in course 10
        status = get_course_completion_status(courseid=10, userid=5)
        
        # Check if user completed the course
        if status['completionstatus']['completed'] == 1:
            print("User completed the course!")
        
        # Check individual criteria
        for criterion in status['completionstatus']['completions']:
            print(f"{criterion['title']}: {criterion['status']}")
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching completion status for user {userid} in course {courseid} from Moodle...")

    try:
        result = await client.get_course_completion_status(courseid, userid)
        
        completion_status = result.get("completionstatus", {})
        is_completed = completion_status.get("completed", 0)
        criteria_count = len(completion_status.get("completions", []))
        warnings_count = len(result.get("warnings", []))
        
        if is_completed == 1:
            await ctx.info(f"User {userid} has completed course {courseid} ({criteria_count} criteria)")
        else:
            await ctx.info(f"User {userid} has not completed course {courseid} ({criteria_count} criteria tracked)")
        
        if warnings_count > 0:
            await ctx.info(f"Note: {warnings_count} warning(s) returned")
        
        return result

    except Exception as e:
        await ctx.error(f"Error fetching course completion status: {str(e)}")
        raise


@mcp.tool()
async def get_activities_completion_status(
    ctx: Context[ServerSession, MoodleClient],
    courseid: int,
    userid: int
) -> dict[str, Any]:
    """Get activities completion status for a user in a course.

    Returns the completion status of all activities (modules) for a user
    in a specific course, including detailed information about each activity's
    completion state and tracking settings.
    WARNING: If the user is not enrolled in the course, Moodle does not return an error,
    but a list with all activities marked as incomplete (state=0).

    Args:
        courseid: Course ID (required).
        userid: User ID (required).

    Returns:
        Dictionary containing:
        - statuses: List of activity completion status objects:
          * cmid: Course module ID
          * modname: Module type name (e.g., 'quiz', 'assign', 'forum')
          * instance: Activity instance ID within the module
          * state: Completion state:
            - 0: Incomplete
            - 1: Complete
            - 2: Complete and passed
            - 3: Complete and failed
          * timecompleted: Timestamp when completed (0 if not complete)
          * tracking: Completion tracking type:
            - 0: None
            - 1: Manual
            - 2: Automatic
          * overrideby: User ID who overrode the status, or null (optional)
          * hascompletion: 1 if completion enabled for this activity (optional)
          * isautomatic: 1 if activity tracks completion automatically (optional)
          * istrackeduser: 1 if completion tracked for this user (optional)
          * uservisible: 1 if activity is visible to user (optional)
          * isoverallcomplete: 1 if overall completion should be marked complete (optional)
          * valueused: If completion status affects another activity availability (optional)
          * details: List of completion rule details (optional):
            - rulename: Name of the rule
            - rulevalue: Object with status and description
        - warnings: List of warning objects (optional):
          * item, itemid, warningcode, message

    Examples:
        # Get all activities completion status for user 5 in course 10
        activities = get_activities_completion_status(courseid=10, userid=5)
        
        # Check completion status of each activity
        for activity in activities['statuses']:
            state_text = [
                "Incomplete",
                "Complete",
                "Complete and passed",
                "Complete and failed"
            ][activity['state']]
            print(f"{activity['modname']} (ID {activity['cmid']}): {state_text}")
        
        # Filter only completed activities
        completed = [a for a in activities['statuses'] if a['state'] >= 1]
        print(f"Completed activities: {len(completed)}")
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Fetching activities completion status for user {userid} in course {courseid} from Moodle...")

    try:
        result = await client.get_activities_completion_status(courseid, userid)
        
        statuses = result.get("statuses", [])
        warnings_count = len(result.get("warnings", []))
        
        # Count activities by state
        incomplete = sum(1 for s in statuses if s.get("state", 0) == 0)
        complete = sum(1 for s in statuses if s.get("state", 0) == 1)
        passed = sum(1 for s in statuses if s.get("state", 0) == 2)
        failed = sum(1 for s in statuses if s.get("state", 0) == 3)
        
        total = len(statuses)
        await ctx.info(
            f"Retrieved {total} activities: {complete} complete, {passed} passed, "
            f"{failed} failed, {incomplete} incomplete"
        )
        
        if warnings_count > 0:
            await ctx.info(f"Note: {warnings_count} warning(s) returned")
        
        return result

    except Exception as e:
        await ctx.error(f"Error fetching activities completion status: {str(e)}")
        raise


@mcp.tool()
async def update_activity_completion_status_manually(
    ctx: Context[ServerSession, MoodleClient],
    cmid: int,
    completed: int
) -> dict[str, Any]:
    """Update activity completion status manually for the current user.

    Manually marks an activity as complete or incomplete for the current user.
    This only works for activities that have manual completion tracking enabled.
    If the activity uses automatic completion tracking, this operation will fail
    with a warning.

    Args:
        cmid: Course module ID (activity ID) (required).
              This is the unique identifier for the activity within the course.
        completed: Completion status to set (required):
                  - 1: Mark the activity as complete
                  - 0: Mark the activity as incomplete

    Returns:
        Dictionary containing:
        - status: Operation result:
          * 1: Operation was successful
          * 0: Operation failed
        - warnings: List of warning objects (optional):
          * item: Item type identifier (e.g., 'cmid')
          * itemid: Specific item ID that caused the warning
          * warningcode: Code identifying the type of warning
          * message: Human-readable description of the warning
          
          Common warnings include:
          - Activity does not have manual completion tracking enabled
          - User does not have permission to update completion status
          - Activity or course module does not exist
          - User is not enrolled in the course containing the activity

    Examples:
        # Mark activity with cmid 42 as complete
        result = update_activity_completion_status_manually(cmid=42, completed=1)
        if result['status'] == 1:
            print("Activity marked as complete!")
        
        # Undo completion for activity with cmid 42
        result = update_activity_completion_status_manually(cmid=42, completed=0)
        
        # Check for warnings
        if result.get('warnings'):
            for warning in result['warnings']:
                print(f"Warning: {warning['message']}")
    """
    client = ctx.request_context.lifespan_context

    status_text = "complete" if completed == 1 else "incomplete"
    await ctx.info(f"Updating activity {cmid} completion status to {status_text}...")

    try:
        result = await client.update_activity_completion_status_manually(cmid, completed)
        
        operation_status = result.get("status", 0)
        warnings = result.get("warnings", [])
        
        if operation_status == 1:
            await ctx.info(f"Successfully updated activity {cmid} to {status_text}")
        else:
            await ctx.info(f"Failed to update activity {cmid} (status={operation_status})")
        
        if warnings:
            await ctx.info(f"Note: {len(warnings)} warning(s) returned")
            for warning in warnings:
                await ctx.info(f"  - {warning.get('message', 'Unknown warning')}")
        
        return result

    except Exception as e:
        await ctx.error(f"Error updating activity completion status: {str(e)}")
        raise


@mcp.tool()
async def get_site_info(
    ctx: Context[ServerSession, MoodleClient]
) -> dict[str, Any]:
    """Get site information, current user details and available webservice functions.

    Retrieves comprehensive information about the Moodle site, the authenticated user,
    and the list of webservice functions available to the current user/token.
    This is useful for understanding the current user's capabilities, site configuration,
    and what operations are available through the webservice.

    Note:
        The Moodle API function accepts a deprecated parameter `serviceshortnames`
        which is ignored by the API. This parameter is not exposed in this tool
        as it serves no purpose.

    Returns:
        Dictionary containing extensive site and user information:
        
        User Information:
        - userid: Current user ID
        - username: Username of the authenticated user
        - firstname: User's first name
        - lastname: User's last name
        - fullname: User's complete name
        - userpictureurl: Public URL of user's profile picture
        - lang: Current language code (e.g., 'en', 'es')
        - userissiteadmin: 1 if user is site administrator (optional)
        - userhomepage: Default homepage setting (0=Site, 1=Dashboard, 4=Custom) (optional)
        - userhomepageurl: Custom homepage URL if userhomepage is 4 (optional)
        
        Site Information:
        - sitename: Name of the Moodle site
        - siteurl: Base URL of the site
        - siteid: ID of the site course (optional)
        - release: Moodle release number (e.g., "4.4.1") (optional)
        - version: Moodle version string (optional)
        - mobilecssurl: URL for mobile custom CSS (optional)
        - sitecalendartype: Calendar type configured for the site (optional)
        - usercalendartype: Calendar type used by this user (optional)
        - theme: Current theme name for the user (optional)
        
        Capabilities and Limits:
        - downloadfiles: 1 if user can download files (optional)
        - uploadfiles: 1 if user can upload files (optional)
        - usercanmanageownfiles: 1 if user can manage their own files (optional)
        - userquota: User's storage quota in bytes (0 = unlimited) (optional)
        - usermaxuploadfilesize: Maximum upload file size in bytes (-1 = unlimited) (optional)
        - limitconcurrentlogins: Number of concurrent sessions allowed (optional)
        - usersessionscount: Number of currently active sessions for this user (optional)
        - policyagreed: 1 if user has agreed to all site policies (optional)
        
        Webservice Functions:
        - functions: List of available webservice function objects. Each contains:
          * name: Name of the webservice function (e.g., 'core_course_get_courses')
          * version: Version of the component providing the function
        
        Advanced Features:
        - advancedfeatures: List of site's advanced features and their status (optional):
          * name: Feature name
          * value: Usually 1 when enabled, 0 when disabled
        
        Access:
        - userprivateaccesskey: User's private access key for secure file retrieval (optional)

    Examples:
        # Get all site and user information
        info = get_site_info()
        print(f"Site: {info['sitename']}")
        print(f"User: {info['fullname']} ({info['username']})")
        print(f"Is admin: {info.get('userissiteadmin', 0) == 1}")
        
        # Check available functions
        functions = info.get('functions', [])
        print(f"Available functions: {len(functions)}")
        for func in functions:
            print(f"  - {func['name']}")
        
        # Check user capabilities
        if info.get('uploadfiles', 0) == 1:
            print("User can upload files")
        if info.get('downloadfiles', 0) == 1:
            print("User can download files")
    """
    client = ctx.request_context.lifespan_context

    await ctx.info("Fetching site information and available webservice functions...")

    try:
        result = await client.get_site_info()
        
        # Extract key information for logging
        sitename = result.get("sitename", "Unknown")
        username = result.get("username", "Unknown")
        fullname = result.get("fullname", "Unknown")
        is_admin = result.get("userissiteadmin", 0) == 1
        functions_count = len(result.get("functions", []))
        
        await ctx.info(f"Site: {sitename}")
        await ctx.info(f"User: {fullname} ({username})" + (" [ADMIN]" if is_admin else ""))
        await ctx.info(f"Available webservice functions: {functions_count}")
        
        # Log some useful capabilities if present
        capabilities = []
        if result.get("uploadfiles", 0) == 1:
            capabilities.append("upload files")
        if result.get("downloadfiles", 0) == 1:
            capabilities.append("download files")
        if result.get("usercanmanageownfiles", 0) == 1:
            capabilities.append("manage own files")
        
        if capabilities:
            await ctx.info(f"User capabilities: {', '.join(capabilities)}")
        
        return result

    except Exception as e:
        await ctx.error(f"Error fetching site info: {str(e)}")
        raise


@mcp.tool()
async def manual_unenrol_users(
    ctx: Context[ServerSession, MoodleClient],
    enrolments: list[ManualUnenrolment]
) -> dict[str, Any]:
    """Manually unenrol users from courses.

    Removes user enrolments from courses. This can either remove specific roles
    or completely unenrol the user by removing all their roles from the course.
    This operation is permanent and cannot be undone through this function.

    Args:
        enrolments: List of ManualUnenrolment objects. Each unenrolment must have:
                   Required fields:
                   - userid: User ID to unenrol
                   - courseid: Course ID from which to unenrol the user
                   
                   Optional field:
                   - roleid: Specific role ID to remove. If not specified,
                            ALL roles will be removed, completely unenrolling
                            the user from the course.

    Returns:
        Dictionary result. An empty dictionary ({}) indicates success.
        On error, an exception is raised (e.g., invalid_parameter_exception).

    Examples:
        # Completely unenrol user 5 from course 10 (remove all roles)
        enrolments = [ManualUnenrolment(userid=5, courseid=10)]
        result = manual_unenrol_users(enrolments=enrolments)
        
        # Remove only the student role (role 5) for user 5 in course 10
        # User will remain enrolled with other roles if they have any
        enrolments = [ManualUnenrolment(userid=5, courseid=10, roleid=5)]
        result = manual_unenrol_users(enrolments=enrolments)
        
        # Unenrol multiple users from the same course
        enrolments = [
            ManualUnenrolment(userid=5, courseid=10),
            ManualUnenrolment(userid=6, courseid=10),
            ManualUnenrolment(userid=7, courseid=10)
        ]
        result = manual_unenrol_users(enrolments=enrolments)
        
        # Mix of complete and partial unenrolments
        enrolments = [
            ManualUnenrolment(userid=5, courseid=10),  # Complete unenrolment
            ManualUnenrolment(userid=6, courseid=10, roleid=5)  # Remove only role 5
        ]
        result = manual_unenrol_users(enrolments=enrolments)

    Important Notes:
        - If roleid is not specified, the user will be COMPLETELY unenrolled
          from the course (all roles removed)
        - If roleid is specified, only that specific role will be removed.
          The user will remain enrolled if they have other roles in the course
        - This operation requires appropriate permissions (typically teacher
          or manager role in the course)
        - Attempting to unenrol a user who is not enrolled will raise an error
    """
    client = ctx.request_context.lifespan_context

    await ctx.info(f"Processing {len(enrolments)} unenrolment operation(s)...")

    try:
        result = await client.manual_unenrol_users(enrolments)
        
        # Count operations by type (check if roleid is None)
        complete_unenrolments = sum(1 for e in enrolments if e.roleid is None)
        partial_unenrolments = len(enrolments) - complete_unenrolments
        
        if complete_unenrolments > 0:
            await ctx.info(f"Complete unenrolments (all roles removed): {complete_unenrolments}")
        if partial_unenrolments > 0:
            await ctx.info(f"Partial unenrolments (specific role removed): {partial_unenrolments}")
        
        # Empty result means success
        if not result or result == {}:
            await ctx.info("Successfully processed all unenrolment operations")
        
        return result

    except Exception as e:
        await ctx.error(f"Error unenrolling users: {str(e)}")
        raise


def run_server():
    """Entry point to run the MCP server."""
    logger.info("Starting Moodle MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
