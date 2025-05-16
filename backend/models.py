from datetime import datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(256), unique=True, index=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    hashed_password = Column(String(256))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    papers = relationship("UserPaperInteraction", back_populates="user")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(50), primary_key=True)  # arXiv IDs are strings like "2107.12345"
    title = Column(String(256), index=True)
    authors = Column(JSON)  # Store as JSON array
    abstract = Column(Text)
    keywords = Column(JSON)  # Store as JSON array
    published_date = Column(DateTime, nullable=True)
    pdf_url = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    is_kg_processed = Column(Boolean, default=False)

    users = relationship("UserPaperInteraction", back_populates="paper")


class UserPaperInteraction(Base):
    __tablename__ = "user_paper_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    paper_id = Column(String(50), ForeignKey("papers.id"))
    action_type = Column(String(50))  # "view", "download", "favorite", etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="papers")
    paper = relationship("Paper", back_populates="users")


class ChatResponse(Base):
    __tablename__ = "chat_responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    matched_papers = relationship("AnswerPaperMatch", back_populates="chat_response")


class AnswerPaperMatch(Base):
    __tablename__ = "answer_paper_matches"

    id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey("chat_responses.id"))
    paper_id = Column(String(50), ForeignKey("papers.id"))
    match_score = Column(Integer)  # 匹配分数
    matched_section = Column(Text)  # 回答中匹配的部分
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_response = relationship("ChatResponse", back_populates="matched_papers")
    paper = relationship("Paper")
