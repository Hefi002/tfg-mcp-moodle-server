"""Moodle API client implementation."""
import httpx
from typing import Any
from .utils.logger import get_logger
from .models import Course, CourseUpdate, CourseContentsOption, EnrolledUsersOption, ManualEnrolment, ManualUnenrolment, UserCreate, UserSearchCriteria, GradeItemDetails, StudentGrade

logger = get_logger(__name__)


def flatten_params(params: dict[str, Any], parent_key: str = '') -> dict[str, Any]:
    """Flatten nested dictionary/list structures to Moodle API format.
    
    Converts nested structures like:
        {"courses": [{"fullname": "Test", "categoryid": 1}]}
    
    To Moodle's expected format:
        {"courses[0][fullname]": "Test", "courses[0][categoryid]": 1}
    
    Args:
        params: Dictionary potentially containing nested dicts/lists
        parent_key: Key prefix for recursion (used internally)
    
    Returns:
        Flattened dictionary with Moodle-formatted keys
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
    """Client for interacting with Moodle Web Services API."""

    def __init__(self, base_url: str, token: str):
        """Initialize Moodle client.

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
        """Call a Moodle web service function (private use only).
        Manages most error handling from api calls.

        Args:
            function_name: Name of the Moodle web service function
            **params: Function parameters as keyword arguments

        Returns:
            Response data from Moodle API

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If Moodle returns an error
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

    async def get_courses(self, courseids: list[int] | None = None) -> list[dict[str, Any]]:
        """Get courses from Moodle.

        Args:
            courseids: Optional list of course IDs to retrieve specific courses.
                      If None or empty, returns all courses.

        Returns:
            List of course dictionaries
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

        Args:
            courses: List of Course objects to create

        Returns:
            List of created course dictionaries with their assigned IDs
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

        Args:
            courses: List of CourseUpdate objects with course ID and fields to update

        Returns:
            Result dictionary (usually contains warnings if any)
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

    async def manual_unenrol_users(self, enrolments: list[ManualUnenrolment]) -> dict[str, Any]:
        """Manually unenrol users from courses.

        Calls Moodle webservice function `enrol_manual_unenrol_users`.
        Removes user enrolments from courses. Can remove specific roles or
        completely unenrol the user by removing all roles.

        Args:
            enrolments: List of ManualUnenrolment objects. Each unenrolment must have:
                       Required fields:
                       - userid: User ID to unenrol
                       - courseid: Course ID from which to unenrol the user
                       
                       Optional field:
                       - roleid: Specific role ID to remove. If not specified,
                                all roles will be removed (complete unenrolment)

        Returns:
            Result dictionary. An empty result ({}) indicates success.
            On error, raises an exception (e.g., invalid_parameter_exception).
            
        Examples:
            # Completely unenrol user 5 from course 10 (remove all roles)
            unenrolments = [ManualUnenrolment(userid=5, courseid=10)]
            
            # Remove only specific role (e.g., student role 5) for user 5 in course 10
            unenrolments = [ManualUnenrolment(userid=5, courseid=10, roleid=5)]
            
            # Unenrol multiple users
            unenrolments = [
                ManualUnenrolment(userid=5, courseid=10),
                ManualUnenrolment(userid=6, courseid=10)
            ]
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

    async def delete_courses(self, courseids: list[int]) -> dict[str, Any]:
        """Delete one or more courses from Moodle.

        Args:
            courseids: List of course IDs to delete

        Returns:
            Result dictionary (usually contains warnings if any)
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
        """Get course contents (sections and modules).

        Args:
            courseid: Course ID to get contents from
            options: Optional CourseContentsOption object to filter results.
                    Available filters:
                    - excludemodules: Do not return modules, return only sections
                    - excludecontents: Do not return module contents (files)
                    - includestealthmodules: Return stealth modules for students
                    - sectionid: Return only this section
                    - sectionnumber: Return only this section with number
                    - cmid: Return only this module information
                    - modname: Return only modules with this name
                    - modid: Return only the module with this id

        Returns:
            List of section dictionaries containing course structure and modules
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
        """Notify Moodle that a course/section was viewed (core_course_view_course).

        Calls the Moodle web service function `core_course_view_course` to inform
        Moodle that a course (or a specific section) has been viewed. This is
        primarily used to log the view action on the Moodle side. The method
        returns the raw Moodle response, which typically contains a `status`
        field and optionally a list of `warnings`.

        Args:
            courseid: ID of the course to view (required).
            sectionnumber: Section number to view within the course (defaults to 0).

        Returns:
            A dictionary with the Moodle response. Expected keys:
            - `status` (int/bool): operation success indicator
            - `warnings` (optional list): any warnings generated by the call
            If the API returns an unexpected type, an empty dict is returned.
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
        """Get the list of courses a user has accessed by recency (recent first).

        Calls the `core_course_get_recent_courses` web service function.

        Arguments:
            userid (Optional): User ID. If 0 (default) or omitted, the current
                authenticated user is used.
            limit (Optional): Limit the number of results. 0 (default) returns
                all available courses.
            offset (Optional): Offset for courses.
            sort (Optional): Sort key (e.g. "fullname", "shortname").

        Returns:
            A list of course dictionaries. Returns an empty list if the response
            is not a list.
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
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_course_enrolment_methods(self, courseid: int) -> list[dict[str, Any]]:
        """Get enrolment methods available for a given course.

        Calls Moodle webservice function `core_enrol_get_course_enrolment_methods`.

        Args:
            courseid: ID del curso para el que se solicitan los métodos de matriculación.

        Returns:
            Lista de objetos con la información de las instancias de enrol (o lista vacía).
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

        Calls Moodle webservice function `core_enrol_get_enrolled_users`.

        Args:
            courseid: Course ID (required).
            options: Optional EnrolledUsersOption object to filter results.
                    Available filters:
                    - withcapability: Return only users with this capability
                    - groupid: Return only users in this group
                    - onlyactive: 1 to return only users with active enrolments
                    - onlysuspended: 1 to return only suspended users
                    - userfields: Comma-separated list of user fields to return
                    - limitfrom: SQL offset for pagination
                    - limitnumber: Maximum number of users to return
                    - sortby: Field to sort by (id, firstname, lastname, siteorder)
                    - sortdirection: Sort direction (ASC or DESC)

        Returns:
            List of enrolled user dictionaries. Each user object contains:
            - id: User ID
            - fullname: Full name
            - username, firstname, lastname, email (if requested)
            - profileimageurl, profileimageurlsmall (if available)
            - customfields: List of custom profile fields
            - groups: List of course groups the user belongs to
            - roles: List of user roles in this course
            - And other optional fields depending on userfields parameter
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

        Calls Moodle webservice function `enrol_manual_enrol_users`.

        Args:
            enrolments: List of ManualEnrolment objects. Each enrolment must have:
                       Required fields:
                       - roleid: Role ID to assign to the user
                       - userid: User ID to enrol
                       - courseid: Course ID in which to enrol the user
                       
                       Optional fields:
                       - timestart: Enrolment start timestamp (0 = immediate/default)
                       - timeend: Enrolment end timestamp (0 = no restriction)
                       - suspend: 1 to create suspended enrolment, 0 for active

        Returns:
            Result dictionary. An empty result indicates success.
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

    async def create_users(self, users: list[UserCreate]) -> list[dict[str, Any]]:
        """Create one or more users in Moodle.

        Calls Moodle webservice function `core_user_create_users`.

        Args:
            users: List of UserCreate objects. Each user must have:
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
                  - idnumber: Arbitrary ID code
                  - lang: Language code (default: 'en')
                  - calendartype: Calendar type (default: 'gregorian')
                  - city, country, timezone: Location fields
                  - maildisplay, mailformat: Email settings
                  - description: Profile description
                  - institution, department: Organizational fields
                  - phone1, phone2, address: Contact fields
                  - theme: Theme name
                  - customfields: List of custom profile fields
                  - preferences: List of user preferences

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

        Calls Moodle webservice function `core_user_get_users`.

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
                     
                     Notes:
                     - Each key must be unique
                     - Search uses AND operator between valid criteria
                     - Invalid criteria are ignored
                     - Empty criteria not recommended (can be very slow)

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
              * profileimageurl, profileimageurlsmall: Profile images
              * customfields: List of custom fields (optional)
              * preferences: List of preferences (optional)
              * And other optional fields (phone1, phone2, lang, timezone, etc.)
            - warnings: List of warning objects (optional)
              * item, itemid, warningcode, message
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

        Calls Moodle webservice function `core_enrol_get_users_courses`.

        Args:
            userid: User ID (required).
            returnusercount: Include enrolled user count in each course.
                            1 (default) to include count.
                            0 to omit and improve performance (especially for users
                            enrolled in many large courses).

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
            - startdate, enddate: Course dates (timestamps) (optional)
            - timemodified: Last modification timestamp (optional)
            - enablecompletion: 1 if completion tracking enabled (optional)
            - completionhascriteria: 1 if completion criteria set (optional)
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
        """
        result = await self._call_function(
            "core_enrol_get_users_courses",
            userid=userid,
            returnusercount=returnusercount
        )

        if isinstance(result, list):
            return result
        return []

    async def get_course_completion_status(self, courseid: int, userid: int) -> dict[str, Any]:
        """Get course completion status for a user.

        Calls Moodle webservice function `core_completion_get_course_completion_status`.

        Args:
            courseid: Course ID (required).
            userid: User ID (required).

        Returns:
            Dictionary containing:
            - completionstatus: Completion status object:
              * completed: 1 if course is complete, 0 otherwise
              * aggregation: Aggregation method (1=ALL criteria, 2=ANY criteria)
              * completions: List of completion criteria objects:
                - type: Criterion type code (numeric)
                - title: Criterion title
                - status: Status as readable text (e.g., "Yes", "No", "50%")
                - complete: 1 if complete, 0 if not
                - timecompleted: Timestamp when completed (0 if not complete)
                - details: Additional details object:
                  * type: Criterion type description
                  * criteria: Specific criterion description
                  * requirement: Requirement description
                  * status: Extended status description
            - warnings: List of warning objects (optional):
              * item, itemid, warningcode, message
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

        Calls Moodle webservice function `core_completion_get_activities_completion_status`.

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
        """
        result = await self._call_function(
            "core_completion_get_activities_completion_status",
            courseid=courseid,
            userid=userid
        )

        if isinstance(result, dict):
            return result
        return {"statuses": [], "warnings": []}

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

        Calls Moodle webservice function `core_grades_update_grades`.

        Args:
            source: Source of the update (arbitrary identifier from calling component, e.g., 'my_script').
            courseid: Course ID (required).
            component: Component the activity belongs to (e.g., 'mod_quiz', 'mod_assign').
            activityid: ID of the activity instance (e.g., specific quiz ID).
            itemnumber: Grade item number for modules with multiple grades. Typically 0.
            grades: List of StudentGrade objects with student grades to update/set (optional).
                   Each grade must have:
                   - studentid: Student ID
                   - grade: Numeric grade (for scale items, must be scale option ID)
                   - str_feedback: Feedback comment in plain text (optional)
            itemdetails: GradeItemDetails object with grade item configuration to modify (optional).
                        Available settings:
                        - itemname: Name of the grade item
                        - idnumber: Arbitrary identification number
                        - gradetype: Grade type (0=None, 1=Value, 2=Scale, 3=Text)
                        - grademax: Maximum grade allowed
                        - grademin: Minimum grade allowed
                        - scaleid: ID of custom scale (only if gradetype=2)
                        - multfactor: Multiply all grades by this number
                        - plusfactor: Add this value to all grades
                        - deleted: Set to 1 to mark item as deleted
                        - hidden: Set to 1 to hide the item

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

        Calls Moodle webservice function `core_grades_get_gradeitems`. For more extensive
        info on each grade_item, consider using

        Args:
            courseid: Course ID (required).

        Returns:
            Dictionary containing:
            - gradeItems: List of grade item objects:
              * id: Unique identifier string (not numeric DB ID, e.g., "mod_quiz_1234_0")
              * itemname: Full name of the grade item
              * category: Name of the grade category the item belongs to (optional)
            - warnings: List of warning objects (optional):
              * item, itemid, warningcode, message
        """
        result = await self._call_function(
            "core_grades_get_gradeitems",
            courseid=courseid
        )

        if isinstance(result, dict):
            return result
        return {"gradeItems": [], "warnings": []}

    async def get_grade_tree(self, courseid: int) -> dict[str, Any]:
        """Get hierarchical grade structure (tree) for a course.

        Calls Moodle webservice function `core_grades_get_grade_tree`.
        Returns the complete gradebook structure for a course as a dictionary.

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
            - And other gradebook configuration details
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

        Calls Moodle webservice function `core_grades_get_feedback`.

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

    async def get_grade_items_user_report(
            self,
            courseid: int,
            userid: int = 0,
            groupid: int = 0
    ) -> dict[str, Any]:
        """Get complete list of grade items and user grades in a course.

        Calls Moodle webservice function `gradereport_user_get_grade_items`.
        Returns the full grade report as shown in the "User report" view.

        Args:
            courseid: Course ID (required).
            userid: User ID (optional). If specified (>0), returns grades only for this user.
                   If 0 (default), returns grades for all visible users.
            groupid: Group ID (optional). If specified (>0), gets users only from this group.
                    If 0 (default), includes all groups.

        Returns:
            Dictionary containing:
            - usergrades: List of user objects with their grades:
              * courseid: Course ID
              * courseidnumber: Course ID number
              * userid: User ID
              * userfullname: User full name
              * useridnumber: User ID number
              * maxdepth: Maximum depth of grade category hierarchy
              * gradeitems: List of grade item objects with user's grades:
                - Identification:
                  * id: Grade item ID
                  * itemname: Item name
                  * itemtype: Type (e.g., 'mod', 'category', 'course')
                  * itemmodule: Module if activity (e.g., 'quiz', 'assign')
                  * iteminstance: Activity instance ID
                  * itemnumber: Item number (typically 0)
                  * idnumber: Item identification number
                  * categoryid: Grade category ID
                  * cmid: Course module ID (if itemtype is 'mod') (optional)
                - Configuration:
                  * scaleid: Scale ID used
                  * outcomeid: Outcome ID if applicable
                  * weightraw: Raw weight (optional)
                  * weightformatted: Formatted weight (optional)
                  * grademin: Minimum possible grade (optional)
                  * grademax: Maximum possible grade (optional)
                  * locked: 1 if item is locked for user (optional)
                - User's Grade:
                  * graderaw: Raw grade (numeric value) (optional)
                  * gradeformatted: Formatted grade for display (optional)
                  * percentageformatted: Formatted percentage (optional)
                  * lettergradeformatted: Formatted letter grade (optional)
                  * rangeformatted: Formatted grade range (optional)
                  * rank: User's rank in course for this item (optional)
                - Grade Metadata:
                  * status: Status (e.g., 'novalue', 'loaded') (optional)
                  * gradedatesubmitted: Submission date timestamp (optional)
                  * gradedategraded: Grading date timestamp (optional)
                  * gradehiddenbydate: 1 if hidden by date (optional)
                  * gradeishidden: 1 if grade is hidden (optional)
                  * gradeislocked: 1 if grade is locked (optional)
                  * gradeisoverridden: 1 if grade was overridden (optional)
                  * gradeneedsupdate: 1 if grade needs update (optional)
                - Feedback:
                  * feedback: Feedback comments (optional)
                  * feedbackformat: Format (1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN) (optional)
                - Statistics:
                  * numusers: Number of users in course (optional)
                  * averageformatted: Formatted item average (optional)
            - warnings: List of warning objects (optional):
              * item, itemid, warningcode, message
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

    async def update_activity_completion_status_manually(
        self,
        cmid: int,
        completed: int
    ) -> dict[str, Any]:
        """Update activity completion status manually for the current user.

        Calls Moodle webservice function `core_completion_update_activity_completion_status_manually`.
        Only works for activities with manual completion tracking enabled.

        Args:
            cmid: Course module ID (activity ID) (required).
            completed: Completion status to set (required):
                      - 1: Mark activity as complete
                      - 0: Mark activity as incomplete

        Returns:
            Dictionary containing:
            - status: 1 if operation was successful, 0 if failed
            - warnings: List of warning objects (optional):
              * item: Item identifier (e.g., 'cmid')
              * itemid: Item ID value
              * warningcode: Warning code identifier
              * message: Human-readable warning message
              
              Common warnings:
              - Activity does not have manual completion tracking enabled
              - User does not have permission to update completion
              - Activity or course module does not exist
        """
        result = await self._call_function(
            "core_completion_update_activity_completion_status_manually",
            cmid=cmid,
            completed=completed
        )

        if isinstance(result, dict):
            return result
        return {"status": 0, "warnings": []}

    async def get_site_info(self) -> dict[str, Any]:
        """Get site information, current user details and available webservice functions.

        Calls Moodle webservice function `core_webservice_get_site_info`.
        Returns comprehensive information about the Moodle site, the authenticated user,
        and the list of webservice functions available to this user.

        Note:
            The Moodle API function accepts a deprecated parameter `serviceshortnames`
            which is ignored by the API. This parameter is not exposed in this method
            as it serves no purpose.

        Returns:
            Dictionary containing extensive site and user information:
            
            User Information:
            - userid: Current user ID
            - username: Username
            - firstname: First name
            - lastname: Last name
            - fullname: Full name
            - userpictureurl: Public profile picture URL
            - lang: Current user language
            - userissiteadmin: 1 if user is site admin (optional)
            - userhomepage: Default homepage (0=Site, 1=Dashboard, 4=Custom) (optional)
            - userhomepageurl: Custom homepage URL if userhomepage is 4 (optional)
            
            Site Information:
            - sitename: Site name
            - siteurl: Site URL
            - siteid: Site course ID (optional)
            - release: Moodle release number (e.g., "4.4.1") (optional)
            - version: Moodle version (optional)
            - mobilecssurl: Mobile custom CSS URL (optional)
            - sitecalendartype: Site calendar type (optional)
            - usercalendartype: User calendar type (optional)
            - theme: Current theme for user (optional)
            
            Capabilities and Limits:
            - downloadfiles: 1 if user can download files (optional)
            - uploadfiles: 1 if user can upload files (optional)
            - usercanmanageownfiles: 1 if user can manage own files (optional)
            - userquota: User storage quota in bytes (0 = unlimited) (optional)
            - usermaxuploadfilesize: Max upload size in bytes (-1 = unlimited) (optional)
            - limitconcurrentlogins: Number of concurrent sessions allowed (optional)
            - usersessionscount: Number of active user sessions (optional)
            - policyagreed: 1 if user agreed to all policies (optional)
            
            Webservice Functions:
            - functions: List of available webservice function objects:
              * name: Function name
              * version: Component version
            
            Advanced Features:
            - advancedfeatures: List of site advanced features status (optional):
              * name: Feature name
              * value: Usually 1 for enabled
            
            Access:
            - userprivateaccesskey: User private access key for file retrieval (optional)
        """
        result = await self._call_function("core_webservice_get_site_info")

        if isinstance(result, dict):
            return result
        return {}
