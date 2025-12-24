"""Pydantic models for Moodle API data structures."""
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Course Models
# ============================================================================

class CourseFormatOption(BaseModel):
    """Additional format option for a course."""
    name: str = Field(..., description="Course format option name")
    value: str = Field(..., description="Course format option value")


class CourseCustomField(BaseModel):
    """Custom field for a course."""
    shortname: str = Field(..., description="Short name of the custom field")
    value: str = Field(..., description="Value of the custom field")


class Course(BaseModel):
    """Represents a Moodle course with all possible attributes.
    
    To create a course, only fullname, shortname and categoryid are required.
    All other fields are optional and have default values.
    """
    # Required fields
    fullname: str = Field(
        ..., 
        min_length=1,
        description="Full course name, e.g.: 'Advanced Mathematics 2024'"
    )
    shortname: str = Field(
        ..., 
        min_length=1,
        description="Unique short course name, e.g.: 'MAT-ADV-2024'"
    )
    categoryid: int = Field(
        ..., 
        gt=0,
        description="Category ID where the course will be created (must be > 0)"
    )
    
    # Optional fields with default values
    idnumber: Optional[str] = Field(
        default=None,
        description="Course identification number (optional)"
    )
    summary: str = Field(
        default="",
        description="HTML description of the course"
    )
    summaryformat: Literal[0, 1, 2, 4] = Field(
        default=1,
        description="Summary format: 1=HTML, 0=MOODLE, 2=PLAIN, 4=MARKDOWN"
    )
    format: str = Field(
        default="topics",
        description="Course format: 'topics', 'weeks', 'social', 'site', etc."
    )
    showgrades: Literal[0, 1] = Field(
        default=1,
        description="Show grades: 1=yes, 0=no"
    )
    newsitems: int = Field(
        default=5,
        ge=0,
        description="Number of recent items appearing on the course page"
    )
    startdate: Optional[int] = Field(
        default=None,
        description="Course start timestamp (Unix timestamp)"
    )
    enddate: Optional[int] = Field(
        default=None,
        description="Course end timestamp (Unix timestamp)"
    )
    numsections: Optional[int] = Field(
        default=None,
        ge=0,
        description="(Deprecated) Number of weeks/topics, use courseformatoptions instead"
    )
    maxbytes: int = Field(
        default=0,
        ge=0,
        description="Maximum file size that can be uploaded to the course (0 = no limit)"
    )
    showreports: Literal[0, 1] = Field(
        default=0,
        description="Show activity reports: 1=yes, 0=no"
    )
    visible: Literal[0, 1] = Field(
        default=1,
        description="Course visibility: 1=available to students, 0=not available"
    )
    hiddensections: Optional[Literal[0, 1]] = Field(
        default=None,
        description="(Deprecated) How hidden sections are displayed: 0=collapsed, 1=invisible"
    )
    groupmode: Literal[0, 1, 2] = Field(
        default=0,
        description="Group mode: 0=no groups, 1=separate groups, 2=visible groups"
    )
    groupmodeforce: Literal[0, 1] = Field(
        default=0,
        description="Force group mode: 1=yes, 0=no"
    )
    defaultgroupingid: int = Field(
        default=0,
        ge=0,
        description="Default grouping ID"
    )
    enablecompletion: Optional[Literal[0, 1]] = Field(
        default=None,
        description="Enable completion: 1=enabled, 0=disabled"
    )
    completionnotify: Optional[Literal[0, 1]] = Field(
        default=None,
        description="Notify completion: 1=yes, 0=no"
    )
    lang: Optional[str] = Field(
        default=None,
        description="Forced course language (language code, e.g.: 'es', 'en')"
    )
    forcetheme: Optional[str] = Field(
        default=None,
        description="Forced theme name for the course"
    )
    courseformatoptions: Optional[list[CourseFormatOption]] = Field(
        default=None,
        description="Additional options for particular course format"
    )
    customfields: Optional[list[CourseCustomField]] = Field(
        default=None,
        description="Custom course fields"
    )

    @field_validator('enddate')
    @classmethod
    def validate_enddate(cls, v: Optional[int], info) -> Optional[int]:
        """Validates that enddate is after startdate if both are present."""
        if v is not None and info.data.get('startdate') is not None:
            if v < info.data['startdate']:
                raise ValueError('enddate must be after startdate')
        return v

    def to_moodle_dict(self) -> dict:
        """Converts the model to a dictionary compatible with the Moodle API.
        
        Removes None fields to avoid sending unnecessary data to the API.
        """
        data = self.model_dump(exclude_none=True)
        
        # Convert nested objects to dictionaries if they exist
        if 'courseformatoptions' in data and data['courseformatoptions']:
            data['courseformatoptions'] = [
                opt if isinstance(opt, dict) else opt.model_dump()
                for opt in data['courseformatoptions']
            ]
        
        if 'customfields' in data and data['customfields']:
            data['customfields'] = [
                field if isinstance(field, dict) else field.model_dump()
                for field in data['customfields']
            ]
        
        return data


class CourseUpdate(Course):
    """Represents a Moodle course, adapted for updating.
    
    Extends Course but makes fullname, shortname and categoryid optional,
    since for updating only the id and the fields to be modified are required.
    """
    # Make id required for updating
    id: int = Field(
        ..., 
        gt=0,
        description="ID of the course to update (must be > 0)"
    )
    
    # Make previously required fields optional for updating
    fullname: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Full course name, e.g.: 'Advanced Mathematics 2024'"
    )
    shortname: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Unique short course name, e.g.: 'MAT-ADV-2024'"
    )
    categoryid: Optional[int] = Field(
        default=None,
        gt=0,
        description="Category ID where the course will be created (must be > 0)"
    )


class CourseContentsOption(BaseModel):
    """Options for filtering course contents (available since Moodle 2.9).
    
    All fields are optional. Only specify the filters you want to apply.
    """
    excludemodules: Optional[bool] = Field(
        default=None,
        description="Do not return modules, return only the sections structure"
    )
    excludecontents: Optional[bool] = Field(
        default=None,
        description="Do not return module contents (i.e: files inside a resource)"
    )
    includestealthmodules: Optional[bool] = Field(
        default=None,
        description="Return stealth modules for students in a special section (with id -1)"
    )
    sectionid: Optional[int] = Field(
        default=None,
        description="Return only this section by its ID"
    )
    sectionnumber: Optional[int] = Field(
        default=None,
        description="Return only this section by its number/order"
    )
    cmid: Optional[int] = Field(
        default=None,
        description="Return only this course module (activity) by its ID"
    )
    modname: Optional[str] = Field(
        default=None,
        description="Return only modules with this name, e.g.: 'forum', 'assign', 'quiz', 'resource'"
    )
    modid: Optional[int] = Field(
        default=None,
        description="Return only the module with this ID (to be used with modname)"
    )
