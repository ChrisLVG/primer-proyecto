from pydantic import BaseModel, Field

class User(BaseModel):
    nombre: str = Field(..., description="The name of the user")
    numero: str = Field(..., description="The phone number of the user")
    email: str = Field(..., description="The email address of the user")

class userresponse(User):
    id: str = Field(..., description="The unique identifier of the user")

    class Config:
        from_attributes = True