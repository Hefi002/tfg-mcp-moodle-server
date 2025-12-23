"""Shared test configuration and fixtures.

This module provides common fixtures used across unit and integration tests.
"""
import pytest
import os


@pytest.fixture(scope="session")
def test_env():
    """Configure test environment variables.
    
    Sets up non-production Moodle credentials for testing.
    Scope is 'session' so it's set once for all tests.
    
    Yields:
        None - environment variables are set in os.environ
        
    Cleanup:
        Removes test environment variables after session completes
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
    """Provide sample course data for testing.
    
    Returns mock Moodle course data matching the structure returned by
    the core_course_get_courses API endpoint.
    
    Returns:
        List of course dictionaries with standard Moodle fields:
        - id: Course ID
        - shortname: Short course name (e.g., "ASW")
        - fullname: Full course name
        - categoryid: Category ID
        - visible: Visibility flag (1=visible, 0=hidden)
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
    """Provide sample course data for creation operations.
    
    Returns Course model instances for creating courses via
    core_course_create_courses API endpoint.
    
    Returns:
        List with one Course instance containing minimal required fields:
        - fullname: Full course name
        - shortname: Short course code
        - categoryid: Category ID where course will be created
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
    """Provide sample course data for update operations.
    
    Returns CourseUpdate model instances for updating courses via
    core_course_update_courses API endpoint.
    
    Returns:
        List with one CourseUpdate instance containing:
        - id: Course ID to update
        - fullname: New full course name
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
        Dictionary with Moodle error fields:
        - exception: invalid_parameter_exception
        - message: Human-readable error message
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
        Dictionary with Moodle error fields:
        - exception: invalid_token_exception
        - message: Human-readable error message
        - errorcode: Moodle error code
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
        Dictionary with Moodle error fields:
        - exception: required_capability_exception
        - message: Human-readable error message
        - errorcode: Moodle error code
    """
    return {
        "exception": "required_capability_exception",
        "message": "Sorry, but you do not currently have permissions to do that (View course information)",
        "errorcode": "nopermissions"
    }
