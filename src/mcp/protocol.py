"""Moodle API client implementation."""
import httpx
from typing import Any
from .utils.logger import get_logger

logger = get_logger(__name__)


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

        try:
            response = await self.client.post(
                self.api_endpoint,
                data=request_params
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

    async def create_courses(self, courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create one or more courses in Moodle.

        Args:
            courses: List of course dictionaries with at least:
                - fullname: Full course name
                - shortname: Short course name
                - categoryid: Category ID

        Returns:
            List of created course dictionaries with id
        """
        result = await self._call_function(
            "core_course_create_courses",
            courses=courses
        )
        if isinstance(result, list):
            return result
        return []

    async def update_courses(self, courses: list[dict[str, Any]]) -> dict[str, Any]:
        """Update one or more courses in Moodle.

        Args:
            courses: List of course dictionaries with at least:
                - id: Course ID
                - And any fields to update (fullname, shortname, etc.)

        Returns:
            Result dictionary (usually contains warnings if any)
        """
        result = await self._call_function(
            "core_course_update_courses",
            courses=courses
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

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()