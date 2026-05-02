from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """
    Base model for user-related data, containing common fields and validation
    rules.
    """

    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False


class UserCreate(UserBase):
    """
    Model for creating a new user, extending UserBase and adding a password
    field.
    """

    password: str


class UserOut(UserBase):
    """
    Model for outputting user data, containing only the user ID and configured
    to allow creation from object attributes.
    """

    id: int
    model_config = {"from_attributes": True}
    # from_attributes “Allow creating this model from an object’s attributes (not just dicts).”


class UserLogin(BaseModel):
    """Model for user login, containing email and password fields."""

    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Model for requesting a password change."""

    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if value.lower() == value or value.upper() == value:
            raise ValueError(
                "Password must contain both uppercase and lowercase letters"
            )
        if not any(char.isdigit() for char in value):
            raise ValueError("New password must contain at least one digit")
        return value


class PasswordResetEmailRequest(BaseModel):
    """
    Model for requesting a password reset email, containing only the email
    field.
    """

    email: EmailStr


class PasswordResetRequest(BaseModel):
    """
    Model for requesting a password reset, containing the reset token and new
    password.
    """

    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if value.lower() == value or value.upper() == value:
            raise ValueError("New password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("New password must contain at least one digit")
        return value
