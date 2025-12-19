"""MCP server integration tests.

Integration tests verify the interaction between MCP server components and MoodleClient.
Mock strategy: Mock only external dependencies (HTTP layer via httpx and AI agent via Context).
Keep MoodleClient and MCP server logic to test integration.
"""
# Standard library imports
from unittest.mock import AsyncMock, patch, MagicMock

# Third-party imports
import pytest
import httpx
from mcp.server.fastmcp import Context

# Local imports
from src.mcp.protocol import MoodleClient
from src.mcp.server import get_courses, mcp


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_http_response(sample_courses):
    """Create a mock HTTP response for httpx.AsyncClient.post.
    
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


# ============================================================================
# CRUD OPERATIONS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_read_tool_integration(mock_context, mock_http_response, sample_courses):
    """Test complete integration for a READ operation (GET).
    
    This tests the full flow:
    1. MCP tool is called with context
    2. Tool calls real MoodleClient method
    3. MoodleClient makes HTTP call (mocked at httpx level)
    4. Response flows back through the layers
    
    Validates:
    - Tool executes without errors
    - Returns expected data structure
    - HTTP call is made with correct parameters
    - MoodleClient processes response correctly
    - Context logging works properly
    """
    # Mock only the HTTP layer (lowest level possible)
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        result = await get_courses(mock_context)
        
        # Verify result from full integration
        assert isinstance(result, list)
        assert len(result) == len(sample_courses)
        assert result[0]["shortname"] == sample_courses[0]["shortname"]
        assert result[0]["fullname"] == sample_courses[0]["fullname"]
        
        # Verify HTTP call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/webservice/rest/server.php"
        assert call_args[1]['data']['wsfunction'] == "core_course_get_courses"
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        assert call_args[1]['data']['moodlewsrestformat'] == "json"
        
        # Verify logging (AI agent interaction)
        mock_context.info.assert_called()


@pytest.mark.asyncio
async def test_create_tool_integration(mock_context, sample_courses_to_create):
    """Test complete integration for a CREATE operation (POST).
    
    Tests the full flow for creating new courses:
    1. MCP tool (create_courses) is called with course data
    2. Tool calls real MoodleClient.create_courses()
    3. MoodleClient makes HTTP POST call (mocked at httpx level)
    4. Response with created course IDs flows back
    
    Validates:
    - Tool executes without errors
    - Returns created courses with assigned IDs
    - HTTP call is made with correct parameters
    - Course data is properly formatted for Moodle API
    - Context logging works properly
    """
    from src.mcp.server import create_courses
    
    # Mock response with created courses (Moodle returns IDs)
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": 100,
            "shortname": "CS101"
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await create_courses(mock_context, courses=sample_courses_to_create)
        
        # Verify result from full integration
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["shortname"] == "CS101"
        
        # Verify HTTP call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/webservice/rest/server.php"
        assert call_args[1]['data']['wsfunction'] == "core_course_create_courses"
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        
        # Verify course data was sent
        assert 'courses' in call_args[1]['data']
        assert isinstance(call_args[1]['data']['courses'], list)
        assert len(call_args[1]['data']['courses']) == len(sample_courses_to_create)
        assert call_args[1]['data']['courses'][0]['fullname'] == sample_courses_to_create[0]['fullname']
        assert call_args[1]['data']['courses'][0]['shortname'] == sample_courses_to_create[0]['shortname']
        assert call_args[1]['data']['courses'][0]['categoryid'] == sample_courses_to_create[0]['categoryid']
        
        # Verify logging
        mock_context.info.assert_called()


@pytest.mark.asyncio
async def test_update_tool_integration(mock_context, sample_courses_to_update):
    """Test complete integration for an UPDATE operation (PUT/PATCH).
    
    Tests the full flow for updating existing courses:
    1. MCP tool (update_courses) is called with course updates
    2. Tool calls real MoodleClient.update_courses()
    3. MoodleClient makes HTTP POST call (mocked at httpx level)
    4. Response with update confirmation flows back
    
    Validates:
    - Tool executes without errors
    - Returns update result (typically warnings array)
    - HTTP call is made with correct parameters
    - Only specified fields are updated
    - Context logging works properly
    """
    from src.mcp.server import update_courses
    
    # Mock response (Moodle update typically returns warnings array)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "warnings": []
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await update_courses(mock_context, courses=sample_courses_to_update)
        
        # Verify result from full integration
        assert isinstance(result, dict)
        assert "warnings" in result
        assert len(result["warnings"]) == 0
        
        # Verify HTTP call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/webservice/rest/server.php"
        assert call_args[1]['data']['wsfunction'] == "core_course_update_courses"
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        
        # Verify course data was sent
        assert 'courses' in call_args[1]['data']
        assert isinstance(call_args[1]['data']['courses'], list)
        assert len(call_args[1]['data']['courses']) == len(sample_courses_to_update)
        assert call_args[1]['data']['courses'][0]['id'] == sample_courses_to_update[0]['id']
        assert call_args[1]['data']['courses'][0]['fullname'] == sample_courses_to_update[0]['fullname']
        
        # Verify logging
        mock_context.info.assert_called()


@pytest.mark.asyncio
async def test_delete_tool_integration(mock_context):
    """Test complete integration for DELETE operations.
    
    Tests the full flow for deleting courses:
    1. MCP tool (delete_courses) is called with course IDs
    2. Tool calls real MoodleClient.delete_courses()
    3. MoodleClient makes HTTP POST call (mocked at httpx level)
    4. Response with deletion confirmation flows back
    
    Validates:
    - Tool executes without errors
    - Returns deletion result (typically warnings array)
    - HTTP call is made with correct parameters
    - Course IDs are properly sent to API
    - Context logging works properly
    """
    from src.mcp.server import delete_courses
    
    # Course IDs to delete
    courseids_to_delete = [1, 2]
    
    # Mock response (Moodle delete typically returns warnings array)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "warnings": []
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await delete_courses(mock_context, courseids=courseids_to_delete)
        
        # Verify result from full integration
        assert isinstance(result, dict)
        assert "warnings" in result
        assert len(result["warnings"]) == 0
        
        # Verify HTTP call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/webservice/rest/server.php"
        assert call_args[1]['data']['wsfunction'] == "core_course_delete_courses"
        assert call_args[1]['data']['wstoken'] == "test_token_123"
        
        # Verify course IDs were sent
        assert 'courseids' in call_args[1]['data']
        assert isinstance(call_args[1]['data']['courseids'], list)
        assert len(call_args[1]['data']['courseids']) == 2
        assert call_args[1]['data']['courseids'][0] == 1
        assert call_args[1]['data']['courseids'][1] == 2
        
        # Verify logging
        mock_context.info.assert_called()


# ============================================================================
# MOODLE API ERROR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tool_with_invalid_parameters(mock_context, sample_moodle_invalid_parameter_error):
    """Test tool handles Moodle API invalid parameter errors.
    
    Simulates Moodle returning an invalid_parameter_exception error.
    
    Validates:
    - Tool propagates Moodle API parameter validation errors correctly
    - Error is logged appropriately
    - Exception is raised with correct message from Moodle
    """
    # Mock HTTP to return Moodle error
    mock_error_response = MagicMock()
    mock_error_response.json.return_value = sample_moodle_invalid_parameter_error
    mock_error_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_error_response
        
        # Tool should raise ValueError (from MoodleClient._call_function)
        with pytest.raises(ValueError, match="Invalid parameter"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


@pytest.mark.asyncio
async def test_tool_with_invalid_token(mock_context, sample_moodle_invalid_token_error):
    """Test tool handles invalid authentication token.
    
    Simulates Moodle returning an invalid_token_exception error.
    This occurs when the token doesn't exist or has been revoked.
    
    Validates:
    - Tool propagates token authentication errors correctly
    - Error is logged appropriately
    - Exception is raised with correct message from Moodle
    """
    # Mock HTTP to return Moodle invalid token error
    mock_error_response = MagicMock()
    mock_error_response.json.return_value = sample_moodle_invalid_token_error
    mock_error_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_error_response
        
        # Tool should raise ValueError (from MoodleClient._call_function)
        with pytest.raises(ValueError, match="Invalid token"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


@pytest.mark.asyncio
async def test_tool_with_access_exception(mock_context, sample_moodle_access_error):
    """Test tool handles Moodle access exceptions.
    
    Simulates Moodle returning access-related errors. This covers:
    - require_login_exception: User not logged in
    - required_capability_exception: User lacks required permissions
    - moodle_exception with access context: User cannot access specific resource
    
    Validates:
    - Tool propagates access/permission errors correctly
    - Error is logged appropriately
    - Exception is raised with correct message from Moodle
    """
    # Mock HTTP to return Moodle access error
    mock_error_response = MagicMock()
    mock_error_response.json.return_value = sample_moodle_access_error
    mock_error_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_error_response
        
        # Tool should raise ValueError (from MoodleClient._call_function)
        with pytest.raises(ValueError, match="you do not currently have permissions"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


# ============================================================================
# HTTP/NETWORK ERROR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tool_with_http_error(mock_context):
    """Test tool handles HTTP/network errors properly.
    
    Simulates network failure or HTTP error (500, timeout, connection refused).
    
    Validates:
    - Tool propagates HTTP errors correctly
    - Error is logged appropriately
    - Exception type is preserved (httpx.HTTPError)
    """
    # Mock HTTP to raise connection error
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection refused")
        
        with pytest.raises(httpx.HTTPError, match="Connection refused"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


# ============================================================================
# BEHAVIOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tool_empty_response(mock_context):
    """Test tool handles empty response correctly.
    
    Validates:
    - Tool returns empty list without errors
    - Logging indicates success with 0 items
    - No exceptions are raised for valid empty responses
    """
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await get_courses(mock_context)
        
        assert isinstance(result, list)
        assert len(result) == 0
        mock_context.info.assert_called()


@pytest.mark.asyncio
async def test_multiple_tool_calls_same_context(mock_context, mock_http_response, sample_courses):
    """Test multiple tool calls with the same context/client.
    
    Simulates an AI agent making multiple calls in the same session.
    
    Validates:
    - Multiple calls work correctly
    - Client state is maintained between calls
    - Results are consistent (idempotency for GET operations)
    - HTTP client is reused efficiently
    """
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        result1 = await get_courses(mock_context)
        result2 = await get_courses(mock_context)
        
        assert result1 == result2
        assert len(result1) == len(sample_courses)
        assert mock_post.call_count == 2


# ============================================================================
# MCP INFRASTRUCTURE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_server_tools_registration():
    """Test that tools are properly registered in the MCP server.
    
    Validates:
    - Tools are registered and discoverable
    - Tool has correct name
    - Tool has proper description
    - Tool metadata is accessible
    """
    # Get registered tools
    tools = await mcp.list_tools()
    
    assert len(tools) > 0, "No tools registered"
    
    # Find get_courses tool
    get_courses_tool = next((t for t in tools if t.name == "get_courses"), None)
    assert get_courses_tool is not None, "get_courses tool not found"
    
    # Verify tool metadata
    assert "Get courses from Moodle" in get_courses_tool.description


@pytest.mark.asyncio
async def test_context_lifespan_client_reuse(mock_http_response, sample_courses):
    """Test that context lifespan properly manages client lifecycle.
    
    This is closer to how the actual server works - the lifespan
    context manager creates and manages the client.
    
    Validates:
    - Client is created during lifespan
    - Same client instance is reused for multiple calls
    - Client maintains state across calls
    - Client cleanup is handled properly
    """
    # Create a real client (will use mocked HTTP)
    real_client = MoodleClient(
        base_url="http://localhost:8000",
        token="test_token_123"
    )
    
    # Create mock context with real client
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.request_context = MagicMock()
    mock_ctx.request_context.lifespan_context = real_client
    mock_ctx.info = AsyncMock()
    mock_ctx.error = AsyncMock()
    
    # Mock HTTP for the calls
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        # Simulate multiple calls with same context (same session)
        result1 = await get_courses(mock_ctx)
        result2 = await get_courses(mock_ctx)
        
        # Both calls use the same client instance
        assert result1 == result2
        assert mock_post.call_count == 2
        
    # Test cleanup: mock aclose and verify it's called when client is closed
    with patch.object(real_client.client, 'aclose', new_callable=AsyncMock) as mock_aclose:
        await real_client.close()
        mock_aclose.assert_called_once()
