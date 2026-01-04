"""Moodle API client implementation."""
import httpx
from typing import Any
from .utils.logger import get_logger
from .models import Course, CourseUpdate, CourseContentsOption, EnrolledUsersOption, ManualEnrolment, ManualUnenrolment, UserCreate, UserSearchCriteria, GradeItemDetails, StudentGrade

logger = get_logger(__name__)


def flatten_params(params: dict[str, Any], parent_key: str = '') -> dict[str, Any]:
    """Flatten nested dictionary/list structures to Moodle API format.
    
    Converts nested structures from standard Python dict/list format to Moodle's
    expected flattened format with bracketed keys. This is required for all Moodle
    API requests that include arrays or nested objects.
    
    Args:
        params: Dictionary potentially containing nested dicts/lists
        parent_key: Key prefix for recursion (used internally)
    
    Returns:
        Flattened dictionary with Moodle-formatted keys
        
    Example:
        Input: {"courses": [{"fullname": "Test", "categoryid": 1}]}
        Output: {"courses[0][fullname]": "Test", "courses[0][categoryid]": 1}
    """
    items = []
    
    for key, value in params.items():
        new_key = f"{parent_key}[{key}]" if parent_key else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            items.extend(flatten_params(value, new_key).items())
        elif isinstance(value, list):
            # Flatten lists with index notation
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    items.extend(flatten_params(item, f"{new_key}[{i}]").items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, value))
    
    return dict(items)


