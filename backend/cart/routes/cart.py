import datetime
import os
import httpx  # 1. Substituído 'requests' por 'httpx' (assíncrono)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session  # 2. Importa a nova dependência de sessão
from models import CartItem  # 3. Importa o modelo do 'models.py' corrigido

# 4. OpenTelemetry (deve funcionar da mesma forma)
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

# 5. Criar APIRouter em vez de Blueprint
cart_router = APIRouter(
    prefix="/cart",
    tags=["Cart"]
)

# 6. URL do serviço de produtos (lida do ambiente)
PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "http://products:5001/products")

# ===============================================================
# Cache local simples (convertido para usar httpx)
# ===============================================================
product_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutos

# 7. Cliente HTTP assíncrono global (melhor performance com pool de conexões)
client = httpx.AsyncClient(timeout=3.0)

async def get_product_from_cache(product_id):
    """Retorna produto do cache se ainda for válido"""
    entry = product_cache.get(product_id)
    if not entry:
        return None
    if (datetime.datetime.now() - entry["timestamp"]).total_seconds() > CACHE_TTL_SECONDS:
        del product_cache[product_id]
        return None
    return entry["data"]

async def fetch_product(product_id: int):
    """Busca produto do cache ou do serviço de produtos (agora assíncrono)"""
    cached = await get_product_from_cache(product_id)
    if cached:
        return cached, True  # True = veio do cache

    try:
        # 8. Usa o cliente httpx global (assíncrono)
        response = await client.get(f"{PRODUCTS_API_URL}/{product_id}")
        
        if response.status_code == 200:
            product_data = response.json()
            product_cache[product_id] = {
                "data": product_data,
                "timestamp": datetime.datetime.now()
            }
            return product_data, False
        else:
            print(f"[WARN] Falha ao buscar produto {product_id}: {response.status_code}")
            return None, False
    except httpx.RequestError as e:
        print(f"[ERRO] Falha ao buscar produto {product_id}: {e}")
        return None, False

# ===============================================================
# Modelos Pydantic (Validação de Body)
# ===============================================================

class CartItemAdd(BaseModel):
    user_id: int  # 9. user_id agora vem no body
    product_id: int
    quantity: int = 1

class CartClear(BaseModel):
    user_id: int # 9. user_id agora vem no body

# ===============================================================
# ADD TO CART
# ===============================================================
@cart_router.post('/', status_code=201)
async def add_to_cart(
    item_data: CartItemAdd,  # 10. Validação automática com Pydantic
    db: AsyncSession = Depends(get_async_session) # 11. Injeção da sessão
):
    user_id = item_data.user_id
    product_id = item_data.product_id
    quantity = item_data.quantity

    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    span.set_attribute("product.id", product_id)
    span.set_attribute("quantity", quantity)

    try:
        # 12. Chamada assíncrona para reservar o produto
        async with httpx.AsyncClient() as reserve_client:
            reserve_response = await reserve_client.post(
                f"{PRODUCTS_API_URL}/{product_id}/reserve", 
                json={'quantity': quantity}
            )
        
        if reserve_response.status_code != 200:
            error_data = reserve_response.json()
            raise HTTPException(
                status_code=reserve_response.status_code,
                detail=error_data.get("error", "Não foi possível reservar o produto")
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro de comunicação com o serviço de produtos: {e}"
        )

    # 13. Query assíncrona com SQLAlchemy Core
    stmt = select(CartItem).where(
        CartItem.user_id == user_id, 
        CartItem.product_id == product_id
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(item)
    
    await db.commit() # 14. Commit assíncrono
    
    span.set_attribute("stock.items", item.quantity)
    return {"message": "Item adicionado ao carrinho"}


# ===============================================================
# REMOVE ITEM FROM CART
# ===============================================================
@cart_router.delete('/{item_id}')
async def remove_from_cart(
    item_id: int, 
    user_id: int = Query(...), # 15. user_id vem como Query Param (?user_id=123)
    db: AsyncSession = Depends(get_async_session)
):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    
    # 16. Query assíncrona para encontrar o item
    stmt = select(CartItem).where(
        CartItem.id == item_id, 
        CartItem.user_id == user_id
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    product_id = item.product_id
    quantity_to_release = item.quantity
    
    await db.delete(item) # 17. Delete assíncrono
    await db.commit()     # 18. Commit assíncrono

    span.set_attribute("product.id", product_id)
    span.set_attribute("deleted.quantity", quantity_to_release)

    try:
        # 19. Liberação de estoque assíncrona (best-effort, não bloqueia o usuário)
        async with httpx.AsyncClient() as release_client:
            await release_client.post(
                f"{PRODUCTS_API_URL}/{product_id}/release", 
                json={'quantity': quantity_to_release}
            )
    except httpx.RequestError as e:
        # Loga o erro crítico, mas não retorna erro ao usuário
        print(f"ERRO CRÍTICO: Falha ao liberar estoque para product_id {product_id}. Detalhes: {e}")

    return {"message": "Item removido"}


# ===============================================================
# CLEAR CART
# ===============================================================
@cart_router.post('/clear')
async def clear_cart(
    data: CartClear, # 20. Usa Pydantic model para pegar user_id
    db: AsyncSession = Depends(get_async_session)
):
    user_id = data.user_id
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    
    try:
        # 21. Delete assíncrono em massa
        stmt = delete(CartItem).where(CartItem.user_id == user_id)
        await db.execute(stmt)
        await db.commit()
        return {"message": "Carrinho limpo com sucesso"}
    except Exception as e:
        await db.rollback() # 22. Rollback assíncrono
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao limpar o carrinho: {e}"
        )


# ===============================================================
# GET CART (agora com cache local)
# ===============================================================
@cart_router.get('/', response_model=List) # Melhora a documentação (define tipo de resposta)
async def get_cart(
    user_id: int = Query(...), # 23. user_id vem como Query Param
    db: AsyncSession = Depends(get_async_session)
):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)

    # 24. Query assíncrona
    stmt = select(CartItem).where(CartItem.user_id == user_id)
    result = await db.execute(stmt)
    cart_items = result.scalars().all() # .scalars() pega a primeira coluna (o obj CartItem)

    if not cart_items:
        return []

    product_ids = [item.product_id for item in cart_items]
    span.set_attribute("cart.product.count", len(product_ids))

    result_list = []
    cache_hits = 0
    cache_misses = 0

    for item in cart_items:
        # 25. Chamada assíncrona ao fetch_product
        product_data, from_cache = await fetch_product(item.product_id)
        
        if from_cache:
            cache_hits += 1
        else:
            cache_misses += 1

        if product_data:
            result_list.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product_data.get('name'),
                "quantity": item.quantity,
                "price": product_data.get('price')
            })
        else:
            result_list.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": "Produto não encontrado",
                "quantity": item.quantity,
                "price": None
            })

    span.set_attribute("cache.hits", cache_hits)
    span.set_attribute("cache.misses", cache_misses)

    # 26. FastAPI converte a lista/dicionário para JSON
    return result_list
