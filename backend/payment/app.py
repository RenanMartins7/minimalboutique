import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importar o router (que vamos migrar a seguir)
from routes.payment import payment_router 
from telemetry import configure_telemetry # Assumindo que telemetry.py existe

# Nome do serviço para OpenTelemetry
SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de 'lifespan' para rodar código no startup e shutdown.
    
    Nota: Este serviço não tem 'init_db()' pois não possui banco próprio.
    """
    # Código de Startup
    print("INFO:     Iniciando o serviço de Pagamento...")
    
    # Configurar OpenTelemetry
    configure_telemetry(app, SERVICE_NAME) 
    print(f"INFO:     OpenTelemetry configurado para o serviço: {SERVICE_NAME}")
    
    yield
    
    # Código de Shutdown (se necessário)
    print("INFO:     Desligando o serviço de Pagamento...")

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

# Incluir o roteador das rotas de pagamento
# (O arquivo 'routes/payment.py' será nosso próximo passo)
app.include_router(payment_router)

@app.get("/health")
def health_check():
    """
    Endpoint simples de verificação de saúde.
    """
    return {"status": "healthy"}
