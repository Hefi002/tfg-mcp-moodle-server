"""Unit tests for MoodleClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.mcp.protocol import MoodleClient
from src.mcp.models import ManualEnrolment, ManualUnenrolment, UserCreate, UserSearchCriteria
import httpx

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
    
    Verifies that _call_function properly passes extra kwargs to Moodle API,
    and that flatten_params converts nested structures to Moodle's expected format.
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
        
        # Verify the data is flattened to Moodle format
        call_args = mock_post.call_args
        flattened_data = call_args[1]['data']
        
        # Check flattened course parameters
        assert flattened_data['courses[0][fullname]'] == "Mathematics 101"
        assert flattened_data['courses[0][shortname]'] == "MATH101"
        assert flattened_data['courses[0][categoryid]'] == 1
        
        # Verify standard parameters are also present
        assert flattened_data['wstoken'] == "test_token_123"
        assert flattened_data['wsfunction'] == "core_course_create_courses"
        assert flattened_data['moodlewsrestformat'] == "json"
        
        # Verify result
        assert result == [{"id": 100, "shortname": "MATH101"}]


@pytest.mark.asyncio
async def test_call_function_unexpected_type(moodle_client):
    """Test _call_function handles completely unexpected response types.
    
    The API accepts dict, list, str, int, and None as valid response types.
    This test verifies that truly unexpected types (e.g., float, bool)
    still raise ValueError.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = 3.14  # float is not a valid type
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(moodle_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="unexpected type"):
            await moodle_client._call_function("core_course_get_courses")

