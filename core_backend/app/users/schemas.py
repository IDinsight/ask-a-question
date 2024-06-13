from pydantic import BaseModel, ConfigDict


# not yet used.
class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str

    model_config = ConfigDict(from_attributes=True)


class UserCreateWithPassword(UserCreate):
    """
    Pydantic model for user creation
    """

    password: str

    model_config = ConfigDict(from_attributes=True)


class UserRetrieve(BaseModel):
    """
    Pydantic model for user retrieval
    """

    user_id: int
    username: str

    model_config = ConfigDict(from_attributes=True)
