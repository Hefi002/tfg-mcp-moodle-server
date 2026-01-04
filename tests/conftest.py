"""Shared test configuration and fixtures.

This module provides common fixtures used across unit and integration tests.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def test_env():
    """Configure test environment variables for test session.
    
    Sets up non-production Moodle credentials for testing with scope='session'
    so it's set once for all tests. Cleans up after session completes.
    
    Yields:
        None - environment variables are set in os.environ
    """
    # Store original values if they exist
    original_url = os.environ.get("MOODLE_URL")
    original_token = os.environ.get("MOODLE_TOKEN")
    
    # Set test values
    os.environ["MOODLE_URL"] = "http://localhost:8000"
    os.environ["MOODLE_TOKEN"] = "test_token_123"
    
    yield
    
    # Cleanup - restore original values or remove if didn't exist
    if original_url is not None:
        os.environ["MOODLE_URL"] = original_url
    else:
        os.environ.pop("MOODLE_URL", None)
        
    if original_token is not None:
        os.environ["MOODLE_TOKEN"] = original_token
    else:
        os.environ.pop("MOODLE_TOKEN", None)


@pytest.fixture
def sample_courses():
    """Provide sample course data for testing READ operations.
    
    Returns mock Moodle course data matching the structure returned by
    the core_course_get_courses API endpoint for use in tests.
    
    Returns:
        List of course dictionaries with standard Moodle fields
    """
    return [
        {
            "id": 1,
            "shortname": "ASW",
            "fullname": "Aplicacions i Serveis Web",
            "categoryid": 1,
            "visible": 1
        },
        {
            "id": 2,
            "shortname": "IES",
            "fullname": "Introducció a l'Enginyeria del Software",
            "categoryid": 2,
            "visible": 1
        }
    ]


@pytest.fixture
def sample_courses_to_create():
    """Provide sample course data for CREATE operations.
    
    Returns Course model instances for creating courses via
    core_course_create_courses API endpoint with minimal required fields.
    
    Returns:
        List with one Course instance containing fullname, shortname, and categoryid
    """
    from src.mcp.models import Course
    
    return [
        Course(
            fullname="Introduction to Programming",
            shortname="CS101",
            categoryid=1
        )
    ]


@pytest.fixture
def sample_courses_to_update():
    """Provide sample course data for UPDATE operations.
    
    Returns CourseUpdate model instances for updating courses via
    core_course_update_courses API endpoint with required id field
    and one field to update.
    
    Returns:
        List with one CourseUpdate instance containing id and fullname
    """
    from src.mcp.models import CourseUpdate
    
    return [
        CourseUpdate(
            id=1,
            fullname="Advanced Web Development"
        )
    ]


@pytest.fixture
def sample_moodle_invalid_parameter_error():
    """Provide sample Moodle invalid parameter error response.
    
    Returns mock error data matching Moodle's error response structure
    when an API call has invalid parameters.
    
    Returns:
        Dictionary with exception and message fields
    """
    return {
        "exception": "invalid_parameter_exception",
        "message": "Invalid parameter value detected"
    }


@pytest.fixture
def sample_moodle_invalid_token_error():
    """Provide sample Moodle invalid token error response.
    
    Returns mock error data matching Moodle's error response structure
    when authentication token is invalid or not found.
    
    Returns:
        Dictionary with exception, message, and errorcode fields
    """
    return {
        "exception": "invalid_token_exception",
        "message": "Invalid token or token not found",
        "errorcode": "invalidtoken"
    }


@pytest.fixture
def sample_moodle_access_error():
    """Provide sample Moodle access/permission error response.
    
    Returns mock error data matching Moodle's error response structure
    when user lacks required permissions or capabilities.
    
    Returns:
        Dictionary with exception, message, and errorcode fields
    """
    return {
        "exception": "required_capability_exception",
        "message": "Sorry, but you do not currently have permissions to do that (View course information)",
        "errorcode": "nopermissions"
    }


@pytest.fixture
def moodle_client():
    """Create MoodleClient instance for testing.
    
    Returns:
        MoodleClient configured with test credentials
    """
    from src.mcp.protocol import MoodleClient
    
    return MoodleClient(
        base_url="http://localhost:8000",
        token="test_token_123"
    )


@pytest.fixture
def mock_http_response(sample_courses):
    """Create a mock HTTP response for httpx.AsyncClient.post.
    
    Args:
        sample_courses: Fixture providing sample course data
    
    Returns:
        Mock response configured with sample course data
    """
    mock = MagicMock()
    mock.json.return_value = sample_courses
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_context():
    """Create a mocked Context with real MoodleClient in lifespan.
    
    This fixture creates a MoodleClient instance but will be used
    with mocked HTTP calls. The Context itself is mocked to simulate
    the AI agent side.
    
    Returns:
        Mock Context with request_context.lifespan_context set to real MoodleClient
    """
    from mcp.server.fastmcp import Context
    from src.mcp.protocol import MoodleClient
    
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.request_context = MagicMock()
    
    # Create MoodleClient (will use mocked HTTP in tests)
    real_client = MoodleClient(
        base_url="http://localhost:8000",
        token="test_token_123"
    )
    mock_ctx.request_context.lifespan_context = real_client
    
    # Mock the logging methods (AI agent side)
    mock_ctx.info = AsyncMock()
    mock_ctx.error = AsyncMock()
    
    return mock_ctx