@pytest.mark.asyncio
async def test_call_function_moodle_error(moodle_client):
    """Test handling of protocol errors, handled by Moodle API.

    MOODLE API protocol errors return a JSON with "exception" field. Also returns a message explaining the error.
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
# Course Tests
# ============================================================================

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
        assert result[0]["id"] == sample_courses[0]["id"]
        assert result[0]["shortname"] == sample_courses[0]["shortname"]


@pytest.mark.asyncio
async def test_create_courses(moodle_client, sample_courses_to_create):
    """Test create_courses method with minimum required fields.
    
    Tests the base case with only required fields:
    - fullname: Full course name
    - shortname: Short course code
    - categoryid: Category ID
    
    Validates:
    - Calls correct Moodle function
    - Passes courses parameter correctly (converted to dict and flattened)
    - Returns list of created courses with assigned IDs
    """
    created_courses = [
        {
            "id": 100,
            "shortname": "CS101"
        }
    ]
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = created_courses
        
        result = await moodle_client.create_courses(sample_courses_to_create)
        
        # Verify correct function called
        mock_call.assert_called_once()
        call_args = mock_call.call_args
        assert call_args[0][0] == "core_course_create_courses"
        
        # Verify courses were converted to dicts (by to_moodle_dict)
        # Note: We're mocking _call_function, so flatten_params happens inside it
        courses_arg = call_args[1]['courses']
        assert isinstance(courses_arg, list)
        assert isinstance(courses_arg[0], dict)
        assert courses_arg[0]['fullname'] == "Introduction to Programming"
        assert courses_arg[0]['shortname'] == "CS101"
        assert courses_arg[0]['categoryid'] == 1
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["shortname"] == "CS101"


@pytest.mark.asyncio
async def test_update_courses(moodle_client, sample_courses_to_update):
    """Test update_courses method with minimum required fields.
    
    Tests the base case with only required field:
    - id: Course ID to update
    
    Plus one field to update (in this case fullname).
    
    Validates:
    - Calls correct Moodle function
    - Passes courses parameter correctly (converted to dict and flattened)
    - Returns result dictionary with warnings array
    """
    update_result = {"warnings": []}
    
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = update_result
        
        result = await moodle_client.update_courses(sample_courses_to_update)
        
        # Verify correct function called
        mock_call.assert_called_once()
        call_args = mock_call.call_args
        assert call_args[0][0] == "core_course_update_courses"
        
        # Verify courses were converted to dicts (by to_moodle_dict)
        # Note: We're mocking _call_function, so flatten_params happens inside it
        courses_arg = call_args[1]['courses']
        assert isinstance(courses_arg, list)
        assert isinstance(courses_arg[0], dict)
        assert courses_arg[0]['id'] == 1
        assert courses_arg[0]['fullname'] == "Advanced Web Development"
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "warnings" in result
        assert result["warnings"] == []


@pytest.mark.asyncio
async def test_delete_courses(moodle_client):
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


@pytest.mark.asyncio
async def test_get_course_contents(moodle_client):
    """Test get_course_contents without options (base case).

    Verifies:
    - Calls the correct Moodle function with only courseid parameter
    - Returns the list of sections as provided by the API
    """
    sample_course_contents = [
        {
            "id": 1,
            "name": "Section 0",
            "summary": "",
            "modules": [
                {"id": 10, "modname": "forum", "name": "General forum"}
            ]
        },
        {
            "id": 2,
            "name": "Section 1",
            "summary": "",
            "modules": []
        }
    ]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_course_contents

        result = await moodle_client.get_course_contents(1)

        # Verify the function was called with only courseid
        mock_call.assert_called_once_with(
            "core_course_get_contents",
            courseid=1
        )

        # Verify result structure
        assert isinstance(result, list)
        assert result == sample_course_contents


@pytest.mark.asyncio
async def test_view_course(moodle_client):
    """Test view_course (core_course_view_course) base case without sectionnumber.

    Verifies:
    - Calls the correct Moodle function with courseid and default sectionnumber
    - Returns the dict as provided by the API
    """
    sample_view_result = {
        "status": 1,
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_view_result

        result = await moodle_client.view_course(42)

        # Verify the function was called with the expected parameters
        mock_call.assert_called_once_with(
            "core_course_view_course",
            courseid=42,
            sectionnumber=0
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert result == sample_view_result


@pytest.mark.asyncio
async def test_get_recent_courses(moodle_client, sample_courses):
    """Test get_recent_courses base case (all parameters default).

    Ensures the correct Moodle function is called without extra parameters and
    that the returned list of courses is propagated unchanged.
    """
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_courses

        result = await moodle_client.get_recent_courses()

        # Should call the function without additional parameters
        mock_call.assert_called_once_with("core_course_get_recent_courses")

        # Verify the returned result
        assert isinstance(result, list)
        assert result == sample_courses


@pytest.mark.asyncio
async def test_get_course_module(moodle_client):
    """Base case test for get_course_module.

    Ensures:
    - correct webservice function is invoked,
    - cmid parameter is passed correctly,
    - returned value is propagated unchanged,
    - cm object contains expected fields.
    """
    expected_func = "core_course_get_course_module"
    cmid = 42
    expected_result = {
        "cm": {
            # Identification and Location
            "id": 42,
            "course": 10,
            "module": 15,
            "modname": "assign",
            "instance": 5,
            "name": "Assignment 1: Introduction to Programming",
            "section": 3,
            "sectionnum": 1,
            "added": 1640000000,
            "idnumber": "ASSIGN001",
            # Visibility and Access
            "visible": 1,
            "visibleoncoursepage": 1,
            "visibleold": 1,
            "availability": '{"op":"&","c":[],"showc":[]}',
            "downloadcontent": 1,
            "showdescription": 1,
            # Groups
            "groupmode": 0,
            "groupingid": 0,
            # Completion
            "completion": 2,
            "completionexpected": 1672000000,
            "completionview": 1,
            "completiongradeitemnumber": 0,
            "completionpassgrade": 1,
            # Grading
            "grade": 100.0,
            "gradepass": "50.00",
            "gradecat": 1,
            "scale": None,
            "advancedgrading": [
                {"area": "submissions", "method": "rubric"}
            ],
            "outcomes": [
                {"id": 1, "name": "Critical Thinking", "scale": "1,2,3,4,5"}
            ],
            # Format and Presentation
            "indent": 0,
            "score": 0
        },
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.get_course_module(cmid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            cmid=cmid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert "cm" in result
        assert "warnings" in result

        # Verify cm object structure
        cm = result["cm"]
        assert cm["id"] == 42
        assert cm["modname"] == "assign"
        assert cm["name"] == "Assignment 1: Introduction to Programming"
        assert cm["course"] == 10
        assert cm["visible"] == 1
        assert cm["completion"] == 2
        assert cm["groupmode"] == 0
        assert cm["grade"] == 100.0
        assert cm["gradepass"] == "50.00"

        # Verify optional fields
        assert "advancedgrading" in cm
        assert len(cm["advancedgrading"]) == 1
        assert cm["advancedgrading"][0]["method"] == "rubric"

        assert "outcomes" in cm
        assert len(cm["outcomes"]) == 1
        assert cm["outcomes"][0]["name"] == "Critical Thinking"


# ============================================================================
# Enrol Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_course_enrolment_methods(moodle_client):
    """Test get_course_enrolment_methods calls the correct Moodle function and returns list."""
    sample_methods = [
        {
            "id": 10,
            "courseid": 42,
            "type": "manual",
            "name": "Manual enrolments",
            "status": "enabled",
            "wsfunction": "enrol_manual_get_instance_info"
        },
        {
            "id": 11,
            "courseid": 42,
            "type": "self",
            "name": "Self enrolment",
            "status": "disabled"
        }
    ]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_methods

        result = await moodle_client.get_course_enrolment_methods(42)

        # Verificar que se llamó la función Moodle correcta con el parámetro courseid
        mock_call.assert_called_once_with(
            "core_enrol_get_course_enrolment_methods",
            courseid=42
        )

        # Verificar estructura y contenido del resultado
        assert isinstance(result, list)
        assert result == sample_methods


@pytest.mark.asyncio
async def test_get_enrolled_users(moodle_client):
    """Test get_enrolled_users base case without options.

    Verifica que se llame a la función `core_enrol_get_enrolled_users` con el
    parámetro `courseid` y que la lista retornada se propague sin cambios.
    """
    sample_users = [
        {"id": 1, "fullname": "Alice"},
        {"id": 2, "fullname": "Bob"}
    ]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_users

        result = await moodle_client.get_enrolled_users(42)

        # Debe llamar la función Moodle con el parámetro courseid
        mock_call.assert_called_once_with(
            "core_enrol_get_enrolled_users",
            courseid=42
        )

        # Verificar el resultado
        assert isinstance(result, list)
        assert result == sample_users


@pytest.mark.asyncio
async def test_manual_enrol_users(moodle_client):
    """Test manual_enrol_users base case.

    Ensures that `manual_enrol_users` calls the correct Moodle function
    with the enrolments converted to dictionaries and returns an empty
    dict when the API returns null/None (success case).
    """
    enrolment = ManualEnrolment(roleid=3, userid=5, courseid=42, timestart=0, suspend=0)
    expected_enrolments = [enrolment.to_moodle_dict()]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        # Moodle often returns null on success; protocol.manual_enrol_users maps None -> {}
        mock_call.return_value = None

        result = await moodle_client.manual_enrol_users([enrolment])

        # Verify the Moodle function name and parameter were passed correctly
        mock_call.assert_called_once_with(
            "enrol_manual_enrol_users",
            enrolments=expected_enrolments
        )

        # Verify the result is an empty dict on success
        assert isinstance(result, dict)
        assert result == {}

@pytest.mark.asyncio
async def test_manual_unenrol_users(moodle_client):
    """Base case test for manual_unenrol_users.

    Ensures:
    - correct webservice function is invoked,
    - enrolments are converted to dictionaries and passed correctly,
    - returns empty dict on success (null/None from API).
    """
    expected_func = "enrol_manual_unenrol_users"
    unenrolment = ManualUnenrolment(userid=5, courseid=42)
    expected_enrolments = [unenrolment.to_moodle_dict()]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        # Moodle returns null/None on success; protocol.manual_unenrol_users maps None -> {}
        mock_call.return_value = None

        result = await moodle_client.manual_unenrol_users([unenrolment])

        # Verify the Moodle function name and parameters were passed correctly
        mock_call.assert_called_once_with(
            expected_func,
            enrolments=expected_enrolments
        )

        # Verify the result is an empty dict on success
        assert isinstance(result, dict)
        assert result == {}

# ============================================================================
# User Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_users(moodle_client):
    """Test create_users base case.

    Ensures that `create_users` calls the correct Moodle function
    with users converted to dictionaries and returns the list of
    created users provided by the API.
    """
    user = UserCreate(username="jdoe", firstname="John", lastname="Doe", email="jdoe@example.com", createpassword=1)
    expected_users = [user.to_moodle_dict()]
    created_response = [{"id": 55, "username": "jdoe"}]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = created_response

        result = await moodle_client.create_users([user])

        # Verify correct function called with users converted to dicts
        mock_call.assert_called_once_with(
            "core_user_create_users",
            users=expected_users
        )

        # Verify the returned result matches the API response
        assert isinstance(result, list)
        assert result == created_response


@pytest.mark.asyncio
async def test_get_users(moodle_client):
    """Test get_users base case.

    Ensures that `get_users` calls the correct Moodle function
    with criteria converted to dictionaries and returns the
    dictionary response provided by the API.
    """
    criterion = UserSearchCriteria(key="username", value="jdoe")
    expected_criteria = [criterion.to_moodle_dict()]

    api_response = {
        "users": [
            {"id": 55, "username": "jdoe", "firstname": "John", "lastname": "Doe"}
        ],
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = api_response

        result = await moodle_client.get_users([criterion])

        # Verify the Moodle function and parameters
        mock_call.assert_called_once_with(
            "core_user_get_users",
            criteria=expected_criteria
        )

        # Verify the returned structure matches the API response
        assert isinstance(result, dict)
        assert "users" in result
        assert result == api_response


@pytest.mark.asyncio
async def test_get_users_courses(moodle_client):
    """Test get_users_courses base case.

    Ensures that `get_users_courses` calls the correct Moodle function
    with the provided userid and returnusercount and returns the list
    of courses as provided by the API.
    """
    sample_courses_for_user = [
        {
            "id": 101,
            "shortname": "BIO101",
            "fullname": "Biology 101",
            "enrolledusercount": 42
        },
        {
            "id": 102,
            "shortname": "CHEM101",
            "fullname": "Chemistry 101",
            "enrolledusercount": 30
        }
    ]

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_courses_for_user

        # Call with default returnusercount
        result = await moodle_client.get_users_courses(userid=5)

        # Verify correct Moodle function and parameters
        mock_call.assert_called_once_with(
            "core_enrol_get_users_courses",
            userid=5,
            returnusercount=1
        )

        # Verify the returned list matches the API response
        assert isinstance(result, list)
        assert result == sample_courses_for_user


# ============================================================================
# Completion Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_course_completion_status(moodle_client):
    """Base case test for get_course_completion_status.

    Ensures:
    - correct webservice function is invoked,
    - courseid and userid are forwarded,
    - returned value is propagated unchanged.
    """
    expected_func = "core_completion_get_course_completion_status"
    courseid = 10
    userid = 5
    expected_result = {
        "completionstatus": {"completed": 0, "aggregation": 1, "completions": []},
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.get_course_completion_status(courseid, userid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid,
            userid=userid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result


@pytest.mark.asyncio
async def test_get_activities_completion_status(moodle_client):
    """Base case test for get_activities_completion_status.

    Ensures:
    - correct webservice function is invoked,
    - courseid and userid are forwarded,
    - returned value is propagated unchanged.
    """
    expected_func = "core_completion_get_activities_completion_status"
    courseid = 10
    userid = 5
    expected_result = {
        "statuses": [
            {"cmid": 101, "modname": "quiz", "instance": 5, "state": 1, "timecompleted": 1620000000}
        ],
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.get_activities_completion_status(courseid, userid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid,
            userid=userid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result


@pytest.mark.asyncio
async def test_update_activity_completion_status_manually(moodle_client):
    """Base case test for update_activity_completion_status_manually.

    Ensures:
    - correct webservice function is invoked,
    - cmid and completed parameters are forwarded,
    - returned value is propagated unchanged.
    """
    expected_func = "core_completion_update_activity_completion_status_manually"
    cmid = 42
    completed = 1
    expected_result = {
        "status": 1,
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.update_activity_completion_status_manually(cmid, completed)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            cmid=cmid,
            completed=completed
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert result["status"] == 1
        assert "warnings" in result

# ============================================================================
# Grades Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_grades(moodle_client):
    """Base case test for update_grades.

    Ensures:
    - correct webservice function is invoked,
    - all required parameters are forwarded correctly,
    - grades and itemdetails are converted to dictionaries,
    - returns integer result code (0 for success).
    """
    from src.mcp.models import StudentGrade, GradeItemDetails

    expected_func = "core_grades_update_grades"
    source = "test_script"
    courseid = 10
    component = "mod_assign"
    activityid = 42
    itemnumber = 0

    # Create test data
    grades = [
        StudentGrade(studentid=5, grade=85.5, str_feedback="Good work!"),
        StudentGrade(studentid=6, grade=92.0)
    ]
    itemdetails = GradeItemDetails(
        itemname="Final Project",
        grademax=100.0,
        grademin=0.0
    )

    # Expected conversion to dicts
    expected_grades = [g.to_moodle_dict() for g in grades]
    expected_itemdetails = itemdetails.to_moodle_dict()

    # API returns 0 for success (GRADE_UPDATE_OK)
    expected_result = 0

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.update_grades(
            source=source,
            courseid=courseid,
            component=component,
            activityid=activityid,
            itemnumber=itemnumber,
            grades=grades,
            itemdetails=itemdetails
        )

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            source=source,
            courseid=courseid,
            component=component,
            activityid=activityid,
            itemnumber=itemnumber,
            grades=expected_grades,
            itemdetails=expected_itemdetails
        )

        # Verify result is the integer code
        assert isinstance(result, int)
        assert result == 0  # GRADE_UPDATE_OK


@pytest.mark.asyncio
async def test_get_gradeitems(moodle_client):
    """Base case test for get_gradeitems.

    Ensures:
    - correct webservice function is invoked,
    - courseid parameter is forwarded correctly,
    - returned value is propagated unchanged.
    """
    expected_func = "core_grades_get_gradeitems"
    courseid = 10
    expected_result = {
        "gradeItems": [
            {
                "id": "mod_quiz_42_0",
                "itemname": "Quiz 1: Introduction",
                "category": "Quizzes"
            },
            {
                "id": "mod_assign_15_0",
                "itemname": "Assignment 1: Essay",
                "category": "Assignments"
            },
            {
                "id": "manual_10",
                "itemname": "Participation"
            }
        ],
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.get_gradeitems(courseid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert "gradeItems" in result
        assert len(result["gradeItems"]) == 3
        assert result["gradeItems"][0]["id"] == "mod_quiz_42_0"
        assert result["gradeItems"][0]["itemname"] == "Quiz 1: Introduction"
        assert result["gradeItems"][0]["category"] == "Quizzes"


@pytest.mark.asyncio
async def test_get_grade_items_user_report(moodle_client):
    """Base case test for get_grade_items_user_report.

    Ensures:
    - correct webservice function is invoked,
    - courseid parameter is passed correctly,
    - optional parameters (userid, groupid) are handled when not specified,
    - returned value is propagated unchanged.
    """
    expected_func = "gradereport_user_get_grade_items"
    courseid = 10
    expected_result = {
        "usergrades": [
            {
                "courseid": 10,
                "userid": 5,
                "userfullname": "John Doe",
                "gradeitems": [
                    {
                        "id": 100,
                        "itemname": "Test Assignment",
                        "itemtype": "mod",
                        "graderaw": 85.5,
                        "gradeformatted": "85.50"
                    }
                ]
            }
        ],
        "warnings": []
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        # Test with only courseid (base case)
        result = await moodle_client.get_grade_items_user_report(courseid=courseid)

        # Verify correct function called with only courseid
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert "usergrades" in result
        assert len(result["usergrades"]) == 1
        assert result["usergrades"][0]["userfullname"] == "John Doe"


@pytest.mark.asyncio
async def test_get_grade_tree(moodle_client):
    """Base case test for get_grade_tree.

    Ensures:
    - correct webservice function is invoked,
    - courseid parameter is forwarded correctly,
    - JSON string from API is parsed and returned as dict,
    - dict returned directly from API is also handled.
    """
    import json

    expected_func = "core_grades_get_grade_tree"
    courseid = 10

    # Sample grade tree structure
    tree_structure = {
        "id": "course_10",
        "type": "course",
        "name": "Test Course",
        "children": [
            {
                "id": "category_1",
                "type": "category",
                "name": "Assignments",
                "aggregation": "weighted_mean",
                "children": [
                    {
                        "id": "item_101",
                        "type": "item",
                        "itemname": "Assignment 1",
                        "grademax": 100.0,
                        "grademin": 0.0
                    },
                    {
                        "id": "item_102",
                        "type": "item",
                        "itemname": "Assignment 2",
                        "grademax": 100.0,
                        "grademin": 0.0
                    }
                ]
            },
            {
                "id": "category_2",
                "type": "category",
                "name": "Quizzes",
                "aggregation": "simple_weighted_mean",
                "children": [
                    {
                        "id": "item_201",
                        "type": "item",
                        "itemname": "Quiz 1",
                        "grademax": 50.0,
                        "grademin": 0.0
                    }
                ]
            }
        ]
    }

    # Test case 1: Moodle returns JSON string (needs parsing)
    api_response_string = json.dumps(tree_structure)

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = api_response_string

        result = await moodle_client.get_grade_tree(courseid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid
        )

        # Verify result is parsed dict (not a string)
        assert isinstance(result, dict)
        assert result == tree_structure
        assert result["type"] == "course"
        assert len(result["children"]) == 2
        assert result["children"][0]["name"] == "Assignments"
        assert len(result["children"][0]["children"]) == 2

    # Test case 2: Moodle returns dict directly (no parsing needed)
    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = tree_structure

        result = await moodle_client.get_grade_tree(courseid)

        # Verify result is the same dict
        assert isinstance(result, dict)
        assert result == tree_structure


@pytest.mark.asyncio
async def test_get_feedback(moodle_client):
    """Base case test for get_feedback.

    Ensures:
    - correct webservice function is invoked,
    - all required parameters are forwarded correctly,
    - returned value is propagated unchanged.
    """
    expected_func = "core_grades_get_feedback"
    courseid = 10
    userid = 5
    itemid = 42
    expected_result = {
        "feedbacktext": "Great work on this assignment! Keep it up.",
        "title": "Assignment 1: Essay",
        "fullname": "John Doe",
        "picture": "https://moodle.example.com/user/pix.php/5/f1.jpg",
        "additionalfield": "jdoe@example.com"
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        result = await moodle_client.get_feedback(courseid, userid, itemid)

        # Verify correct function and parameters
        mock_call.assert_called_once_with(
            expected_func,
            courseid=courseid,
            userid=userid,
            itemid=itemid
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert result["feedbacktext"] == "Great work on this assignment! Keep it up."
        assert result["fullname"] == "John Doe"


@pytest.mark.asyncio
async def test_get_site_info(moodle_client):
    """Base case test for get_site_info.

    Ensures:
    - correct webservice function is invoked,
    - function is called without parameters (serviceshortnames is deprecated and not exposed),
    - returned value is propagated unchanged.
    """
    expected_func = "core_webservice_get_site_info"
    expected_result = {
        "userid": 2,
        "username": "admin",
        "firstname": "Admin",
        "lastname": "User",
        "fullname": "Admin User",
        "lang": "en",
        "sitename": "Test Moodle Site",
        "siteurl": "http://localhost:8000",
        "release": "4.4.1",
        "version": "2024100700.00",
        "userissiteadmin": 1,
        "functions": [
            {"name": "core_course_get_courses", "version": "2024100700.00"},
            {"name": "core_user_get_users", "version": "2024100700.00"}
        ],
        "downloadfiles": 1,
        "uploadfiles": 1
    }

    with patch.object(moodle_client, '_call_function', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_result

        # Test without parameters (base case)
        result = await moodle_client.get_site_info()

        # Verify correct function called without extra parameters
        mock_call.assert_called_once_with(
            expected_func
        )

        # Verify result propagated
        assert isinstance(result, dict)
        assert result == expected_result
        assert result["userid"] == 2
        assert result["username"] == "admin"
        assert result["sitename"] == "Test Moodle Site"
        assert "functions" in result
        assert len(result["functions"]) == 2



