from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Request
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

# 添加基础日志配置
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
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


@app.get("/api/papers/{paper_id}", response_model=schemas.Paper)
async def read_paper(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        paper_id: int,
        db: SessionDep
):
    db_paper = crud.get_paper(db, paper_id=paper_id)
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return db_paper


@app.get("/api/papers/search/", response_model=schemas.PaperSearchResponse)
async def search_papers(
        current_user: Annotated[schemas.User, Depends(get_current_active_user)],
        query: str,
        db: SessionDep,
        limit: int = 10
):
    papers = crud.search_papers(db, query=query, limit=limit)
    return schemas.PaperSearchResponse(papers=papers, search_time=0.0)


@app.post("/api/papers/{paper_id}/interact")
async def record_paper_interaction(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)],
    paper_id: int,
    action_type: str,
    db: SessionDep
):
    db_paper = crud.get_paper(db, paper_id=paper_id)
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    interaction = schemas.UserPaperInteractionCreate(
        user_id=current_user.id,
        paper_id=paper_id,
        action_type=action_type
    )
    crud.record_user_interaction(db=db, interaction=interaction)
    return {"message": "Interaction recorded"}

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
