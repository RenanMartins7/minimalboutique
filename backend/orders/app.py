import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importar o router (que vamos migrar a seguir)
from routes.orders import orders_router
from telemetry import configure_telemetry # Assumindo que telemetry.py existe
from database import init_db, engine # Importa a função de inicialização do DB

# Nome do serviço para OpenTelemetry
SERVICE_NAME = os.getenv("SERVICE_NAME", "orders-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de 'lifespan' para rodar código no startup e shutdown.
    """
    # Código de Startup
    print("INFO:     Iniciando o serviço de Pedidos...")
    
    # Configurar OpenTelemetry
    configure_telemetry(app, SERVICE_NAME, engine)
    print(f"INFO:     OpenTelemetry configurado para o serviço: {SERVICE_NAME}")
    
    # Inicializar o banco de dados (criar tabelas se não existirem)
    await init_db()
    print("INFO:     Banco de dados inicializado.")
    
    yield
    
    # Código de Shutdown (se necessário)
    print("INFO:     Desligando o serviço de Pedidos...")

# Criar a aplicação FastAPI
app = FastAPI(lifespan=lifespan)

# Configurar CORS (Middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens (ajuste para produção)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

# Incluir o roteador das rotas de pedidos
# (O arquivo 'routes/orders.py' será nosso próximo passo)
app.include_router(orders_router)

@app.get("/health")
def health_check():
    """
    Endpoint simples de verificação de saúde.
    """
    return {"status": "healthy"}
