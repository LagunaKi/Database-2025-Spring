from typing import List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class PaperBase(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    keywords: Optional[List[str]] = []
    published_date: Optional[datetime] = None
    pdf_url: str


class PaperCreate(PaperBase):
    pass


class Paper(PaperBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_processed: bool

    class Config:
        from_attributes = True


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
    papers: List[Paper]


class PaperList(BaseModel):
    total: int
    papers: List[Paper]


class PaperList(BaseModel):
    total: int
    papers: List[Paper]


class PaperSearchRequest(BaseModel):
    query: str
    limit: int = 10


class PaperSearchResponse(BaseModel):
    papers: List[Paper]
    search_time: float


class PaperRecommendRequest(BaseModel):
    user_id: int
    limit: int = 10


class PaperRecommendResponse(BaseModel):
    papers: List[Paper]
    recommendation_time: float


class PaperEmbedRequest(BaseModel):
    paper_id: str
    title: str
    abstract: str
    keywords: List[str]


class PaperEmbedResponse(BaseModel):
    paper_id: str
    status: str
    embedding: Optional[List[float]] = None


class UserPaperInteractionBase(BaseModel):
    user_id: int
    paper_id: str  # Changed from int to match Paper model
    action_type: str


class UserPaperInteractionCreate(UserPaperInteractionBase):
    pass


class UserPaperInteraction(UserPaperInteractionBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
