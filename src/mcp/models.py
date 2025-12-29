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

    def to_moodle_dict(self) -> list[dict[str, Any]]:
        """Converts the model to a list of {name, value} dicts for Moodle API.
        
        Moodle expects options as an array of objects with 'name' and 'value' keys.
        Only includes non-None fields.
        """
        options = []
        data = self.model_dump(exclude_none=True)
        
        for name, value in data.items():
            options.append({"name": name, "value": value})
        
        return options


class ManualEnrolment(BaseModel):
    """Represents a manual enrolment operation for a user in a course.
    
    Used with enrol_manual_enrol_users to manually enrol users.
    """
    roleid: int = Field(
        ...,
        description="Role ID to assign to the user in the course"
    )
    userid: int = Field(
        ...,
        description="User ID to enrol"
    )
    courseid: int = Field(
        ...,
        description="Course ID in which to enrol the user"
    )
    timestart: Optional[int] = Field(
        default=None,
        description="Enrolment start timestamp. 0 means immediate or use default configuration"
    )
    timeend: Optional[int] = Field(
        default=None,
        description="Enrolment end timestamp. 0 means no time restriction"
    )
    suspend: Optional[int] = Field(
        default=None,
        description="Set to 1 to create enrolment in suspended (inactive) state. 0 for active enrolment"
    )

    def to_moodle_dict(self) -> dict[str, Any]:
        """Converts the model to a dictionary compatible with the Moodle API.
        
        Removes None fields to avoid sending unnecessary data to the API.
        """
        return self.model_dump(exclude_none=True)


# ============================================================================
# User Models
# ============================================================================

class UserCustomField(BaseModel):
    """Custom field for a user profile."""
    type: str = Field(
        ...,
        description="Name/type of the custom field"
    )
    value: str = Field(
        ...,
        description="Value of the custom field"
    )


class UserPreference(BaseModel):
    """Preference for a user."""
    type: str = Field(
        ...,
        description="Name/type of the preference"
    )
    value: str = Field(
        ...,
        description="Value of the preference"
    )


class UserCreate(BaseModel):
    """Represents a user to be created in Moodle.
    
    Used with core_user_create_users to create new users.
    """
    # Required fields
    username: str = Field(
        ...,
        min_length=1,
        description="Username (unique). Must follow Moodle security policy"
    )
    firstname: str = Field(
        ...,
        min_length=1,
        description="First name(s) of the user"
    )
    lastname: str = Field(
        ...,
        min_length=1,
        description="Last name(s) of the user"
    )
    email: str = Field(
        ...,
        min_length=1,
        description="Valid and unique email address"
    )
    
    # Password options (mutually exclusive)
    createpassword: Optional[int] = Field(
        default=None,
        description="Set to 1 to have system create and email password. Incompatible with password field"
    )
    password: Optional[str] = Field(
        default=None,
        description="Plain text password. Incompatible with createpassword field"
    )
    
    # Common optional fields
    auth: str = Field(
        default="manual",
        description="Authentication plugin. Default: 'manual' (e.g., 'ldap')"
    )
    idnumber: str = Field(
        default="",
        description="Arbitrary ID code. Default: empty string"
    )
    lang: str = Field(
        default="en",
        description="Language code (e.g., 'en', must exist in Moodle). Default: 'en'"
    )
    calendartype: str = Field(
        default="gregorian",
        description="Calendar type (e.g., 'gregorian', must exist in Moodle). Default: 'gregorian'"
    )
    
    # Location fields
    city: Optional[str] = Field(
        default=None,
        description="User's city"
    )
    country: Optional[str] = Field(
        default=None,
        description="Country code (e.g., 'ES', 'MX')"
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Timezone (e.g., 'America/Mexico_City'). '99' for site default"
    )
    
    # Contact and profile fields
    maildisplay: Optional[int] = Field(
        default=None,
        description="Email visibility (privacy setting)"
    )
    mailformat: Optional[int] = Field(
        default=None,
        description="Preferred email format: 0=plain text, 1=HTML"
    )
    description: Optional[str] = Field(
        default=None,
        description="Profile description (no HTML)"
    )
    
    # Name variations
    firstnamephonetic: Optional[str] = Field(
        default=None,
        description="First name(s) phonetically"
    )
    lastnamephonetic: Optional[str] = Field(
        default=None,
        description="Last name(s) phonetically"
    )
    middlename: Optional[str] = Field(
        default=None,
        description="Middle name"
    )
    alternatename: Optional[str] = Field(
        default=None,
        description="Alternate name"
    )
    
    # Additional profile fields
    interests: Optional[str] = Field(
        default=None,
        description="Interests separated by commas"
    )
    institution: Optional[str] = Field(
        default=None,
        description="Institution"
    )
    department: Optional[str] = Field(
        default=None,
        description="Department"
    )
    phone1: Optional[str] = Field(
        default=None,
        description="Primary phone number"
    )
    phone2: Optional[str] = Field(
        default=None,
        description="Secondary phone number"
    )
    address: Optional[str] = Field(
        default=None,
        description="Postal address"
    )
    
    # Appearance
    theme: Optional[str] = Field(
        default=None,
        description="Theme name (must exist in Moodle)"
    )
    
    # Custom fields and preferences
    customfields: Optional[list[UserCustomField]] = Field(
        default=None,
        description="Custom profile fields"
    )
    preferences: Optional[list[UserPreference]] = Field(
        default=None,
        description="User preferences"
    )

    @field_validator('createpassword', 'password')
    @classmethod
    def validate_password_options(cls, v: Optional[int | str], info) -> Optional[int | str]:
        """Validates that createpassword and password are not both set."""
        field_name = info.field_name
        if v is not None:
            # Check if the other field is also set
            other_field = 'password' if field_name == 'createpassword' else 'createpassword'
            if info.data.get(other_field) is not None:
                raise ValueError('createpassword and password are incompatible')
        return v

    def to_moodle_dict(self) -> dict[str, Any]:
        """Converts the model to a dictionary compatible with the Moodle API.
        
        Removes None fields and converts nested objects to dictionaries.
        """
        data = self.model_dump(exclude_none=True)
        
        # Convert nested objects to dictionaries if they exist
        if 'customfields' in data and data['customfields']:
            data['customfields'] = [
                field if isinstance(field, dict) else field.model_dump()
                for field in data['customfields']
            ]
        
        if 'preferences' in data and data['preferences']:
            data['preferences'] = [
                pref if isinstance(pref, dict) else pref.model_dump()
                for pref in data['preferences']
            ]
        
        return data


