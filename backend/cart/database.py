import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Definir a Base declarativa para os modelos do 'cart'
Base = declarative_base()

# 2. Usar a mesma variável de ambiente DATABASE_URL (com driver asyncpg)
#    O microsserviço 'cart' se conectará ao mesmo banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/meubanco"
)

# 3. Criar o engine assíncrono com os parâmetros de pool corretos
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,        # Mínimo de conexões no pool
    max_overflow=155,  # Conexões extras permitidas (ajuste conforme necessário)
    connect_args={"timeout": 120}  # Timeout para cada conexão individual
)

# 4. Criar a fábrica de sessões assíncronas
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# 5. Criar a dependência do FastAPI para injetar a sessão
async def get_async_session() -> AsyncSession:
    """
    Dependência do FastAPI para obter uma sessão de banco de dados.
    """
    async with async_session() as session:
        yield session

# 6. Criar a função de inicialização do DB (para ser chamada no startup)
async def init_db():
    """
    Cria as tabelas do banco de dados (se não existirem).
    """
    async with engine.begin() as conn:
        # Importa os modelos aqui para garantir que eles sejam registrados na Base
        import models  
        await conn.run_sync(Base.metadata.create_all)
