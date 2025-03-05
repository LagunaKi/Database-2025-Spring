from typing import List

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    is_active: bool
    is_superuser: bool

    class Config:
        # orm_mode = True
        from_attributes = True

class UserList(BaseModel):
    total: int
    users: List[User]


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str
