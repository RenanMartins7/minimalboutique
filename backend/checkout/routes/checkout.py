import os
import asyncio  # Importado para 'asyncio.gather'
import httpx      # 1. Substituído 'requests' por 'httpx'
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# 2. Substituído Blueprint por APIRouter
checkout_router = APIRouter(
    prefix="/checkout",
    tags=["Checkout"]
)

# URLs dos serviços lidas do ambiente
PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "http://products:5001/products/")
ORDERS_API_URL = os.getenv("ORDERS_API_URL", "http://orders:5002/orders/")

# 3. Cliente httpx assíncrono global para reuso de conexão
client = httpx.AsyncClient()

# ===============================================================
# Modelos Pydantic para Validação de Entrada
# ===============================================================

class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CheckoutPayload(BaseModel):
    user_id: int
    cart_items: List[CartItemBase]

# ===============================================================
# Rotas
# ===============================================================

async def fetch_product_price(item: CartItemBase, span):
    """
    Busca um único produto de forma assíncrona e retorna os dados
    necessários para o pedido ou levanta um erro.
    """
    try:
        product_response = await client.get(f"{PRODUCTS_API_URL}{item.product_id}")
        
        if product_response.status_code != 200:
            # Produto não encontrado ou serviço de produtos falhou
            raise HTTPException(status_code=404, detail=f"Produto com ID {item.product_id} não encontrado")
        
        product_data = product_response.json()
        price = product_data.get('price')
        
        if price is None:
             raise HTTPException(status_code=500, detail=f"Produto com ID {item.product_id} não tem preço definido")

        span.set_attribute(f"product.{item.product_id}.price:", price)
        span.set_attribute(f"product.{item.product_id}.quantity", item.quantity)
        
        # Retorna o total do item e o payload para a ordem
        item_total = price * item.quantity
        order_item_payload = {
            "product_id": item.product_id, 
            "quantity": item.quantity, 
            "price": price
        }
        return (item_total, order_item_payload)

    except httpx.RequestError:
        # Erro de rede/conexão
        raise HTTPException(status_code=503, detail="Erro de comunicação com o serviço de produtos")


@checkout_router.post('/', status_code=201)
async def process_checkout(payload: CheckoutPayload): # 4. Validação Pydantic
    
    user_id = payload.user_id
    cart_items = payload.cart_items

    if not cart_items:
        raise HTTPException(status_code=400, detail="Carrinho está vazio")

    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)

    total = 0
    order_items_payload = []

    # 5. Otimização: Criar uma lista de 'tarefas' para buscar todos os produtos em paralelo
    tasks = [fetch_product_price(item, span) for item in cart_items]
    
    # 6. Executar todas as tarefas concorrentemente
    try:
        results = await asyncio.gather(*tasks)
    except HTTPException as e:
        # Se qualquer tarefa falhar (ex: produto não encontrado), 'gather' vai levantar o erro
        raise e # Re-levanta o erro (ex: 404, 503) para o cliente

    # 7. Processar os resultados (se todos foram bem-sucedidos)
    for item_total, item_payload in results:
        total += item_total
        order_items_payload.append(item_payload)

    # 8. Criar o pedido com status 'pending'
    if total > 0:
        span.set_attribute("total", total)
        order_payload = {"user_id": user_id, "total": total, "items": order_items_payload}
        
        try:
            order_response = await client.post(ORDERS_API_URL, json=order_payload)
            
            if order_response.status_code != 201:
                # 9. Tratamento de erro FastAPI
                raise HTTPException(
                    status_code=order_response.status_code, 
                    detail="Falha ao criar o pedido pendente"
                )
            
            # 10. Retorna a resposta do serviço de pedidos diretamente
            return order_response.json()
        
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Erro de comunicação com o serviço de pedidos")
    
    raise HTTPException(status_code=400, detail="Não foi possível calcular o total")
