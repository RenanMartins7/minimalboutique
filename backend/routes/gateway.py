from flask import Blueprint, jsonify, session, request
from models import CartItem
import requests



gateway_bp = Blueprint('gateway', __name__)

ORDERS_API_URL = "http://orders:5002/orders/"
PRODUCTS_API_URL = "http://products:5001/products/"
CHECKOUT_API_URL = "http://checkout:5003/checkout/"
PAYMENT_API_URL = "http://payment:5004/payment/"

@gateway_bp.route('/orders/', methods=['GET'])
def get_user_orders():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error":"Usuário não autenticado"}), 401

    try:
        response = requests.get(ORDERS_API_URL, params={'user_id': user_id})
        return response.content, response.status_code, response.headers.items()
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível conectar ao serviço de pedidos", "details:":str(e)}), 503

@gateway_bp.route('/products/', methods=['GET'])
def get_all_products():
    try:
        response = requests.get(PRODUCTS_API_URL)
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível conectar ao serviço de produtos", "details:":str(e)}), 503

@gateway_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    try:
        response = requests.get(f"{PRODUCTS_API_URL}{product_id}")
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestExceptions as e:
        return jsonify({"error":"Não foi possível conectar ao serviço de produtos", "details:":str(e)}), 503

@gateway_bp.route('/checkout/', methods=['POST'])
def checkout_gateway():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 401
    
    cart_items_obj = CartItem.query.filter_by(user_id=user_id).all()
    if not cart_items_obj:
        return jsonify({"error": "Carrinho vazio"}), 400
    
    cart_items_list = [
        {"product_id": item.product_id, "quantity": item.quantity}
        for item in cart_items_obj
    ]

    payload = {
        "user_id": user_id,
        "cart_items": cart_items_list
    }

    try:
        response = requests.post(CHECKOUT_API_URL, json=payload)
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível conectar ao serviço de checkout", "details": str(e)}), 503


@gateway_bp.route('/payment/charge', methods=['POST'])
def payment_gateway():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 401

    payload = request.json
    payload['user_id'] = user_id

    try:
        response = requests.post(f"{PAYMENT_API_URL}charge", json=payload)
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível conectar ao serviço de pagamento"}), 503