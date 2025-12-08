"""MCP server integration tests.

Integration tests verify the interaction between MCP server components and MoodleClient.
Mock strategy: Mock only external dependencies (HTTP layer via httpx and AI agent via Context).
Keep MoodleClient and MCP server logic to test integration.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
import httpx
from src.mcp.protocol import MoodleClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_http_response(sample_courses):
    """Create a mock HTTP response for httpx.AsyncClient.post.
    
    Returns:
        Mock response configured with sample course data
    """
    mock_response = MagicMock()
    mock_response.json.return_value = sample_courses
    mock_response.raise_for_status = MagicMock()
    return mock_response


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
# TOOL TESTS - get_courses
# ============================================================================

@pytest.mark.asyncio
async def test_get_courses_tool_integration(mock_context, mock_http_response, sample_courses):
    """Test complete integration: MCP tool → MoodleClient → HTTP mock → response.
    
    This tests the full flow:
    1. MCP tool (get_courses) is called with context
    2. Tool calls real MoodleClient.get_courses()
    3. MoodleClient makes HTTP call (mocked at httpx level)
    4. Response flows back through the layers
    
    Validates:
    - Tool executes without errors
    - Returns expected course data
    - HTTP call is made with correct parameters
    - MoodleClient processes response correctly
    """
    from src.mcp.server import get_courses
    
    # Mock only the HTTP layer (lowest level possible)
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        result = await get_courses(mock_context)
        
        # Verify result from full integration
        assert isinstance(result, list)
        assert len(result) == len(sample_courses)
        assert result[0]["shortname"] == "ASW"
        assert result[0]["fullname"] == "Aplicacions i Serveis Web"
        
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
async def test_get_courses_tool_with_moodle_error(mock_context):
    """Test get_courses tool handles Moodle API errors properly.
    
    Simulates Moodle returning an error response (e.g., invalid token).
    
    Validates:
    - Tool propagates Moodle API errors correctly
    - Error is logged appropriately
    - Exception is raised with correct message
    """
    from src.mcp.server import get_courses
    
    # Mock HTTP to return Moodle error
    mock_error_response = MagicMock()
    mock_error_response.json.return_value = {
        "exception": "invalid_token_exception",
        "message": "Invalid token - token not found"
    }
    mock_error_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_error_response
        
        # Tool should raise ValueError (from MoodleClient._call_function)
        with pytest.raises(ValueError, match="Invalid token"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


@pytest.mark.asyncio
async def test_get_courses_tool_with_http_error(mock_context):
    """Test get_courses tool handles HTTP/network errors properly.
    
    Simulates network failure or HTTP error (500, timeout, etc.).
    
    Validates:
    - Tool propagates HTTP errors correctly
    - Error is logged appropriately
    - Exception is raised
    """
    from src.mcp.server import get_courses
    
    # Mock HTTP to raise connection error
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection refused")
        
        with pytest.raises(httpx.HTTPError, match="Connection refused"):
            await get_courses(mock_context)
        
        # Verify error was logged
        mock_context.error.assert_called()


@pytest.mark.asyncio
async def test_get_courses_tool_empty_response(mock_context):
    """Test get_courses tool handles empty course list.
    
    Validates:
    - Tool returns empty list without errors
    - Logging indicates success with 0 courses
    """
    from src.mcp.server import get_courses
    
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await get_courses(mock_context)
        
        assert isinstance(result, list)
        assert len(result) == 0
        mock_context.info.assert_called()


# ============================================================================
# RESOURCE TESTS - moodle://courses
# ============================================================================

@pytest.mark.asyncio
async def test_list_courses_resource_integration(mock_http_response, sample_courses, test_env):
    """Test complete integration for courses resource.
    
    Resources create their own MoodleClient, so we test:
    1. Resource creates MoodleClient with env vars
    2. MoodleClient makes HTTP call (mocked)
    3. Resource formats response as JSON
    4. Client is properly closed
    
    Validates:
    - Resource returns valid JSON
    - Data structure matches expected format
    - All course fields are properly formatted
    - Client cleanup happens
    """
    from src.mcp.server import list_courses_resource
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        # Mock aclose to verify cleanup
        with patch('httpx.AsyncClient.aclose', new_callable=AsyncMock) as mock_close:
            result = await list_courses_resource()
            
            # Verify result is valid JSON
            courses_data = json.loads(result)
            assert isinstance(courses_data, list)
            assert len(courses_data) == len(sample_courses)
            
            # Verify data format (resource formats differently than raw API)
            assert courses_data[0]["id"] == 1
            assert courses_data[0]["shortname"] == "ASW"
            assert courses_data[0]["fullname"] == "Aplicacions i Serveis Web"
            assert courses_data[0]["category"] == 1
            assert courses_data[0]["visible"] == 1
            
            # Verify HTTP call was made
            assert mock_post.called
            
            # Verify client was closed
            mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_list_courses_resource_with_moodle_error(test_env):
    """Test list_courses_resource handles Moodle API errors properly.
    
    Validates:
    - Resource raises exception on Moodle error
    - Client is closed even on error (cleanup in finally block)
    """
    from src.mcp.server import list_courses_resource
    
    mock_error_response = MagicMock()
    mock_error_response.json.return_value = {
        "exception": "invalid_token_exception",
        "message": "Invalid token - token not found"
    }
    mock_error_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_error_response
        
        with patch('httpx.AsyncClient.aclose', new_callable=AsyncMock) as mock_close:
            # Should raise ValueError from MoodleClient
            with pytest.raises(ValueError, match="Invalid token"):
                await list_courses_resource()
            
            # Verify cleanup happened even on error
            mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_list_courses_resource_missing_env():
    """Test list_courses_resource fails gracefully without env vars.
    
    Validates:
    - Resource raises RuntimeError when env vars are missing
    - Error message is clear
    """
    from src.mcp.server import list_courses_resource
    
    # Temporarily remove env vars
    import os
    old_url = os.environ.pop("MOODLE_URL", None)
    old_token = os.environ.pop("MOODLE_TOKEN", None)
    
    try:
        with pytest.raises(RuntimeError, match="Moodle configuration not found"):
            await list_courses_resource()
    finally:
        # Restore env vars
        if old_url:
            os.environ["MOODLE_URL"] = old_url
        if old_token:
            os.environ["MOODLE_TOKEN"] = old_token


# ============================================================================
# SERVER REGISTRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_server_tools_registration():
    """Test that tools are properly registered in the MCP server.
    
    Validates:
    - get_courses tool is registered
    - Tool has correct name and description
    - Tool metadata is accessible
    """
    from src.mcp.server import mcp
    
    # Get registered tools
    tools = await mcp.list_tools()
    
    assert len(tools) > 0, "No tools registered"
    
    # Find get_courses tool
    get_courses_tool = next((t for t in tools if t.name == "get_courses"), None)
    assert get_courses_tool is not None, "get_courses tool not found"
    
    # Verify tool metadata
    assert "Get all courses from Moodle" in get_courses_tool.description


@pytest.mark.asyncio  
async def test_server_resources_registration():
    """Test that resources are properly registered in the MCP server.
    
    Validates:
    - moodle://courses resource is registered
    - Resource has correct URI
    - Resource metadata is accessible
    """
    from src.mcp.server import mcp
    
    # Get registered resources
    resources = await mcp.list_resources()
    
    assert len(resources) > 0, "No resources registered"
    
    # Find courses resource
    courses_resource = next(
        (r for r in resources if str(r.uri) == "moodle://courses"),
        None
    )
    assert courses_resource is not None, "moodle://courses resource not found"


# ============================================================================
# INTEGRATION EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_tool_calls_same_context(mock_context, mock_http_response, sample_courses):
    """Test multiple tool calls with the same context/client.
    
    Simulates an AI agent making multiple calls in the same session.
    
    Validates:
    - Multiple calls work correctly
    - Client state is maintained between calls
    - Results are consistent
    """
    from src.mcp.server import get_courses
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        result1 = await get_courses(mock_context)
        result2 = await get_courses(mock_context)
        
        assert result1 == result2
        assert len(result1) == len(sample_courses)
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_context_lifespan_client_reuse(mock_http_response, sample_courses):
    """Test that context lifespan properly manages client lifecycle.
    
    This is closer to how the actual server works - the lifespan
    context manager creates and manages the client.
    
    Validates:
    - Client is created during lifespan
    - Same client instance is reused for multiple calls
    - Client is properly closed on shutdown
    """
    from src.mcp.server import get_courses
    from mcp.server.fastmcp import Context
    
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
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        # Simulate multiple calls with same context (same session)
        result1 = await get_courses(mock_ctx)
        result2 = await get_courses(mock_ctx)
        
        # Both calls use the same client instance
        assert result1 == result2
        
        # Cleanup
        with patch('httpx.AsyncClient.aclose', new_callable=AsyncMock) as mock_close:
            await real_client.close()
            mock_close.assert_called_once()
