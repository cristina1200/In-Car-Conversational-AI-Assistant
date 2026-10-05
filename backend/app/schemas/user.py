from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    voice_enrolled: bool
    created_at: str
