from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_async_session
from models import User
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

auth_router = APIRouter(prefix="/auth")


# Dependência para obter usuário autenticado (simula session)
async def get_current_user(request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    return int(user_id)


@auth_router.post("/register")
async def register(data: dict, db: AsyncSession = Depends(get_async_session)):
    email = data.get("email")
    password = data.get("password")
    span = trace.get_current_span()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")

    span.set_attribute("email", email)
    span.set_attribute("password", password)

    # Verifica se usuário já existe
    result = await db.execute(select(User).where(User.username == email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    # Cria novo usuário
    user = User(username=email, password=password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return JSONResponse(content={"message": "Usuário criado com sucesso"}, status_code=201)


@auth_router.post("/login")
async def login(data: dict, db: AsyncSession = Depends(get_async_session)):
    span = trace.get_current_span()
    result = await db.execute(
        select(User).where(User.username == data.get("email"), User.password == data.get("password"))
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    span.set_attribute("user.id", user.id)
    span.set_attribute("email", data["email"])

    # No lugar de session, retornamos user_id no header ou token (simples aqui)
    response = JSONResponse(content={"message": "Login realizado com sucesso"})
    response.headers["X-User-Id"] = str(user.id)
    return response


@auth_router.post("/logout")
async def logout(user_id: int = Depends(get_current_user)):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    # No FastAPI, logout pode ser feito no frontend removendo o token/header
    return JSONResponse(content={"message": "Logout realizado com sucesso"})


@auth_router.get("/user")
async def get_user(user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        return JSONResponse(content=None)
    return JSONResponse(content={"email": user.username})
