"""Moodle API client implementation."""
import httpx
from typing import Any
from .utils.logger import get_logger
from .models import Course, CourseUpdate, CourseContentsOption

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
            if not isinstance(data, (dict, list)):
                logger.error(f"Unexpected response type: {type(data).__name__}")
                raise ValueError(f"Moodle API returned unexpected type: {type(data).__name__}")
            # Check for Moodle API error
            elif "exception" in data:
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
        """Obtener la lista de cursos a los que un usuario ha accedido, ordenados por fecha de acceso,
        de más reciente a más antiguo.

        Llama a la función web service `core_course_get_recent_courses`.

        Argumentos:
            userid (Opcional): ID del usuario. Si es 0 (por defecto) o se omite, se usa
                el usuario que realiza la solicitud.
            limit (Opcional): Límite del número de resultados. 0 devuelve todos los cursos.
            offset (Opcional): Desplazamiento (offset) para paginación.
            sort (Opcional): Cadena para ordenar los resultados (ej., "fullname", "shortname").

        Retorna:
            Lista de diccionarios de cursos. Si la respuesta no es una lista, devuelve []
        """
        params: dict[str, Any] = {}

        # Sólo se añaden los parámetros si son diferentes de sus valores por defecto
        # para evitar enviar valores innecesarios a la API.
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