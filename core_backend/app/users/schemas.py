from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """
    Pydantic model for user creation
    """

    username: str
    password: str
    user_id: str
    retrieval_key: str

    model_config = ConfigDict(from_attributes=True)


class KeyResponse(BaseModel):
    """
    Pydantic model for key response
    """

    user_id: str
    username: str
    retrieval_key: str
    model_config = ConfigDict(from_attributes=True)
