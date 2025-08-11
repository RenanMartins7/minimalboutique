from flask import Blueprint, jsonify, session
from models import CartItem # Order e OrderItem não são mais necessários aqui
from database import db
import requests

checkout_bp = Blueprint('checkout', __name__, url_prefix = '/checkout')

@checkout_bp.route('/', methods = ['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Faça o login para finalizar a sua compra'}), 401

    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return jsonify({"error": "Carrinho Vazio"}), 400

    total = 0
    order_items_payload = []

    # 1. Validar produtos e calcular o total
    for item in cart_items:
        try:
            product_response = requests.get(f'http://products:5001/products/{item.product_id}')
            if product_response.status_code != 200:
                return jsonify({"error": f"Produto com ID {item.product_id} não encontrado"}), 404

            product_data = product_response.json()
            price = product_data.get('price')
            total += price * item.quantity

            order_items_payload.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": price
            })

        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Erro ao comunicar com o serviço de produtos", "details": str(e)}), 503

    # 2. Enviar o pedido para o serviço de 'orders'
    if total > 0:
        order_payload = {
            "user_id": user_id,
            "total": total,
            "items": order_items_payload
        }
        try:
            order_response = requests.post('http://orders:5002/orders/', json=order_payload)
            if order_response.status_code != 201:
                return jsonify({"error": "Falha ao criar o pedido no serviço de pedidos", "details": order_response.text}), 500

            # 3. Limpar o carrinho após o sucesso
            CartItem.query.filter_by(user_id=user_id).delete()
            db.session.commit()

            return jsonify({"message": "Compra finalizada", "order_data": order_response.json(), "total": total}), 200

        except requests.exceptions.RequestException as e:
             return jsonify({"error": "Erro ao comunicar com o serviço de pedidos", "details": str(e)}), 503
    else:
        return jsonify({"error": "Não foi possível calcular o total do pedido"}), 400