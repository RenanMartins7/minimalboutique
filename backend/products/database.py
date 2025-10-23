import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Lê a URL do banco de dados do ambiente
# Garanta que esta variável de ambiente inclua '+asyncpg'
# O nome do banco (ex: meubanco_products) deve ser o correto para este serviço.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/meubanco" 
)

# Cria engine assíncrona
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,        # Mínimo de conexões no pool
    max_overflow=144,    # Conexões extras permitidas
    connect_args={"timeout": 120}  # Timeout para conexão individual
)

# Session assíncrona
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_async_session() -> AsyncSession:
    """
    Dependência do FastAPI para injetar uma sessão de DB em rotas.
    """
    async with async_session() as session:
        yield session

async def init_db():
    """
    Inicializa o banco de dados, criando todas as tabelas
    definidas nos modelos que herdam de 'Base'.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