class MoodleClient:
    """Client for interacting with Moodle Web Services API.
    
    Provides methods for all implemented Moodle webservice functions, handling
    request formatting, HTTP communication, and response parsing. Each method
    corresponds to a specific Moodle webservice function.
    """

    def __init__(self, base_url: str, token: str):
        """Initialize Moodle client with connection parameters.

        Args:
            base_url: Base URL of Moodle instance (e.g., http://localhost:8000)
            token: Web service token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.api_endpoint = f"{self.base_url}/webservice/rest/server.php"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _call_function(
            self,
            function_name: str,
            **params: Any
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Call a Moodle web service function (internal use only).
        
        Makes HTTP POST request to Moodle API endpoint with authentication and formatting.
        Handles parameter flattening, response validation, and error checking. This method
        is the central point for all Moodle API communication.

        Args:
            function_name: Name of the Moodle web service function
            **params: Function parameters as keyword arguments

        Returns:
            Response data from Moodle API (dict, list, str, int, or None depending on function)

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If Moodle returns an error response or unexpected data type
        """
        # Build request parameters
        request_params = {
            "wstoken": self.token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
            **params
        }

        logger.debug(f"Calling Moodle function: {function_name}")
        logger.debug(f"Parameters: {params}")

        # Flatten nested structures for Moodle's format
        flattened_params = flatten_params(request_params)
        logger.debug(f"Flattened parameters: {flattened_params}")

        try:
            response = await self.client.post(
                self.api_endpoint,
                data=flattened_params
            )
            response.raise_for_status()

            data = response.json()

            # Check for unexpected response type
            if not isinstance(data, (dict, list, str, int, type(None))):
                logger.error(f"Unexpected response type: {type(data).__name__}")
                raise ValueError(f"Moodle API returned unexpected type: {type(data).__name__}")
            # Check for Moodle API error
            elif isinstance(data, dict) and "exception" in data:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"Moodle API error: {error_msg}")
                raise ValueError(f"Moodle API error: {error_msg}")

            logger.debug(f"Response received: {len(str(data))} bytes")
            return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Moodle: {e}")
            raise

    # ============================================================================
    # Course Calls
    # ============================================================================

    async def get_courses(self, courseids: list[int] | None = None) -> list[dict[str, Any]]:
        """Get courses from Moodle.
        
        Retrieves course information from the Moodle instance. Can fetch all courses
        or specific courses by their IDs. Each course includes comprehensive metadata.

        Args:
            courseids: Optional list of course IDs to retrieve specific courses.
                      If None or empty, returns all courses.

        Returns:
            List of course dictionaries containing course metadata such as id, shortname,
            fullname, categoryid, summary, format, visibility, dates, and other fields
        """
        params = {}
        if courseids:
            params["options"] = {"ids": courseids}
        
        result = await self._call_function("core_course_get_courses", **params)
        if isinstance(result, list):
            return result
        return []

    async def create_courses(self, courses: list[Course]) -> list[dict[str, Any]]:
        """Create one or more courses in Moodle.
        
        Creates new course instances in the Moodle database. Each course must have
        required fields (fullname, shortname, categoryid) and can include optional
        configuration fields. Note that no users are enrolled by default.
        
        WARNING: When a course is created through this method, no user is enrolled
        by default. You need to manually enroll users after creation using manual_enrol_users.

        Args:
            courses: List of Course objects to create. Each Course must have:
                    Required fields:
                    - fullname: Full course name
                    - shortname: Unique short name
                    - categoryid: Category ID (must be > 0)
                    Optional fields include summary, format, visible, dates, grading options, etc.

        Returns:
            List of created course dictionaries with their assigned IDs and all fields
        """
        # Convert Course models to dictionaries
        courses_data = [course.to_moodle_dict() for course in courses]
        
        result = await self._call_function(
            "core_course_create_courses",
            courses=courses_data
        )
        if isinstance(result, list):
            return result
        return []

    async def update_courses(self, courses: list[CourseUpdate]) -> dict[str, Any]:
        """Update one or more courses in Moodle.
        
        Modifies existing course configuration. Only specified fields are updated;
        other fields remain unchanged. Useful for bulk course updates or single field changes.

        Args:
            courses: List of CourseUpdate objects with course ID and fields to update.
                    Each CourseUpdate must have:
                    Required field:
                    - id: Course ID to update (must be > 0)
                    
                    Optional fields (only specify what you want to change):
                    - fullname, shortname, categoryid, summary, format, visible, dates,
                      grading options, and any other course field

        Returns:
            Result dictionary (usually contains warnings array if any issues occurred)
        """
        # Convert CourseUpdate models to dictionaries
        courses_data = [course.to_moodle_dict() for course in courses]
        
        result = await self._call_function(
            "core_course_update_courses",
            courses=courses_data
        )
        if isinstance(result, dict):
            return result
        return {}

    async def delete_courses(self, courseids: list[int]) -> dict[str, Any]:
        """Delete one or more courses from Moodle.
        
        Permanently removes courses from the Moodle instance. This action cannot be undone
        and will delete all course content, enrollments, and related data.
        
        WARNING: This action cannot be undone!

        Args:
            courseids: List of course IDs to delete. Each ID must be a valid course ID
                      that exists in the Moodle instance.

        Returns:
            Result dictionary containing:
            - warnings: Array of warning messages if any issues occurred during deletion
                       (e.g., if a course ID doesn't exist or user lacks permissions)
        """
        result = await self._call_function(
            "core_course_delete_courses",
            courseids=courseids
        )
        if isinstance(result, dict):
            return result
        return {}

    async def get_course_contents(
        self, 
        courseid: int, 
        options: CourseContentsOption | None = None
    ) -> list[dict[str, Any]]:
        """Get course contents (sections and modules) from Moodle.
        
        Retrieves the complete course structure including all sections and their modules
        (activities and resources). Can be filtered using options to retrieve only specific
        sections, modules, or module types.

        Args:
            courseid: Course ID to get contents from
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
        params: dict[str, Any] = {"courseid": courseid}
        
        if options:
            # Convert to dict and create list of {name, value} objects for Moodle API
            params["options"] = options.to_moodle_dict()
        
        result = await self._call_function(
            "core_course_get_contents",
            **params
        )
        if isinstance(result, list):
            return result
        return []

    async def view_course(self, courseid: int, sectionnumber: int = 0) -> dict[str, Any]:
        """Log that the course was viewed.
        
        Notifies Moodle that a course or specific section has been viewed, triggering
        activity logs and completion tracking. This is used to track user engagement.

        Args:
            courseid: ID of the course that was viewed (required).
            sectionnumber: Section number within the course that was viewed
                          (defaults to 0, which is the main page of the course).

        Returns:
            Dictionary with the Moodle response. Expected to contain:
            - status: Operation success indicator
            - warnings: List of warning objects (optional)
        """
        params: dict[str, Any] = {
            "courseid": courseid,
            "sectionnumber": sectionnumber
        }

        result = await self._call_function(
            "core_course_view_course",
            **params
        )

        if isinstance(result, dict):
            return result
        return {}

    async def get_recent_courses(
        self,
        userid: int = 0,
        limit: int = 0,
        offset: int = 0,
        sort: str | None = None
    ) -> list[dict[str, Any]]:
        """Get the list of courses a user accessed by recency, most recent first.
        
        Retrieves courses ordered by last access time. Useful for displaying recently
        accessed courses in dashboards or navigation menus.

        Args:
            userid: User ID. If 0 (default), the requesting user is used.
            limit: Maximum number of results. 0 returns all courses.
            offset: Result offset for pagination.
            sort: Field to sort by (e.g., "fullname", "shortname").

        Returns:
            List of recent course dictionaries ordered by access time
        """
        params: dict[str, Any] = {}

        # Only include parameters that differ from their defaults to avoid
        # sending unnecessary values to the API.
        if userid:
            params["userid"] = userid
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if sort is not None:
            params["sort"] = sort

        result = await self._call_function(
            "core_course_get_recent_courses",
            **params
        )

        if isinstance(result, list):
            return result
        return []

    async def close(self) -> None:
        """Close the HTTP client connection.
        
        Properly closes the HTTP client to release resources. Should be called when
        the MoodleClient is no longer needed, typically in cleanup/shutdown procedures.
        
        Returns:
            None
        """
        await self.client.aclose()

    async def get_course_module(self, cmid: int) -> dict[str, Any]:
        """Get detailed information about a specific course module.
        
        Retrieves comprehensive metadata about a course module (activity or resource),
        including identification, visibility, completion settings, grading configuration,
        group settings, and more.

        Args:
            cmid: Course module ID (required).

        Returns:
            Dictionary containing:
            - cm: Course module object with complete information:
              * Identification: id, course, module, modname, instance, name, section, etc.
              * Visibility: visible, visibleoncoursepage, availability, etc.
              * Groups: groupmode, groupingid
              * Completion: completion, completionview, completionpassgrade, etc.
              * Grading: grade, gradepass, gradecat, scale, advancedgrading, outcomes
              * Format: indent, score
            - warnings: List of warning objects (optional)
        """
        result = await self._call_function(
            "core_course_get_course_module",
            cmid=cmid
        )

        if isinstance(result, dict):
            return result
        return {"cm": {}, "warnings": []}

    # ============================================================================
    # Enrol Calls
    # ============================================================================

    async def get_course_enrolment_methods(self, courseid: int) -> list[dict[str, Any]]:
        """Get enrolment methods available for a course.
        
        Retrieves the list of enrolment methods (plugins) configured for a specific course,
        including their status and configuration.
        
        WARNING: Moodle currently only returns [] for this call, so shouldn't be used.

        Args:
            courseid: ID of the course (required).

        Returns:
            List of objects describing the course's enrolment instances. Each contains:
            - id, courseid, type, name, status, and other enrolment method fields
        """

        result = await self._call_function(
            "core_enrol_get_course_enrolment_methods",
            courseid=courseid
        )
        if isinstance(result, list):
            return result
        return []

    async def get_enrolled_users(
        self,
        courseid: int,
        options: EnrolledUsersOption | None = None
    ) -> list[dict[str, Any]]:
        """Get list of users enrolled in a course.
        
        Retrieves all users enrolled in a course with their profile information, roles,
        and enrolment status. Can be filtered by capability, group, active status, and more.

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
                    - limitfrom: SQL offset for pagination
                    - limitnumber: Maximum number of users to return
                    - sortby: Field to sort by (id, firstname, lastname, siteorder)
                    - sortdirection: Sort direction (ASC or DESC)

        Returns:
            List of enrolled user dictionaries. Each user object contains:
            - id, fullname, username, firstname, lastname, email (optional)
            - profileimageurl, profileimageurlsmall (optional)
            - customfields: List of custom profile fields (optional)
            - groups: List of course groups the user belongs to (optional)
            - roles: List of user roles in this course (optional)
        """
        params: dict[str, Any] = {"courseid": courseid}

        if options:
            # Convert to list of {name, value} objects for Moodle API
            params["options"] = options.to_moodle_dict()

        result = await self._call_function(
            "core_enrol_get_enrolled_users",
            **params
        )

        if isinstance(result, list):
            return result
        return []

    async def manual_enrol_users(self, enrolments: list[ManualEnrolment]) -> dict[str, Any]:
        """Manually enrol users in courses.
        
        Performs manual enrolment of one or more users in courses. Each enrolment
        operation specifies a user, course, role, and optional time restrictions.

        Args:
            enrolments: List of ManualEnrolment objects. Each must have:
                       Required fields:
                       - roleid: Role ID to assign to the user
                       - userid: User ID to enrol
                       - courseid: Course ID in which to enrol the user
                       
                       Optional fields:
                       - timestart: Enrolment start timestamp (0 = immediate/default)
                       - timeend: Enrolment end timestamp (0 = no restriction)
                       - suspend: 1 to create suspended enrolment, 0 for active

        Returns:
            Result dictionary. An empty result ({}) indicates success.
            On error, raises an exception (e.g., invalid_parameter_exception).
        """
        # Convert ManualEnrolment models to dictionaries
        enrolments_data = [enrolment.to_moodle_dict() for enrolment in enrolments]

        result = await self._call_function(
            "enrol_manual_enrol_users",
            enrolments=enrolments_data
        )

        # The API typically returns null/None on success, but we'll handle both cases
        if result is None:
            return {}
        if isinstance(result, dict):
            return result
        return {}

    async def manual_unenrol_users(self, enrolments: list[ManualUnenrolment]) -> dict[str, Any]:
        """Manually unenrol users from courses.
        
        Removes user enrolments from courses. Can remove specific roles or completely
        unenrol the user by removing all roles. This operation is permanent.

        Args:
            enrolments: List of ManualUnenrolment objects. Each must have:
                       Required fields:
                       - userid: User ID to unenrol
                       - courseid: Course ID from which to unenrol the user

                       Optional field:
                       - roleid: Specific role ID to remove. If not specified,
                                all roles will be removed (complete unenrolment)

        Returns:
            Result dictionary. An empty dictionary ({}) indicates success.
            On error, an exception is raised (e.g., invalid_parameter_exception).
        """
        # Convert ManualUnenrolment models to dictionaries
        enrolments_data = [enrolment.to_moodle_dict() for enrolment in enrolments]

        result = await self._call_function(
            "enrol_manual_unenrol_users",
            enrolments=enrolments_data
        )

        # The API typically returns null/None on success, but we'll handle both cases
        if result is None:
            return {}
        if isinstance(result, dict):
            return result
        return {}

    # ============================================================================
    # User Calls
    # ============================================================================

    async def create_users(self, users: list[UserCreate]) -> list[dict[str, Any]]:
        """Create one or more users in Moodle.
        
        Creates new user accounts in the Moodle instance. Each user must have unique
        username and email. Password can be auto-generated or specified manually.

        Args:
            users: List of UserCreate objects. Each must have:
                  Required fields:
                  - username: Username (unique, follows Moodle security policy)
                  - firstname: First name(s) of the user
                  - lastname: Last name(s) of the user
                  - email: Valid and unique email address
                  
                  Password options (mutually exclusive):
                  - createpassword: Set to 1 to have system create and email password
                  - password: Plain text password
                  
                  Common optional fields:
                  - auth: Authentication plugin (default: 'manual')
                  - idnumber, lang, calendartype, city, country, timezone
                  - maildisplay, mailformat, description
                  - institution, department, phone1, phone2, address
                  - theme, customfields, preferences

        Returns:
            List of created user dictionaries. Each contains:
            - id: Assigned user ID
            - username: Username of the new user
        """
        # Convert UserCreate models to dictionaries
        users_data = [user.to_moodle_dict() for user in users]

        result = await self._call_function(
            "core_user_create_users",
            users=users_data
        )

        if isinstance(result, list):
            return result
        return []

    async def get_users(self, criteria: list[UserSearchCriteria]) -> dict[str, Any]:
        """Search for users matching specified criteria.
        
        Searches for users in Moodle that match the given search criteria.
        Multiple criteria are combined with AND operator. Supports wildcards.

        Args:
            criteria: List of UserSearchCriterion objects (key/value pairs).
                     Each criterion must have:
                     - key: User column to search by:
                       * 'id': Match user ID (value must be numeric string)
                       * 'lastname': Last name (can use '%' as wildcard)
                       * 'firstname': First name (can use '%' as wildcard)
                       * 'idnumber': ID number
                       * 'username': Username
                       * 'email': Email (can use '%' as wildcard)
                       * 'auth': Authentication plugin (e.g., 'manual', 'ldap')
                     - value: Value to search for (cannot be empty)
                     
                     NOTE: Each key must be unique. Search uses AND operator between
                     valid criteria. Use '%' as wildcard for text fields.

        Returns:
            Dictionary containing:
            - users: List of user dictionaries found with fields like id, username,
              firstname, lastname, fullname, email, suspended, confirmed, and more
            - warnings: List of warning objects (optional)
        """
        # Convert UserSearchCriterion models to dictionaries
        criteria_data = [criterion.to_moodle_dict() for criterion in criteria]

        result = await self._call_function(
            "core_user_get_users",
            criteria=criteria_data
        )

        if isinstance(result, dict):
            return result
        return {"users": [], "warnings": []}

    async def get_users_courses(self, userid: int, returnusercount: int = 1) -> list[dict[str, Any]]:
        """Get list of courses where a user is enrolled.
        
        Returns all courses in which the specified user is enrolled, optionally including
        the count of enrolled users in each course for better context.

        Args:
            userid: User ID (required).
            returnusercount: Include enrolled user count in each course.
                            1 (default) to include count.
                            0 to omit for better performance (useful when user is
                            enrolled in many large courses).

        Returns:
            List of course dictionaries where the user is enrolled. Each contains:
            - id, shortname, fullname, displayname, idnumber, visible
            - enrolledusercount: Number of enrolled users (only if returnusercount=1)
            - category, format, summary, lang, courseimage
            - startdate, enddate, timemodified
            - enablecompletion, completionhascriteria, completionusertracked
            - progress, completed, lastaccess, isfavourite, hidden
            - showgrades, showactivitydates, showcompletionconditions
            - overviewfiles: List of overview files (optional)
        """
        result = await self._call_function(
            "core_enrol_get_users_courses",
            userid=userid,
            returnusercount=returnusercount
        )

        if isinstance(result, list):
            return result
        return []

    # ============================================================================
    # Completion Calls
    # ============================================================================

    async def get_course_completion_status(self, courseid: int, userid: int) -> dict[str, Any]:
        """Get course completion status for a user.
        
        Returns the completion status of a user in a specific course, including all
        completion criteria and their individual completion states.

        Args:
            courseid: Course ID (required).
            userid: User ID (required).

        Returns:
            Dictionary containing:
            - completionstatus: Completion status object:
              * completed: 1 if course is complete, 0 otherwise
              * aggregation: Aggregation method (1=ALL criteria, 2=ANY criteria)
              * completions: List of completion criteria with their status
            - warnings: List of warning objects (optional)
        """
        result = await self._call_function(
            "core_completion_get_course_completion_status",
            courseid=courseid,
            userid=userid
        )

        if isinstance(result, dict):
            return result
        return {"completionstatus": {"completed": 0, "aggregation": 1, "completions": []}, "warnings": []}

    async def get_activities_completion_status(self, courseid: int, userid: int) -> dict[str, Any]:
        """Get activities completion status for a user in a course.
        
        Returns the completion status of all activities (modules) for a user in a specific
        course, including detailed information about each activity's state and tracking settings.
        
        WARNING: If the user is not enrolled in the course, Moodle does not return an error,
        but a list with all activities marked as incomplete (state=0).

        Args:
            courseid: Course ID (required).
            userid: User ID (required).

        Returns:
            Dictionary containing:
            - statuses: List of activity completion status objects with fields like:
              * cmid, modname, instance, state, timecompleted, tracking
              * hascompletion, isautomatic, istrackeduser, uservisible
              * details: List of completion rule details (optional)
            - warnings: List of warning objects (optional)
        """
        result = await self._call_function(
            "core_completion_get_activities_completion_status",
            courseid=courseid,
            userid=userid
        )

        if isinstance(result, dict):
            return result
        return {"statuses": [], "warnings": []}

    async def update_activity_completion_status_manually(
            self,
            cmid: int,
            completed: int
    ) -> dict[str, Any]:
        """Update activity completion status manually for the current user.
        
        Manually marks an activity as complete or incomplete for the current user.
        This only works for activities that have manual completion tracking enabled.

        Args:
            cmid: Course module ID (activity ID) (required).
            completed: Completion status to set (required):
                      - 1: Mark activity as complete
                      - 0: Mark activity as incomplete

        Returns:
            Dictionary containing:
            - status: 1 if operation was successful, 0 if failed
            - warnings: List of warning objects (optional) with details about failures
        """
        result = await self._call_function(
            "core_completion_update_activity_completion_status_manually",
            cmid=cmid,
            completed=completed
        )

        if isinstance(result, dict):
            return result
        return {"status": 0, "warnings": []}

    # ============================================================================
    # Grades Calls
    # ============================================================================

    async def update_grades(
        self,
        source: str,
        courseid: int,
        component: str,
        activityid: int,
        itemnumber: int,
        grades: list[StudentGrade] | None = None,
        itemdetails: GradeItemDetails | None = None
    ) -> int:
        """Update a grade item and associated student grades.
        
        Updates a grade item configuration and/or student grades for a specific activity
        in Moodle. Can update item settings, grades, or both simultaneously.

        Args:
            source: Source of the update (arbitrary identifier, e.g., 'my_script').
            courseid: Course ID (required).
            component: Component the activity belongs to (e.g., 'mod_quiz', 'mod_assign').
            activityid: ID of the activity instance (e.g., specific quiz ID).
            itemnumber: Grade item number for modules with multiple grades. Typically 0.
            grades: List of StudentGrade objects with student grades to update (optional).
                   Each grade must have studentid, grade, and optional str_feedback.
            itemdetails: GradeItemDetails object with grade item config to modify (optional).
                        Available settings: itemname, idnumber, gradetype, grademax, grademin,
                        scaleid, multfactor, plusfactor, deleted, hidden.

        Returns:
            Result code:
            - 0: GRADE_UPDATE_OK (Success)
            - 1: GRADE_UPDATE_FAILED (Failure)
        """
        params: dict[str, Any] = {
            "source": source,
            "courseid": courseid,
            "component": component,
            "activityid": activityid,
            "itemnumber": itemnumber
        }

        # Add grades if provided
        if grades:
            params["grades"] = [grade.to_moodle_dict() for grade in grades]
        else:
            params["grades"] = []

        # Add itemdetails if provided
        if itemdetails:
            params["itemdetails"] = itemdetails.to_moodle_dict()
        else:
            params["itemdetails"] = {}

        result = await self._call_function(
            "core_grades_update_grades",
            **params
        )

        # Result should be an integer (0 or 1)
        if isinstance(result, int):
            return result
        # If result is not an integer, consider it a failure
        return 1

    async def get_gradeitems(self, courseid: int) -> dict[str, Any]:
        """Get grade items for a course.
        
        Returns all grade items (grade elements) configured in a specific course.
        Grade items represent individual assessments, activities, or manual grade entries.

        Args:
            courseid: Course ID (required).

        Returns:
            Dictionary containing:
            - gradeItems: List of grade item objects with id, itemname, category (optional)
            - warnings: List of warning objects (optional)
        """
        result = await self._call_function(
            "core_grades_get_gradeitems",
            courseid=courseid
        )

        if isinstance(result, dict):
            return result
        return {"gradeItems": [], "warnings": []}

    async def get_grade_items_user_report(
            self,
            courseid: int,
            userid: int = 0,
            groupid: int = 0
    ) -> dict[str, Any]:
        """Get complete list of grade items and user grades in a course.
        
        Returns the full grade report as shown in the "User report" view in Moodle.
        This provides a comprehensive view of all grade items and user grades,
        including detailed information about each grade item and the user's performance.

        Args:
            courseid: Course ID (required).
            userid: User ID (optional). If specified (>0), returns grades only for this user.
                   If 0 (default), returns grades for all visible users.
            groupid: Group ID (optional). If specified (>0), gets users only from this group.
                    If 0 (default), includes all groups.

        Returns:
            Dictionary containing:
            - usergrades: List of user objects with their grades. Each contains:
              * courseid, userid, userfullname, useridnumber, maxdepth
              * gradeitems: List of grade item objects with user's grades including
                identification, configuration, user's grade, metadata, feedback, and statistics
            - warnings: List of warning objects (optional)
        """
        params: dict[str, Any] = {"courseid": courseid}

        if userid > 0:
            params["userid"] = userid
        if groupid > 0:
            params["groupid"] = groupid

        result = await self._call_function(
            "gradereport_user_get_grade_items",
            **params
        )

        if isinstance(result, dict):
            return result
        return {"usergrades": [], "warnings": []}

    async def get_grade_tree(self, courseid: int) -> dict[str, Any]:
        """Get hierarchical grade structure (tree) for a course.
        
        Returns the complete gradebook structure for a course as a dictionary.
        This includes the full hierarchy of grade categories, subcategories,
        grade items, their relationships, weights, and aggregation settings.

        Args:
            courseid: Course ID (required).

        Returns:
            Dictionary containing the complete gradebook structure:
            - children: List of grade categories and items
            - Grade categories and their hierarchy
            - Grade items within each category
            - Aggregation methods and weights
            - Grade scales and maximum/minimum values
            - Hidden/visible status of items
        """
        result = await self._call_function(
            "core_grades_get_grade_tree",
            courseid=courseid
        )

        # Parse JSON string if necessary (Moodle may return a JSON string)
        if isinstance(result, str):
            import json
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse grade tree JSON: {result[:100]}")
                return {}
        
        # Already a dict, return as-is
        if isinstance(result, dict):
            return result
        
        # Unexpected type, return empty dict
        return {}

    async def get_feedback(
        self,
        courseid: int,
        userid: int,
        itemid: int
    ) -> dict[str, Any]:
        """Get feedback data for a specific user's grade in a grade item.
        
        Returns the feedback (comment) associated with a specific student's
        grade for a particular grade item, along with related information.

        Args:
            courseid: Course ID (required).
            userid: User (student) ID (required).
            itemid: Specific grade item ID (required).

        Returns:
            Dictionary containing:
            - feedbacktext: Full feedback text (comment) for this grade
            - title: Title of the grade item
            - fullname: Full name of the student
            - picture: String representing student's image (likely URL or identifier)
            - additionalfield: Additional user field (email or ID number)
        """
        result = await self._call_function(
            "core_grades_get_feedback",
            courseid=courseid,
            userid=userid,
            itemid=itemid
        )

        if isinstance(result, dict):
            return result
        return {
            "feedbacktext": "",
            "title": "",
            "fullname": "",
            "picture": "",
            "additionalfield": ""
        }

    # ============================================================================
    # Webservice Calls
    # ============================================================================

    async def get_site_info(self) -> dict[str, Any]:
        """Get site information, current user details and available webservice functions.
        
        Retrieves comprehensive information about the Moodle site, the authenticated user,
        and the list of webservice functions available to the current user/token.
        This is useful for understanding the current user's capabilities, site configuration,
        and what operations are available through the webservice.
        
        NOTE: The Moodle API function accepts a deprecated parameter `serviceshortnames`
        which is ignored by the API. This parameter is not exposed in this method
        as it serves no purpose.

        Returns:
            Dictionary containing extensive site and user information:
            
            User Information:
            - userid, username, firstname, lastname, fullname, userpictureurl, lang
            - userissiteadmin, userhomepage, userhomepageurl (optional)
            
            Site Information:
            - sitename, siteurl, siteid, release, version (optional)
            - mobilecssurl, sitecalendartype, usercalendartype, theme (optional)
            
            Capabilities and Limits:
            - downloadfiles, uploadfiles, usercanmanageownfiles (optional)
            - userquota, usermaxuploadfilesize, limitconcurrentlogins (optional)
            - usersessionscount, policyagreed (optional)
            
            Webservice Functions:
            - functions: List of available webservice function objects with name and version
            
            Advanced Features:
            - advancedfeatures: List of site advanced features and their status (optional)
            
            Access:
            - userprivateaccesskey: User private access key for file retrieval (optional)
        """
        result = await self._call_function("core_webservice_get_site_info")

        if isinstance(result, dict):
            return result
        return {}