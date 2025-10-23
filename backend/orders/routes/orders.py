import os
import httpx
import datetime
import asyncio
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Importa os modelos (já migrados)
from models import Order, OrderItem
# Importa a sessão e o 'get_db' (já migrados)
from database import get_async_session

from opentelemetry import trace

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================================================
# Configuração
# ===============================================================

# 1. Substituir Blueprint por APIRouter
orders_router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

tracer = trace.get_tracer(__name__)

# URL do serviço de produtos (lida do ambiente)
PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "http://products:5001/products")

# 2. Cliente HTTP assíncrono global
client = httpx.AsyncClient(timeout=3.0)

# ===============================================================
# Cache (Lógica de cache mantida, agora usada por httpx)
# ===============================================================
product_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutos

def get_product_from_cache(product_id):
    """Retorna produto do cache se ainda for válido"""
    entry = product_cache.get(product_id)
    if not entry:
        return None
    if (datetime.datetime.now() - entry["timestamp"]).total_seconds() > CACHE_TTL_SECONDS:
        del product_cache[product_id]
        return None
    return entry["data"]

async def fetch_product(product_id: int):
    """
    Busca o produto no cache ou via requisição HTTP assíncrona.
    Retorna (product_data, was_cached)
    """
    cached = get_product_from_cache(product_id)
    if cached:
        return cached, True

    try:
        # 3. Substituir requests.get por client.get
        response = await client.get(f"{PRODUCTS_API_URL}/{product_id}")
        
        if response.status_code == 200:
            product_data = response.json()
            product_cache[product_id] = {
                "data": product_data,
                "timestamp": datetime.datetime.now()
            }
            return product_data, False
        else:
            logger.warning(f"[WARN] Falha ao buscar produto {product_id}: {response.status_code}")
            return None, False
    except httpx.RequestError as e:
        logger.error(f"[ERRO] Requisição ao serviço de produtos falhou: {e}")
        return None, False

# ===============================================================
# Modelos Pydantic (Validação de Entrada/Saída)
# ===============================================================

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: float
    price: float

class OrderCreate(BaseModel):
    user_id: int
    total: float
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    product_name: str
    quantity: float
    price: float

class OrderResponse(BaseModel):
    id: int
    total: float
    status: str
    items: List[OrderItemResponse]

# ===============================================================
# CREATE ORDER
# ===============================================================
@orders_router.post('/', status_code=201)
async def create_order(
    payload: OrderCreate,  # 4. Validação Pydantic
    db: AsyncSession = Depends(get_async_session) # 5. Injeção de sessão Async
):
    span = trace.get_current_span()
    span.set_attribute("user.id", payload.user_id)
    span.set_attribute("total", payload.total)
    span.set_attribute("number.of.items", len(payload.items))

    # 6. Criar objetos SQLAlchemy (não mais db.Model)
    order = Order(user_id=payload.user_id, total=payload.total, status='pending')
    
    # 7. Usar 'await' para operações de DB
    db.add(order)
    await db.flush()  # Precisamos do ID do pedido (order.id) para os itens
    span.set_attribute("order.id", order.id)

    order_items = []
    for item_data in payload.items:
        order_items.append(
            OrderItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price=item_data.price
            )
        )
    
    db.add_all(order_items)
    await db.commit()
    
    return {'message': 'Pedido criado com sucesso', 'order_id': order.id}

# ===============================================================
# GET ORDERS (Otimizado para chamadas de rede paralelas)
# ===============================================================
@orders_router.get('/', response_model=List[OrderResponse])
async def get_orders(
    user_id: int,  # 8. Parâmetro de query tipado
    db: AsyncSession = Depends(get_async_session)
):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)

    # 9. Query assíncrona
    # O 'lazy="selectin"' no models.py garante que os 'items' sejam carregados
    # de forma eficiente (uma query extra para todos os itens).
    statement = select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())
    result = await db.execute(statement)
    orders = result.scalars().all()
    span.set_attribute("number.of.orders", len(orders))

    if not orders:
        return []

    # 10. Otimização N+1: Buscar todos os produtos em paralelo
    all_product_ids = {item.product_id for order in orders for item in order.items}
    tasks = [fetch_product(pid) for pid in all_product_ids]
    product_results = await asyncio.gather(*tasks)

    # Criar um mapa de ID -> (product_data, was_cached)
    product_map = dict(zip(all_product_ids, product_results))
    
    cache_hits = sum(1 for _, was_cached in product_map.values() if was_cached)
    cache_misses = len(all_product_ids) - cache_hits

    # Montar a resposta
    response_list = []
    for order in orders:
        items_data = []
        for item in order.items:
            product_data, _ = product_map.get(item.product_id, (None, False))
            
            product_name = "Produto não encontrado"
            if product_data:
                product_name = product_data.get('name', 'Nome não encontrado')

            items_data.append(
                OrderItemResponse(
                    product_name=product_name,
                    quantity=item.quantity,
                    price=item.price
                )
            )

        response_list.append(
            OrderResponse(
                id=order.id,
                total=order.total,
                status=order.status,
                items=items_data
            )
        )

    span.set_attribute("cache.hits", cache_hits)
    span.set_attribute("cache.misses", cache_misses)

    return response_list

# ===============================================================
# CONFIRM PAYMENT
# ===============================================================
@orders_router.post('/{order_id}/confirm_payment')
async def confirm_payment(
    order_id: int,  # 11. Parâmetro de rota tipado
    db: AsyncSession = Depends(get_async_session)
):
    span = trace.get_current_span()

    # 12. db.get() é a forma assíncrona de .query.get()
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    span.set_attribute("order.id", order.id)
    
    order.status = 'paid'
    span.set_attribute("payment.status", "paid")
    
    db.add(order) # Adiciona a instância modificada à sessão
    await db.commit()

    return {"message": "Pagamento do pedido confirmado com sucesso"}

# ===============================================================
# DELETE ORDER (Otimizado para chamadas de rede paralelas)
# ===============================================================
@orders_router.delete('/{order_id}')
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    span = trace.get_current_span()

    # 13. Precisamos dos 'items' para liberar o estoque,
    # então usamos 'select' (que ativará o 'selectin' do modelo).
    statement = select(Order).where(Order.id == order_id)
    result = await db.execute(statement)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    span.set_attribute("order.id", order.id)
    
    if order.status != 'pending':
        raise HTTPException(status_code=400, detail="Apenas pedidos pendentes podem ser cancelados")
    
    # 14. Otimização N+1: Liberar estoque em paralelo
    tasks = []
    for item in order.items:
        release_url = f"{PRODUCTS_API_URL}/{item.product_id}/release"
        tasks.append(client.post(release_url, json={'quantity': item.quantity}))
    
    try:
        release_results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in release_results:
            if isinstance(res, Exception):
                logger.error(f"ERRO CRÍTICO: Falha ao liberar estoque (durante delete): {res}")
            elif res.status_code != 200:
                 logger.error(f"ERRO CRÍTICO: Falha ao liberar estoque (status {res.status_code}): {res.text}")
    except Exception as e:
         logger.error(f"ERRO CRÍTICO: Exceção ao liberar estoque: {e}")
    
    # 15. Deletar e commitar
    await db.delete(order)
    await db.commit()

    return {"message": "Pedido cancelado com sucesso"}