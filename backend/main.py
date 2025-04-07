from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional
import re
import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Request, Query
from pydantic import BaseModel


class PaperDetailResponse(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    pdf_url: str
    keywords: Optional[List[str]] = None
    published_date: Optional[str] = None
    year: Optional[int] = None
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.database import SessionLocal, engine
from backend.security import verify_password

import requests



# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


models.Base.metadata.create_all(bind=engine)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

app = FastAPI()

# 配置详细日志输出到控制台和文件
import logging
from logging.handlers import RotatingFileHandler

# 创建logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 控制台handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 文件handler (最大10MB，保留3个备份)
file_handler = RotatingFileHandler(
    'backend.log', 
    maxBytes=10*1024*1024,
    backupCount=3,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)

# 日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 测试日志输出
logger.info("Logger initialized successfully")

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"收到请求: {request.method} {request.url}")
    logger.debug(f"请求头: {dict(request.headers)}")
    try:
        response = await call_next(request)
        logger.debug(f"请求处理完成: {request.method} {request.url} 状态码: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"请求处理出错: {str(e)}")
        raise

# 健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "port": 8000,
        "listening": True
    }

# 连通性测试端点
@app.get("/api/test/echo")
async def echo_test(
    request: Request,
    text: str = "test"
):
    logger.info(f"Echo test request from {request.client.host}")
    return {
        "echo": text,
        "headers": dict(request.headers),
        "client": str(request.client),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# 确保CORS是第一个中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:3333",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3333"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # 暴露所有头部
)

# 添加调试端点
@app.get("/api/debug/cors")
async def debug_cors(request: Request):
    return {
        "origin": request.headers.get("origin"),
        "access-control-request-headers": request.headers.get("access-control-request-headers"),
        "user-agent": request.headers.get("user-agent")
    }


# Dependency
def get_session():
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def authenticate_user(db: Session, username: str, password: str):
    user = crud.get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        db: SessionDep
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug(f"Validating token: {token[:10]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token validation failed: username not found in payload")
            raise credentials_exception
        token_data = TokenData(username=username)
        logger.debug(f"Token validated for user: {username}")
    except InvalidTokenError as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/api/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDep
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/api/users/me/", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)],
):
    return current_user


