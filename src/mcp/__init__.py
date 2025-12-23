"""MCP Moodle Server package.

This package provides a Model Context Protocol (MCP) server for interacting
with Moodle Learning Management System through its Web Services API.
"""
from .models import Course, CourseUpdate, CourseFormatOption, CourseCustomField
from .protocol import MoodleClient
from .server import mcp, run_server

__all__ = [
    # Models
    "Course",
    "CourseUpdate",
    "CourseFormatOption",
    "CourseCustomField",
    # Client
    "MoodleClient",
    # Server
    "mcp",
    "run_server",
]
