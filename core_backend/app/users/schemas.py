from pydantic import BaseModel, ConfigDict


# not yet used.
class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str
    content_quota: int

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """
    Pydantic model for user creation
    """

    password: str

    model_config = ConfigDict(from_attributes=True)
