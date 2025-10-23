from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import auth_router
from routes.gateway import gateway_router
from database import init_db, engine  # engine para telemetry
from telemetry import configure_telemetry
import asyncio
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(gateway_router)

# Inicialização do banco assíncrono
async def on_startup():
    await init_db()

app.add_event_handler("startup", on_startup)

# Configuração de telemetria
configure_telemetry(app, "backend", db_engine=engine)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
