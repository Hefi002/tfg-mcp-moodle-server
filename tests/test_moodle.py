"""Unit tests for MoodleClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.mcp.protocol import MoodleClient
import httpx


@pytest.fixture
def moodle_client():
    """Create MoodleClient instance for testing.
    
    Returns:
        MoodleClient configured with test credentials
    """
    return MoodleClient(
        base_url="http://localhost:8000",
        token="test_token_123"
    )


def test_moodle_client_initialization(moodle_client):
    """Verify client initializes with correct configuration.
    
    Validates:
    - Base URL is properly cleaned
    - Token is stored
    - API endpoint is constructed correctly
    """
    assert moodle_client.base_url == "http://localhost:8000"
    assert moodle_client.token == "test_token_123"
    assert moodle_client.api_endpoint == "http://localhost:8000/webservice/rest/server.php"
    assert moodle_client.client is not None


def test_base_url_trailing_slash():
    """Verify trailing slash(slash at the end of url) is removed from base URL."""
    client = MoodleClient(
        base_url="http://localhost:8000/",
        token="test_token"
    )
    assert client.base_url == "http://localhost:8000"
    assert not client.base_url.endswith("/")


@pytest.mark.asyncio
async def test_call_function_success(moodle_client, sample_courses):
    """Test successful API call with correct parameters.
    
    Validates:
    - HTTP POST is made to correct endpoint
    - Request includes wstoken, wsfunction, and format parameters
    - Response data is returned correctly
    """
    mock_response = MagicMock()
    mock_response.json.return_value = sample_courses
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await moodle_client._call_function("core_course_get_courses")
        
        # Verify HTTP call
        assert mock_post.called
        
        # Verify request parameters
        call_args = mock_post.call_args
        assert call_args[0][0] == moodle_client.api_endpoint
        assert call_args[1]['data']['wsfunction'] == "core_course_get_courses"
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        assert call_args[1]['data']['moodlewsrestformat'] == "json"
        
        # Verify result
        assert result == sample_courses


# TODO: Uncomment when implementing functions that require parameters (e.g., get_course_contents)
# @pytest.mark.asyncio
# async def test_call_function_with_parameters(moodle_client):
#     """Test internal API call with additional parameters.
#     
#     Verifies that _call_function properly passes extra kwargs to Moodle API.
#     This tests the internal method used by all public methods.
#     """
#     mock_response = MagicMock()
#     mock_response.json.return_value = {"id": 1, "name": "Test"}
#     mock_response.raise_for_status = MagicMock()
#     
#     with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
#         mock_post.return_value = mock_response
#         
#         result = await moodle_client._call_function(
#             "core_course_get_contents",
#             courseid=1
#         )
#         
#         # Verify additional parameters
#         call_args = mock_post.call_args
#         assert call_args[1]['data']['courseid'] == 1


@pytest.mark.asyncio
async def test_call_function_moodle_error(moodle_client):
    """Test handling of Moodle API errors.
    
    Verifies that:
    - Moodle exception responses are detected
    - ValueError is raised with appropriate message
    """
    mock_error_response = {
        "exception": "invalid_token_exception",
        "message": "Invalid token - token not found"
    }
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_error_response
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Invalid token"):
            await moodle_client._call_function("core_course_get_courses")


@pytest.mark.asyncio
async def test_call_function_http_error(moodle_client):
    """Test handling of HTTP errors (network failures, 500s, etc.)."""
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection error")
        
        with pytest.raises(httpx.HTTPError):
            await moodle_client._call_function("core_course_get_courses")


@pytest.mark.asyncio
async def test_get_courses(moodle_client, sample_courses):
    """Test get_courses method.
    
    Validates:
    - Calls correct Moodle function
    - Returns list of courses
    - Data structure matches expected format
    """
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_courses
        
        result = await moodle_client.get_courses()
        
        # Verify correct function called
        mock_call.assert_called_once_with("core_course_get_courses")
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["shortname"] == "ASW"


@pytest.mark.asyncio
async def test_get_courses_empty(moodle_client):
    """Test get_courses with empty response.
    
    Verifies method returns empty list rather than None or raising error.
    """
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = []
        
        result = await moodle_client.get_courses()
        
        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_get_courses_non_list_response(moodle_client):
    """Test get_courses with unexpected response type.
    
    Verifies robustness when API returns dict instead of expected list.
    """
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"error": "some error"}
        
        result = await moodle_client.get_courses()
        
        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_client_close(moodle_client):
    """Verify client closes HTTP connection properly."""
    with patch.object(moodle_client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await moodle_client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_calls(moodle_client, sample_courses):
    """Test multiple consecutive API calls.
    
    Verifies:
    - Client maintains state between calls
    - No side effects between calls
    - Results are consistent
    """
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_courses
        
        result1 = await moodle_client.get_courses()
        result2 = await moodle_client.get_courses()
        
        assert result1 == result2
        assert mock_call.call_count == 2
