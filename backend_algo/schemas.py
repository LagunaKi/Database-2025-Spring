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
