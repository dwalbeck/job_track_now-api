import re
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class UserRequest(BaseModel):
    """Schema for user create/update request"""
    # User info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    login: Optional[str] = None
    passwd: Optional[str] = None

    # Address info
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None

    # User detail info
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # IDs for update operations
    user_id: Optional[int] = None
    address_id: Optional[int] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and v.strip():
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError('Invalid email format')
        return v

    @field_validator('linkedin_url', 'github_url', 'website_url', 'portfolio_url')
    @classmethod
    def validate_url(cls, v):
        if v and v.strip():
            if not v.startswith(('http://', 'https://')):
                raise ValueError('URL must start with http:// or https://')
        return v

    @model_validator(mode='after')
    def validate_required_fields(self):
        """
        Validate required fields based on operation type (create vs update).
        For new users (no user_id): first_name, last_name, login, passwd, email are required.
        For updates (has user_id): these fields are optional.
        """
        is_create = self.user_id is None

        if is_create:
            required_fields = ['first_name', 'last_name', 'login', 'passwd', 'email']
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"Required fields for new user: {', '.join(missing)}")

        return self

    @model_validator(mode='after')
    def validate_address_fields(self):
        """
        If any address field has a value, all fields except address_2 are required.
        """
        address_fields = ['address_1', 'city', 'state', 'zip', 'country']
        optional_field = 'address_2'

        # Get all address-related values
        all_address_fields = address_fields + [optional_field]
        address_values = {f: getattr(self, f) for f in all_address_fields}

        # Check if any address field has a value
        has_any_address = any(v and str(v).strip() for v in address_values.values())

        if has_any_address:
            # All required address fields must be present
            missing = [f for f in address_fields if not getattr(self, f) or not str(getattr(self, f)).strip()]
            if missing:
                raise ValueError(f"When providing address, these fields are required: {', '.join(missing)}")

        return self


class UserResponse(BaseModel):
    """Schema for user response"""
    # User info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    login: Optional[str] = None
    passwd: Optional[str] = None

    # Address info
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None

    # User detail info
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    # IDs
    user_id: Optional[int] = None
    address_id: Optional[int] = None

    class Config:
        from_attributes = True
