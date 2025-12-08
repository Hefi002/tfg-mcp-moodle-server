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
def sample_moodle_error():
    """Provide sample Moodle API error response.
    
    Returns mock error data matching Moodle's error response structure
    when an API call fails.
    
    Returns:
        Dictionary with Moodle error fields:
        - exception: Exception class name
        - message: Human-readable error message
        - errorcode: Moodle error code (optional)
    """
    return {
        "exception": "invalid_token_exception",
        "message": "Invalid token - token not found",
        "errorcode": "invalidtoken"
    }


@pytest.fixture
def sample_course_with_all_fields():
    """Provide a complete course object with all possible fields.
    
    Useful for testing field handling and data completeness.
    Based on Moodle's core_course_get_courses response.
    
    Returns:
        Dictionary with all standard Moodle course fields
    """
    return {
        "id": 1,
        "shortname": "ASW",
        "fullname": "Aplicacions i Serveis Web",
        "categoryid": 1,
        "categorysortorder": 10000,
        "summary": "Curs sobre aplicacions web modernes",
        "summaryformat": 1,
        "format": "topics",
        "showgrades": 1,
        "newsitems": 5,
        "startdate": 1704067200,
        "enddate": 1719792000,
        "numsections": 10,
        "maxbytes": 0,
        "showreports": 0,
        "visible": 1,
        "groupmode": 0,
        "groupmodeforce": 0,
        "defaultgroupingid": 0,
        "timecreated": 1704067200,
        "timemodified": 1704067200,
        "enablecompletion": 1,
        "completionnotify": 0,
        "lang": "ca",
        "theme": "",
    }
