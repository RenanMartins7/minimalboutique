from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Importa o modelo (do Canvas) e a sessão (do database.py)
from models import Product
from database import get_async_session

from opentelemetry import trace

# ===============================================================
# Configuração
# ===============================================================

tracer = trace.get_tracer(__name__)

# 1. Substituir Blueprint por APIRouter
products_router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

# ===============================================================
# Modelos Pydantic (Validação de Entrada/Saída)
# ===============================================================

# Modelo base para o produto (campos comuns)
class ProductBase(BaseModel):
    name: str
    price: float
    description: str | None = None
    image_url: str | None = None
    stock: int = 0

# Modelo para criar um novo produto
class ProductCreate(ProductBase):
    pass

# Modelo para a resposta (inclui o ID)
class ProductResponse(ProductBase):
    id: int

    # Permite que o Pydantic leia o modelo SQLAlchemy
    class Config:
        orm_mode = True 

# Modelo para atualizar estoque (reservar/liberar)
class StockPayload(BaseModel):
    quantity: int

# Modelo para requisição em lote
class BatchPayload(BaseModel):
    ids: List[int]

# ===============================================================
# ROTAS MIGRADAS
# ===============================================================

@products_router.get("/", response_model=List[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_async_session)):
    """
    Lista todos os produtos que têm estoque (stock > 0).
    """
    span = trace.get_current_span()
    
    # 2. Query assíncrona
    statement = select(Product).where(Product.stock > 0)
    result = await db.execute(statement)
    products = result.scalars().all()
    
    span.set_attribute("number.of.products", len(products))
    return products

@products_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Busca um produto específico pelo ID.
    """
    span = trace.get_current_span()
    
    # 3. db.get() é a forma assíncrona de .query.get()
    product = await db.get(Product, product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    span.set_attribute("product.id", product.id)
    return product

@products_router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Deleta um produto pelo ID.
    """
    span = trace.get_current_span()
    product = await db.get(Product, product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    span.set_attribute("product.id", product_id)
    
    # 4. Deletar e commitar
    await db.delete(product)
    await db.commit()
    
    return {"message": "Produto removido com sucesso"}

@products_router.post("/", response_model=ProductResponse, status_code=201)
async def add_product(
    payload: ProductCreate, # 5. Validação Pydantic
    db: AsyncSession = Depends(get_async_session)
):
    """
    Adiciona um novo produto ao banco de dados.
    """
    # 6. Cria o objeto do modelo SQLAlchemy a partir do Pydantic
    product = Product(**payload.model_dump())
    
    db.add(product)
    await db.commit()
    await db.refresh(product) # Recarrega o 'product' para obter o ID
    
    return product

# ===============================================================
# Rotas de Estoque (Reservar/Liberar)
# ===============================================================

@products_router.post("/{product_id}/reserve")
async def reserve_stock(
    product_id: int, 
    payload: StockPayload, # 5. Validação Pydantic
    db: AsyncSession = Depends(get_async_session)
):
    """
    Reserva uma quantidade do estoque de um produto.
    """
    span = trace.get_current_span()
    span.set_attribute("product.id", product_id)

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    quantity_to_reserve = payload.quantity
    if quantity_to_reserve <= 0:
        raise HTTPException(status_code=400, detail="Quantidade inválida")

    if product.stock >= quantity_to_reserve:
        product.stock -= quantity_to_reserve
        db.add(product) # Adiciona a instância modificada à sessão
        await db.commit()
        return {"message": "Estoque reservado com sucesso", "new_stock": product.stock}
    else:
        # Replicando a lógica do seu código Flask
        product.stock += 50000 
        db.add(product)
        await db.commit()
        # Nota: O original comentou o erro 409. Mantendo a lógica de adição.
        # Se você quiser que falhe, descomente a linha abaixo e remova as 2 acima.
        # raise HTTPException(status_code=409, detail="Estoque insuficiente")
        return {"message": "Estoque insuficiente, adicionado 50k", "new_stock": product.stock}


@products_router.post("/{product_id}/release")
async def release_stock(
    product_id: int, 
    payload: StockPayload, # 5. Validação Pydantic
    db: AsyncSession = Depends(get_async_session)
):
    """
    Libera (devolve) uma quantidade ao estoque de um produto.
    """
    span = trace.get_current_span()
    span.set_attribute("product.id", product_id)

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    quantity_to_release = payload.quantity
    if quantity_to_release <= 0:
        raise HTTPException(status_code=400, detail="Quantidade inválida")

    product.stock += quantity_to_release
    db.add(product) # Adiciona a instância modificada à sessão
    await db.commit()
    
    return {"message": "Estoque liberado com sucesso", "new_stock": product.stock}

@products_router.post("/batch", response_model=List[ProductResponse])
async def get_products_batch(
    payload: BatchPayload, # 5. Validação Pydantic
    db: AsyncSession = Depends(get_async_session)
):
    """
    Busca uma lista de produtos com base em uma lista de IDs.
    """
    span = trace.get_current_span()
    
    if not payload.ids:
        return []

    span.set_attribute("batch.request.size", len(payload.ids))

    # 7. Query assíncrona com 'in_'
    statement = select(Product).where(Product.id.in_(payload.ids))
    result = await db.execute(statement)
    products = result.scalars().all()
    
    span.set_attribute("batch.response.size", len(products))
    
    return products
