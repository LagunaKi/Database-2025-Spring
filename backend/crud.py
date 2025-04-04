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


def get_paper(db: Session, paper_id: str):
    # Use original paper_id for query (database stores full ID with version)
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Paper).offset(skip).limit(limit).all()


def count_papers(db: Session):
    return db.query(models.Paper).count()


def search_papers(db: Session, query: str, limit: int = 10):
    try:
        # First try vector search using ChromaDB client
        import chromadb
        from chromadb.utils import embedding_functions
        
        # Initialize ChromaDB client
        chroma_client = chromadb.HttpClient(host='localhost', port=8002)
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key="API_KEY_IS_NOT_NEEDED",
            api_base="http://10.176.64.152:11435/v1",
            model_name="bge-m3"
        )
        collection = chroma_client.get_collection(
            name="papers",
            embedding_function=openai_ef
        )
        
        # Perform vector search
        results = collection.query(
            query_texts=[query],
            n_results=limit * 2  # Get more results to account for possible missing papers
        )
        
        # Get paper IDs from results
        paper_ids = results['ids'][0]
        
        # Verify each paper exists in database
        existing_papers = []
        for pid in paper_ids:
            paper = db.query(models.Paper).filter(models.Paper.id == pid).first()
            if paper:
                existing_papers.append(paper)
            else:
                print(f"Warning: Paper {pid} found in vector DB but not in main database")
        
        # Log search results
        print(f"Vector search returned {len(paper_ids)} papers, found {len(existing_papers)} valid papers in database")
        
        # Return up to limit papers
        return existing_papers[:limit] if len(existing_papers) > 0 else []
    
    except Exception as e:
        print(f"Vector search failed, falling back to text search: {e}")
    
    # Fallback to text search if vector search fails
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
