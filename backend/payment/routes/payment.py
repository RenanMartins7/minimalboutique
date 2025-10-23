import os
import httpx  # 1. Substituir 'requests' por 'httpx'
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from opentelemetry import trace

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Substituir Blueprint por APIRouter
payment_router = APIRouter(
    prefix="/payment",
    tags=["Payment"]
)

# URLs dos serviços lidas do ambiente
ORDERS_API_URL = os.getenv("ORDERS_API_URL", "http://orders:5002/orders")
# O endpoint de limpar carrinho agora é no serviço 'cart', não no 'backend' (gateway)
CART_API_URL = os.getenv("CART_API_URL", "http://cart:5002/cart/clear")


tracer = trace.get_tracer(__name__)

# 3. Cliente httpx assíncrono global para reuso de conexão
client = httpx.AsyncClient()

# ===============================================================
# Modelos Pydantic para Validação de Entrada
# ===============================================================

class PaymentPayload(BaseModel):
    order_id: int
    user_id: int

class CartClearPayload(BaseModel):
    user_id: int

# ===============================================================
# Rotas
# ===============================================================

@payment_router.post('/charge')
async def charge(payload: PaymentPayload): # 4. Validação Pydantic
    
    span = trace.get_current_span()
    order_id = payload.order_id
    user_id = payload.user_id

    span.set_attribute("order.id", order_id)
    span.set_attribute("user.id", user_id)
    
    logger.info(f"Pagamento para o pedido {order_id} processado com sucesso.")

    # 1. Confirmar o pagamento no serviço de Pedidos
    try:
        confirm_url = f"{ORDERS_API_URL}/{order_id}/confirm_payment"
        # 5. Usar 'httpx' e 'await'
        confirm_response = await client.post(confirm_url)

        if confirm_response.status_code != 200:
            logger.error(f"ERRO: Falha ao confirmar o pagamento para o pedido {order_id}. Status: {confirm_response.status_code}")
            span.set_attribute("payment.status", "declined")
            # 6. Usar HTTPException para erros
            raise HTTPException(
                status_code=confirm_response.status_code,
                detail="Falha ao atualizar o status do pedido"
            )
        
        span.set_attribute("payment.status", "paid")
    
    except httpx.RequestError as e:
        logger.error(f"ERRO: Não foi possível conectar ao serviço do pedido: {e}")
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao serviço do pedido")

    # 2. Limpar o carrinho (operação "fire-and-forget", não crítica)
    try:
        # 6. O 'cart' service (que migramos) espera um JSON no corpo
        cart_payload = CartClearPayload(user_id=user_id)
        clear_cart_response = await client.post(CART_API_URL, json=cart_payload.dict())
        
        if clear_cart_response.status_code != 200:
            logger.warning(f"AVISO: Não foi possível limpar o carrinho do usuário {user_id}. Status: {clear_cart_response.status_code}")
        else:
            logger.info(f"Carrinho do usuário {user_id} limpo com sucesso.")
            
    except httpx.RequestError as e:
        # Esta falha não deve interromper o fluxo, apenas registramos.
        logger.warning(f"AVISO: Não foi possível conectar ao serviço de carrinho para limpar: {e}")
    
    # 7. Retornar dicionário (FastAPI converte para JSON)
    return {"message": "Pagamento bem sucedido e pedido confirmado"}
