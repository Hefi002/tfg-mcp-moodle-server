# API Reference

This section contains the complete documentation of all project modules.

## Code Structure

The project is organized into the following modules:

### Models (`models.py`)

Pydantic models for validation and serialization of Moodle API data.

**Includes**:

- Course models (Course, CourseUpdate, CourseContentsOption)
- Enrollment models (ManualEnrolment, ManualUnenrolment, EnrolledUsersOption)
- User models (UserCreate, UserSearchCriteria)
- Grade models (GradeItemDetails, StudentGrade)

### Protocol (`protocol.py`)

Protocol layer that handles communication with the Moodle Web Services API.

**Main class**: `MoodleClient`

**Key functions**:

- `flatten_params()`: Converts nested structures to Moodle format
- Methods for all CRUD operations on courses, users, enrollments, grades, etc.

### Server (`server.py`)

MCP server that exposes tools for AI agents.

**Main components**:

- `app_lifespan()`: Context manager for server lifecycle
- Tools decorated with `@mcp.tool()` for each available operation

**Tool categories**:

- Course Tools: Course management
- Enrolment Tools: Enrollments
- User Tools: User management
- Completion Tools: Completion status
- Grades Tools: Grades
- Webservice Tools: Site information

## Automatic Documentation

The following sections contain the complete documentation automatically generated from docstrings:

## Models

::: src.mcp.models
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      heading_level: 3

## Protocol - MoodleClient

::: src.mcp.protocol.flatten_params
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

::: src.mcp.protocol.MoodleClient
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      heading_level: 3

## Server - MCP Tools

::: src.mcp.server.app_lifespan
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

::: src.mcp.server.get_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.create_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.update_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.delete_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_course_contents
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.view_course
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_recent_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_course_module
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_enrolled_users
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.manual_enrol_users
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.manual_unenrol_users
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.create_users
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_users
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_users_courses
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_course_completion_status
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_activities_completion_status
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.update_activity_completion_status_manually
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.update_grades
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_gradeitems
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_grade_items_user_report
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_grade_tree
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_feedback
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.get_site_info
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: src.mcp.server.run_server
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3
