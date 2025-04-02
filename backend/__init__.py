# Make backend a Python package
from .database import Base, SessionLocal
from .models import User, Paper, UserPaperInteraction
from .crud import (
    get_user, get_user_by_username, get_users, create_user,
    get_paper, get_papers, create_paper, search_papers
)
from .schemas import UserCreate, PaperCreate
from .security import verify_password, get_password_hash

__all__ = [
    'Base', 'SessionLocal',
    'User', 'Paper', 'UserPaperInteraction',
    'get_user', 'get_user_by_username', 'get_users', 'create_user',
    'get_paper', 'get_papers', 'create_paper', 'search_papers',
    'UserCreate', 'PaperCreate',
    'verify_password', 'get_password_hash'
]
