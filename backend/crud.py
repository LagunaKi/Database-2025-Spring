import re
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, String

from . import models, schemas
from .security import get_password_hash


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def count_users(db: Session):
    return db.query(models.User).count()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_paper(db: Session, paper: schemas.PaperCreate):
    db_paper = models.Paper(
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        keywords=paper.keywords,
        published_date=paper.published_date,
        pdf_url=paper.pdf_url,
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper


def get_paper(db: Session, paper_id: int):
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Paper).offset(skip).limit(limit).all()


def count_papers(db: Session):
    return db.query(models.Paper).count()


def search_papers(db: Session, query: str, limit: int = 10):
    # Temporarily disable vector search for testing
    # Academic-oriented text search only
    conditions = []
    
    # 1. Check for academic category code (e.g. cs.CL)
    if re.match(r'[a-z]+\.[A-Z]+', query):
        conditions.append(func.json_contains(models.Paper.keywords, f'"{query}"'))
    
    # 2. Handle Chinese and English terms differently
    terms = []
    if any('\u4e00' <= char <= '\u9fff' for char in query):  # Check if contains Chinese
        # For Chinese, search the whole phrase
        terms.append(query)
    else:
        # For English, split into words
        terms += [term for term in re.split(r'[\s,\-\.;]+', query) if len(term) > 1]
    
    # 3. Build search conditions
    for term in terms:
        conditions.append(models.Paper.title.ilike(f"%{term}%"))
        conditions.append(models.Paper.abstract.ilike(f"%{term}%"))
    
    return db.query(models.Paper).filter(
        or_(*conditions)
    ).limit(limit).all()


def record_user_interaction(db: Session, interaction: schemas.UserPaperInteractionCreate):
    db_interaction = models.UserPaperInteraction(
        user_id=interaction.user_id,
        paper_id=interaction.paper_id,
        action_type=interaction.action_type
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction
