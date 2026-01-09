# Testing

Documentation about testing strategy, coverage, and test execution.

## Testing Strategy

The project implements two main types of tests:

### 1. Unit Tests (`test_moodle.py`)

Test the protocol layer (`MoodleClient`) in isolation.

**Mocking strategy**:

- Mock only the HTTP layer (`httpx.AsyncClient.post`)
- Keep all `MoodleClient` logic unmocked
- Validate that requests have the correct format
- Validate that responses are processed correctly

**What is tested**:

- Client initialization
- Parameter flattening
- Moodle API error handling
- HTTP error handling
- Model to Moodle format conversion
- Each public method of `MoodleClient`

### 2. Integration Tests (`test_mcp.py`)

Test the complete integration between MCP Server and MoodleClient.

**Mocking strategy**:

- Mock only the HTTP layer (same as unit tests)
- Keep both `MoodleClient` and MCP tools unmocked
- Mock the Context (AI agent side)
- Test the complete data flow

**What is tested**:

- Complete CRUD operations (Create, Read, Update, Delete)
- Error handling propagated from Moodle API
- HTTP error handling
- Behavior with empty responses
- Multiple calls with the same context
- Correct registration of MCP tools
- Client lifecycle management

## Reusable Fixtures

Defined in `conftest.py`:

```python
@pytest.fixture(scope="session")
def test_env()
    # Configure environment variables for tests

@pytest.fixture
def sample_courses()
    # Sample course data

@pytest.fixture
def sample_courses_to_create()
    # Course models to create

@pytest.fixture
def sample_courses_to_update()
    # CourseUpdate models to update

@pytest.fixture
def sample_moodle_invalid_parameter_error()
    # Moodle invalid parameter error

@pytest.fixture
def sample_moodle_invalid_token_error()
    # Invalid token error

@pytest.fixture
def sample_moodle_access_error()
    # Permission error
```

## Running Tests

### All tests

```bash
pytest
```

### Tests with verbose output

```bash
pytest -v
```

### Specific tests

```bash
# Only unit tests
pytest tests/test_moodle.py

# Only integration tests
pytest tests/test_mcp.py

# Specific test
pytest tests/test_moodle.py::test_get_courses

# Tests from a class
pytest tests/test_moodle.py::TestMoodleClient
```

### With coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term

# With details of missing lines
pytest --cov=src --cov-report=term-missing
```

The HTML report is generated in `htmlcov/index.html`

### Tests in watch mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw
```

## Test Coverage

### Target

- **Lines**: > 90%
- **Functions**: > 90%
- **Classes**: 100%

### Current Status

Run to see current status:

```bash
pytest --cov=src --cov-report=term
```

### Covered Areas

✅ **Protocol Layer** (`protocol.py`):

- All methods of `MoodleClient`
- `flatten_params()` function
- Error handling in `_call_function()`
- Model conversion

✅ **Server Layer** (`server.py`):

- All MCP server tools
- Server lifecycle
- Error handling

✅ **Models** (`models.py`):

- Pydantic model validation
- Conversion to Moodle format
- Custom validators

## Test Structure

### Typical Unit Test (test_moodle.py)

```python
@pytest.mark.asyncio
async def test_get_courses(moodle_client, sample_courses):
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
        assert len(result) == len(sample_courses)
```

### Typical Integration Test (test_mcp.py)

```python
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
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response
        
        result = await get_courses(mock_context)
        
        # Verify result from full integration
        assert isinstance(result, list)
        assert len(result) == len(sample_courses)
        
        # Verify HTTP call was made correctly
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[1]['data']['wsfunction'] == "core_course_get_courses"
```

## CI/CD

### GitHub Actions

The project includes CI/CD configuration (if available):

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Best Practices

1. **Mock at the lowest level possible**: Only HTTP, keep real logic
2. **Independent tests**: Each test should be able to run alone
3. **Reusable fixtures**: DRY in test data
4. **Descriptive names**: The test name should explain what it tests
5. **Complete docstrings**: Explain what each test validates
6. **Clear assertions**: Verify specific behavior
7. **Automatic cleanup**: Use fixtures with session/function scope as needed

## Debugging Tests

### Show print statements

```bash
pytest -s
```

### Verbose mode with output

```bash
pytest -v -s
```

### Run with debugger

```bash
pytest --pdb
```

### Show warnings

```bash
pytest -W all
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Pytest-cov](https://pytest-cov.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