@app.post("/api/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: SessionDep):
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.get("/api/users/", response_model=schemas.UserList)
async def read_users(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        db: SessionDep,
        skip: int = 0,
        limit: int = 100,
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return schemas.UserList(total=crud.count_users(db), users=users)


@app.get("/api/users/{user_id}", response_model=schemas.User)
async def read_user(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        user_id: int,
        db: SessionDep
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.get("/api/users/name/{username}", response_model=schemas.User)
async def read_user(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        username: str,
        db: SessionDep
):
    # print(current_user.username)
    db_user = crud.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        chat_request: schemas.ChatRequest,
        db: SessionDep
):
    try:
        # 获取大模型回答
        resp = requests.post('http://localhost:8001/chat/', json={
            'messages': [{
                'role': 'user',
                'content': chat_request.prompt
            }]
        }, timeout=10)
        resp.raise_for_status()
        
        # 解析LLM响应
        llm_response = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # 搜索相关论文
        papers = crud.search_papers(db, query=chat_request.prompt, limit=5)
        print(f"Found {len(papers)} papers for query: {chat_request.prompt}")  # 调试日志
        for i, paper in enumerate(papers):
            print(f"Paper {i+1}: {paper.title}")
        
        return schemas.ChatResponse(
            response=llm_response,
            papers=papers
        )
    except requests.exceptions.RequestException as e:
        print(f"Error calling chat service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is currently unavailable"
        )


# Paper related endpoints
@app.post("/api/papers/", response_model=schemas.Paper)
async def create_paper(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        paper: schemas.PaperCreate,
        db: SessionDep
):
    return crud.create_paper(db=db, paper=paper)


@app.get("/api/papers/", response_model=schemas.PaperList)
async def read_papers(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        db: SessionDep,
        skip: int = 0,
        limit: int = 100
):
    papers = crud.get_papers(db, skip=skip, limit=limit)
    return schemas.PaperList(total=crud.count_papers(db), papers=papers)


@app.get("/api/papers/{paper_id:path}", response_model=PaperDetailResponse)
async def read_paper(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        paper_id: str,
        db: SessionDep,
        request: Request
):
    logger.info(f"Paper detail request - User: {current_user.id}, Paper: {paper_id}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request URL: {request.url}")
    
    try:
        # 规范化paper_id
        paper_id = paper_id.strip()
        if not paper_id:
            raise HTTPException(
                status_code=422,
                detail="Paper ID cannot be empty"
            )

        # 尝试获取论文
        db_paper = crud.get_paper(db, paper_id=paper_id)
        if not db_paper:
            logger.warning(f"Paper not found: {paper_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Paper with ID '{paper_id}' not found"
            )

        # 验证并准备响应数据
        response_data = {
            "id": str(db_paper.id),
            "title": str(db_paper.title) if db_paper.title else "",
            "authors": list(db_paper.authors) if db_paper.authors else [],
            "abstract": str(db_paper.abstract) if db_paper.abstract else "",
            "pdf_url": str(db_paper.pdf_url) if db_paper.pdf_url else "",
            "keywords": list(db_paper.keywords) if db_paper.keywords else [],
            "published_date": db_paper.published_date.isoformat() if db_paper.published_date else None,
            "year": db_paper.published_date.year if db_paper.published_date else None
        }

        logger.debug(f"Prepared response data: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing paper detail request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Error processing paper details: {str(e)}"
        )
        
        
        logger.info(f"Successfully retrieved paper: {paper_id}")
        return response_data
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error processing paper detail request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Error processing paper details: {str(e)}"
        )


@app.get("/api/papers/search/", response_model=schemas.PaperSearchResponse)
async def search_papers(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        query: str,
        db: SessionDep,
        limit: int = 10
):
    papers = crud.search_papers(db, query=query, limit=limit)
    
    # Record searched papers in user_paper_interactions
    for paper in papers:
        interaction = schemas.UserPaperInteractionCreate(
            user_id=current_user.id,
            paper_id=paper.id,
            action_type="search"
        )
        crud.record_user_interaction(db=db, interaction=interaction)
    
    db.commit()
    return schemas.PaperSearchResponse(papers=papers, search_time=0.0)


async def _handle_recommendation(
    current_user: schemas.User,
    db: Session,
    paper_id: str,
    source: str
) -> PaperDetailResponse:
    """Shared recommendation logic"""
    logger.info(f"Recommendation request - User: {current_user.id}, Paper: {paper_id} (from {source})")
    
    try:
        # Verify current paper exists
        current_paper = crud.get_paper(db, paper_id=paper_id)
        if not current_paper:
            logger.warning(f"Paper not found: {paper_id}")
            raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
        
        # Get user's recently viewed papers
        viewed_papers = crud.get_user_interactions(
            db, 
            user_id=current_user.id,
            action_type="view",
            limit=5
        )
        viewed_papers = [p for p in viewed_papers if p.id != paper_id]
        
        if not viewed_papers:
            logger.info("No user history, using random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Build search query from viewed papers
        search_terms = []
        for paper in viewed_papers:
            if paper.keywords:
                search_terms.extend(paper.keywords)
            if paper.title:
                search_terms.append(paper.title.split()[0])
        
        if not search_terms:
            logger.info("No keywords, using random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Get most frequent terms
        from collections import Counter
        query = " ".join([term for term, _ in Counter(search_terms).most_common(3)])
        
        # Find similar papers
        candidate_papers = crud.search_papers(db, query=query, limit=10)
        candidate_papers = [p for p in candidate_papers if p.id != paper_id]
        
        if not candidate_papers:
            logger.info("No similar papers, using random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Return top candidate
        recommended_paper = candidate_papers[0]
        logger.info(f"Recommended paper: {recommended_paper.id}")
        
        return await read_paper(
            current_user=current_user,
            paper_id=recommended_paper.id,
            db=db,
            request=Request(scope={"type": "http"})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        return await _get_random_recommendation(current_user, db, paper_id)

@app.get("/api/recommendations/{paper_id}")
async def get_recommendation(
    request: Request,
    current_user: Annotated[schemas.User, Depends(get_current_active_user)],
    db: SessionDep,
    paper_id: str
) -> PaperDetailResponse:
    """Get paper recommendations based on user history"""
    logger.debug(f"Recommendation request for paper: {paper_id}")
    
    # Verify paper exists
    paper = crud.get_paper(db, paper_id=paper_id)
    if not paper:
        logger.warning(f"Paper not found: {paper_id}")
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Get user's recently viewed papers (last 5)
    viewed_papers = crud.get_user_interactions(
        db, 
        user_id=current_user.id,
        action_type="view",
        limit=5
    )
    
    # Filter out current paper and get keywords
    keywords = set()
    for p in viewed_papers:
        if p.id != paper_id and p.keywords:
            keywords.update(p.keywords)
    
    if not keywords:
        # Fallback to random recommendation if no history
        papers = db.query(models.Paper).filter(models.Paper.id != paper_id).all()
        if not papers:
            raise HTTPException(status_code=404, detail="No papers available")
        recommended = random.choice(papers)
    else:
        # Find papers with matching keywords
        query = " ".join(keywords)
        candidates = crud.search_papers(db, query=query, limit=10)
        candidates = [p for p in candidates if p.id != paper_id]
        recommended = candidates[0] if candidates else None
    
    if not recommended:
        raise HTTPException(status_code=404, detail="No recommendations available")
    
    return await read_paper(
        current_user=current_user,
        paper_id=recommended.id,
        db=db,
        request=request
    )
    """Get personalized recommendation based on user history and current paper"""
    logger.info(f"Recommendation request - User: {current_user.id}, Paper: {paper_id}")
    logger.debug(f"Full request URL: {Request.url}")
    
    try:
        # Verify current paper exists with actual paper_id
        logger.debug(f"Querying paper with ID: {paper_id}")
        current_paper = crud.get_paper(db, paper_id=paper_id)
        if not current_paper:
            logger.warning(f"Paper not found: {paper_id}")
            raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
        
        # Get user's recently viewed papers (excluding current paper)
        viewed_papers = crud.get_user_interactions(
            db, 
            user_id=current_user.id,
            action_type="view",
            limit=5
        )
        viewed_papers = [p for p in viewed_papers if p.id != paper_id]
        
        if not viewed_papers:
            logger.info("No user history available, falling back to random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Build search query from viewed papers' keywords
        search_terms = []
        for paper in viewed_papers:
            if paper.keywords:
                search_terms.extend(paper.keywords)
            if paper.title:
                search_terms.append(paper.title.split()[0])  # Add first word of title
        
        if not search_terms:
            logger.info("No keywords available, falling back to random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Use most frequent 3 terms as query
        from collections import Counter
        query = " ".join([term for term, _ in Counter(search_terms).most_common(3)])
        logger.debug(f"Generated search query from user history: {query}")
        
        # Search for similar papers (excluding current paper)
        candidate_papers = crud.search_papers(db, query=query, limit=10)
        candidate_papers = [p for p in candidate_papers if p.id != paper_id]
        
        if not candidate_papers:
            logger.info("No similar papers found, falling back to random recommendation")
            return await _get_random_recommendation(current_user, db, paper_id)
        
        # Select top candidate
        recommended_paper = candidate_papers[0]
        logger.info(f"Recommended paper: {recommended_paper.id} ({recommended_paper.title})")
        
        return await read_paper(
            current_user=current_user,
            paper_id=recommended_paper.id,
            db=db,
            request=Request(scope={"type": "http"})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}", exc_info=True)
        # Fallback to random recommendation on error
        return await _get_random_recommendation(current_user, db, paper_id)


async def _get_random_recommendation(
    current_user: schemas.User,
    db: Session,
    exclude_paper_id: str
) -> PaperDetailResponse:
    """Fallback random recommendation"""
    all_papers = db.query(models.Paper)\
        .filter(models.Paper.id != exclude_paper_id)\
        .all()
    
    if not all_papers:
        raise HTTPException(
            status_code=404,
            detail="No papers available for recommendation"
        )
    
    import random
    recommended_paper = random.choice(all_papers)
    logger.info(f"Randomly recommended paper: {recommended_paper.id}")
    
    return await read_paper(
        current_user=current_user,
        paper_id=recommended_paper.id,
        db=db,
        request=Request(scope={"type": "http"})
    )


@app.post("/api/papers/{paper_id}/interact")
async def record_paper_interaction(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)],
    paper_id: str,
    db: SessionDep,
    action_type: str = "view"
):
    """Simplified interaction recording endpoint"""
    logger.info(f"Recording interaction for user {current_user.id} on paper {paper_id}")
    
    interaction = schemas.UserPaperInteractionCreate(
        user_id=current_user.id,
        paper_id=paper_id,
        action_type=action_type
    )
    
    try:
        crud.record_user_interaction(db=db, interaction=interaction)
        db.commit()
        return {"status": "success", "message": "Interaction recorded"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording interaction: {str(e)}")
        return {"status": "error", "message": "Failed to record interaction"}

# 调试接口 - 获取所有论文数据
@app.get("/test/papers")
async def debug_papers(db: SessionDep):
    papers = crud.get_papers(db, skip=0, limit=100)
    return {
        "count": len(papers),
        "papers": [
            {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract
            } for paper in papers
        ]
    }

# 调试接口 - 测试论文请求
@app.get("/api/debug/paper/{paper_id:path}")
async def debug_paper_request(paper_id: str):
    print(f"DEBUG - Received paper_id: {paper_id}")  # 确保输出到控制台
    return {"paper_id": paper_id, "status": "received"}

# 调试接口 - 添加测试论文数据
@app.post("/test/papers")
async def add_test_papers(db: SessionDep):
    test_papers = [
        {
            "title": "深度学习在自然语言处理中的应用",
            "authors": ["张三", "李四"],
            "abstract": "本文探讨了深度学习技术在NLP领域的最新进展",
            "keywords": ["深度学习", "NLP"],
            "published_date": "2023-01-01",
            "pdf_url": "http://example.com/paper1.pdf"
        },
        {
            "title": "基于Transformer的文本分类方法",
            "authors": ["王五", "赵六"],
            "abstract": "提出了一种改进的Transformer模型用于文本分类",
            "keywords": ["Transformer", "文本分类"],
            "published_date": "2023-02-01",
            "pdf_url": "http://example.com/paper2.pdf"
        }
    ]
    
    created = []
    try:
        for paper_data in test_papers:
            try:
                paper = schemas.PaperCreate(**paper_data)
                db_paper = crud.create_paper(db=db, paper=paper)
                created.append({
                    "id": db_paper.id,
                    "title": db_paper.title
                })
            except Exception as e:
                print(f"Error creating paper {paper_data['title']}: {str(e)}")
                raise
        
        db.commit()
        return {"message": "Test papers added", "papers": created}
    except Exception as e:
        db.rollback()
        print(f"Error in add_test_papers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
