from pydantic import BaseModel, ConfigDict


class KeyResponse(BaseModel):
    """
    Pydantic model for key response
    """

    username: str
    new_api_key: str
    model_config = ConfigDict(from_attributes=True)
