# Make backend_algo a Python package
from .main import app
from .schemas import (
    Conversation,
    ConversationResponse,
    PaperEmbedRequest,
    PaperEmbedResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    PaperRecommendRequest,
    PaperRecommendResponse
)

__all__ = [
    'app',
    'Conversation',
    'ConversationResponse',
    'PaperEmbedRequest',
    'PaperEmbedResponse',
    'VectorSearchRequest',
    'VectorSearchResponse',
    'PaperRecommendRequest',
    'PaperRecommendResponse'
]
