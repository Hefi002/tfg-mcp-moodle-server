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

# ============================================================================
# GENERAL TESTS
# ============================================================================

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
    """Verify trailing slash is removed from base URL."""
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


@pytest.mark.asyncio
async def test_call_function_with_parameters(moodle_client):
    """Test internal API call with additional parameters.
    
    Verifies that _call_function properly passes extra kwargs to Moodle API.
    httpx handles the serialization of complex structures (lists, dicts) automatically.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": 100, "shortname": "MATH101"}]
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        courses_param = [{"fullname": "Mathematics 101", "shortname": "MATH101", "categoryid": 1}]
        result = await moodle_client._call_function(
            "core_course_create_courses",
            courses=courses_param
        )
        
        # Verify the function was called
        assert mock_post.called
        
        # Verify the data dict contains our parameter with exact value
        call_args = mock_post.call_args
        assert call_args[1]['data']['courses'] == courses_param
        
        # Verify standard parameters are also present
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        assert call_args[1]['data']['wsfunction'] == "core_course_create_courses"
        assert call_args[1]['data']['moodlewsrestformat'] == "json"
        
        # Verify result
        assert result == [{"id": 100, "shortname": "MATH101"}]


@pytest.mark.asyncio
async def test_call_function_unexpected_type(moodle_client):
    """Test _call_function handles completely unexpected response types.
    
    If Moodle API returns something unexpected (string, null, number),
    _call_function should raise ValueError.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = "unexpected string"
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="unexpected type"):
            await moodle_client._call_function("core_course_get_courses")

#TODO: should i move this test to integration?
@pytest.mark.asyncio
async def test_call_function_moodle_error(moodle_client):
    """Test handling of Moodle API errors.
    
    All MOODLE API errors return a JSON with "exception" field.
    All MOODLE API errors return an invalid parameter exception.
    """
    mock_error_response = {
        "exception": "invalid_parameter_exception",
        "message": "Invalid parameter value detected"
    }
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_error_response
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Invalid parameter"):
            await moodle_client._call_function("core_course_get_courses")


@pytest.mark.asyncio
async def test_call_function_http_error(moodle_client):
    """Test handling of HTTP errors.
    
    This covers ALL HTTP/network errors: connection failures, timeouts,
    500 errors, etc.
    """
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection error")
        
        with pytest.raises(httpx.HTTPError):
            await moodle_client._call_function("core_course_get_courses")


@pytest.mark.asyncio
async def test_client_close(moodle_client):
    """Verify client closes HTTP connection properly."""
    with patch.object(moodle_client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await moodle_client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_calls(moodle_client, sample_courses):
    """Test multiple consecutive API calls. Tests idempotency.

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


# ============================================================================
# core_course Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_courses_with_ids(moodle_client, sample_courses):
    """Test get_courses method with specific course IDs.
    
    Validates:
    - Calls correct Moodle function with options parameter
    - Passes courseids correctly in options[ids] format
    - Returns list of courses
    - Data structure matches expected format
    """
    courseids = [1, 2]
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_courses
        
        result = await moodle_client.get_courses(courseids=courseids)
        
        # Verify correct function called with options parameter
        mock_call.assert_called_once_with(
            "core_course_get_courses",
            options={"ids": courseids}
        )
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["shortname"] == "ASW"


@pytest.mark.asyncio
async def test_create_courses_minimal_fields(moodle_client):
    """Test create_courses method with minimum required fields.
    
    Tests the base case with only required fields:
    - fullname: Full course name
    - shortname: Short course code
    - categoryid: Category ID
    
    Validates:
    - Calls correct Moodle function
    - Passes courses parameter correctly
    - Returns list of created courses with assigned IDs
    """
    courses_to_create = [
        {
            "fullname": "Introduction to Programming",
            "shortname": "CS101",
            "categoryid": 1
        }
    ]
    
    created_courses = [
        {
            "id": 100,
            "shortname": "CS101"
        }
    ]
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = created_courses
        
        result = await moodle_client.create_courses(courses_to_create)
        
        # Verify correct function called with parameters
        mock_call.assert_called_once_with(
            "core_course_create_courses",
            courses=courses_to_create
        )
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["shortname"] == "CS101"


@pytest.mark.asyncio
async def test_update_courses_minimal_fields(moodle_client):
    """Test update_courses method with minimum required fields.
    
    Tests the base case with only required field:
    - id: Course ID to update
    
    Plus one field to update (in this case fullname).
    
    Validates:
    - Calls correct Moodle function
    - Passes courses parameter correctly
    - Returns result dictionary with warnings array
    """
    courses_to_update = [
        {
            "id": 1,
            "fullname": "Advanced Web Development"
        }
    ]
    
    update_result = {"warnings": []}
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = update_result
        
        result = await moodle_client.update_courses(courses_to_update)
        
        # Verify correct function called with parameters
        mock_call.assert_called_once_with(
            "core_course_update_courses",
            courses=courses_to_update
        )
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "warnings" in result
        assert result["warnings"] == []


@pytest.mark.asyncio
async def test_delete_courses_single_id(moodle_client):
    """Test delete_courses method with single course ID.
    
    Tests the base case deleting one course.
    
    Validates:
    - Calls correct Moodle function
    - Passes courseids parameter correctly
    - Returns result dictionary with warnings array
    """
    courseids_to_delete = [42]
    delete_result = {"warnings": []}
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = delete_result
        
        result = await moodle_client.delete_courses(courseids_to_delete)
        
        # Verify correct function called with parameters
        mock_call.assert_called_once_with(
            "core_course_delete_courses",
            courseids=courseids_to_delete
        )
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "warnings" in result
        assert result["warnings"] == []