class UserSearchCriteria(BaseModel):
    """Search criteria for finding users.
    
    Used with core_user_get_users to search for users matching specific criteria.
    """
    key: str = Field(
        ...,
        description="User column to search by: 'id', 'lastname', 'firstname', 'idnumber', 'username', 'email', 'auth'"
    )
    value: str = Field(
        ...,
        min_length=1,
        description="Value to search for. Use '%' as wildcard for text fields. For 'id', must be numeric string"
    )

    def to_moodle_dict(self) -> dict[str, Any]:
        """Converts the model to a dictionary compatible with the Moodle API."""
        return self.model_dump()


# ============================================================================
# Enrolment Models
# ============================================================================

class EnrolledUsersOption(BaseModel):
    """Options for filtering enrolled users results.
    
    All fields are optional. Only specify the filters you want to apply.
    """
    withcapability: Optional[str] = Field(
        default=None,
        description="Return only users with this capability. Requires moodle/role:review permission"
    )
    groupid: Optional[int] = Field(
        default=None,
        description="Return only users in this group. Requires moodle/site:accessallgroups if querying user not in group"
    )
    onlyactive: Optional[int] = Field(
        default=None,
        description="1 to return only users with active enrolments. Requires moodle/course:enrolreview. Incompatible with onlysuspended"
    )
    onlysuspended: Optional[int] = Field(
        default=None,
        description="1 to return only suspended users. Requires moodle/course:enrolreview. Incompatible with onlyactive"
    )
    userfields: Optional[str] = Field(
        default=None,
        description="Comma-separated list of user fields to return (e.g., 'id,firstname,lastname')"
    )
    limitfrom: Optional[int] = Field(
        default=None,
        description="SQL offset for pagination"
    )
    limitnumber: Optional[int] = Field(
        default=None,
        description="Maximum number of users to return"
    )
    sortby: Optional[str] = Field(
        default=None,
        description="Field to sort by: id, firstname, lastname, siteorder"
    )
    sortdirection: Optional[str] = Field(
        default=None,
        description="Sort direction: ASC or DESC"
    )

    @field_validator('onlyactive', 'onlysuspended')
    @classmethod
    def validate_active_suspended(cls, v: Optional[int], info) -> Optional[int]:
        """Validates that onlyactive and onlysuspended are not both set."""
        field_name = info.field_name
        if v is not None:
            # Check if the other field is also set
            other_field = 'onlysuspended' if field_name == 'onlyactive' else 'onlyactive'
            if info.data.get(other_field) is not None:
                raise ValueError('onlyactive and onlysuspended are incompatible')
        return v