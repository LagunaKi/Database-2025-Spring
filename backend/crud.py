from sqlalchemy.orm import Session
from sqlalchemy import or_, func

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
    # Hybrid search: text search + vector search (when available)
    from backend_algo.main import vector_search
    
    try:
        # First try vector search
        vector_results = vector_search(query, limit)
        if vector_results:
            paper_ids = [result["paper_id"] for result in vector_results]
            return db.query(models.Paper).filter(
                models.Paper.id.in_(paper_ids)
            ).all()
    except:
        pass
    
    # Fallback to text search
    keywords = query.split()
    conditions = []
    for keyword in keywords:
        search = f"%{keyword}%"
        conditions.append(models.Paper.title.ilike(search))
        conditions.append(models.Paper.abstract.ilike(search))
    
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
