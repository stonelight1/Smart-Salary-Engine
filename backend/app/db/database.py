"""SQLAlchemy 数据库连接"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "sse.db"

# 确保 data 目录存在
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 多线程支持
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """创建所有表"""
    import app.models  # noqa: F401 确保模型被导入
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖 - 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
