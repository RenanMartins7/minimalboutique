import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importar a função de inicialização do DB e o router (que ainda vamos criar)
from database import init_db, engine
from routes.cart import cart_router # Vamos migrar 'routes/cart.py' a seguir
from telemetry import configure_telemetry # Assumindo que telemetry.py existe

# Nome do serviço para OpenTelemetry
SERVICE_NAME = os.getenv("SERVICE_NAME", "cart-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de 'lifespan' para rodar código no startup e shutdown.
    """
    # Código de Startup
    print("INFO:     Iniciando o serviço de Carrinho...")
    await init_db()
    print("INFO:     Banco de dados do Carrinho inicializado.")
    
    # Configurar OpenTelemetry
    # (Ajuste 'setup_telemetry' se a assinatura mudou de Flask para FastAPI)
    configure_telemetry(app, SERVICE_NAME, engine) 
    print(f"INFO:     OpenTelemetry configurado para o serviço: {SERVICE_NAME}")
    
    yield
    
    # Código de Shutdown (se necessário)
    print("INFO:     Desligando o serviço de Carrinho...")

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

# Incluir o roteador das rotas do carrinho
# (O arquivo 'routes/cart.py' será nosso próximo passo)
app.include_router(cart_router)

@app.get("/health")
def health_check():
    """
    Endpoint simples de verificação de saúde.
    """
    return {"status": "healthy"}
