from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from opentelemetry import trace

gateway_router = APIRouter()

ORDERS_API_URL = "http://orders:5002/orders/"
PRODUCTS_API_URL = "http://products:5001/products/"
CHECKOUT_API_URL = "http://checkout:5003/checkout/"
PAYMENT_API_URL = "http://payment:5004/payment/"
CART_API_URL = "http://cart:5005/cart/"

tracer = trace.get_tracer(__name__)

# Dependência para autenticação
async def get_current_user(user_id: str | None = None):
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    return user_id


@gateway_router.get("/orders/")
async def get_user_orders(user_id: str = Depends(get_current_user), request: Request = None):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ORDERS_API_URL, params={"user_id": user_id}, cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de pedidos: {e}")


@gateway_router.get("/products/")
async def get_all_products():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PRODUCTS_API_URL)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de produtos: {e}")


@gateway_router.get("/products/{product_id}")
async def get_product_by_id(product_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PRODUCTS_API_URL}{product_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de produtos: {e}")


@gateway_router.post("/checkout/")
async def checkout_gateway(user_id: str = Depends(get_current_user), request: Request = None):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)

    async with httpx.AsyncClient() as client:
        try:
            cart_response = await client.get(CART_API_URL, params={"user_id": user_id}, cookies=request.cookies)
            if cart_response.status_code != 200:
                raise HTTPException(status_code=cart_response.status_code, detail="Não foi possível buscar os itens do carrinho")

            cart_items = cart_response.json()
            if not cart_items:
                raise HTTPException(status_code=400, detail="Carrinho vazio")

            payload = {"user_id": user_id, "cart_items": cart_items}
            checkout_response = await client.post(CHECKOUT_API_URL, json=payload, cookies=request.cookies)
            return JSONResponse(content=checkout_response.json(), status_code=checkout_response.status_code)

        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Erro de comunicação com os serviços: {e}")


@gateway_router.post("/payment/charge")
async def payment_gateway(payload: dict, user_id: str = Depends(get_current_user), request: Request = None):
    span = trace.get_current_span()
    span.set_attribute("user.id", user_id)
    payload['user_id'] = user_id

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{PAYMENT_API_URL}charge", json=payload, cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de pagamento: {e}")


@gateway_router.delete("/orders/{order_id}")
async def delete_order_gateway(order_id: int, request: Request = None):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{ORDERS_API_URL}{order_id}", cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de pedidos: {e}")


@gateway_router.api_route("/cart/", methods=["GET", "POST"])
async def cart_gateway(request: Request, user_id: str = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        try:
            if request.method == "POST":
                payload = await request.json()
                response = await client.post(CART_API_URL, json=payload, cookies=request.cookies)
            else:  # GET
                response = await client.get(CART_API_URL, cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de carrinho: {e}")


@gateway_router.delete("/cart/{item_id}")
async def delete_cart_item_gateway(item_id: int, request: Request, user_id: str = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{CART_API_URL}{item_id}", cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de carrinho: {e}")


@gateway_router.post("/cart/clear")
async def clear_cart_gateway(request: Request, user_id: str = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        try:
            payload = await request.json()
            response = await client.post(f"{CART_API_URL}clear", json=payload, cookies=request.cookies)
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao serviço de carrinho: {e}")
