from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Conversation(BaseModel):
    messages: List[Message]


class ConversationResponseUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ConversationResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str]


class ConversationResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    system_fingerprint: str
    choices: List[ConversationResponseChoice]
    usage: ConversationResponseUsage


# Paper processing models
class PaperEmbedRequest(BaseModel):
    paper_id: str
    title: str
    abstract: str
    keywords: List[str]


class PaperEmbedResponse(BaseModel):
    paper_id: str
    status: str
    embedding: Optional[List[float]] = None


class VectorSearchRequest(BaseModel):
    query: str
    limit: int = 10


class VectorSearchResponse(BaseModel):
    results: List[dict]
    search_time: float


class PaperRecommendRequest(BaseModel):
    user_id: int
    paper_ids: List[str]
    limit: int = 10


class PaperRecommendResponse(BaseModel):
    recommendations: List[dict]
    recommendation_time: float


# 知识图谱三元组模型
class KGTriple(BaseModel):
    head: str
    relation: str
    tail: str
    paper_id: str
    source: str


class KGTripleSearchRequest(BaseModel):
    query: str
    limit: int = 10


class KGTripleSearchResponse(BaseModel):
    results: List[KGTriple]
    search_time: float
