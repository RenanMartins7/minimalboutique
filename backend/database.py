import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/meubanco"
)

# Cria engine assíncrona - removendo parâmetros de pool síncronos
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,  # opcional, bom para SQLAlchemy 2.x
    pool_size=5,
    max_overflow=155,
    connect_args={"timeout":120}
)

# Session assíncrona
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
