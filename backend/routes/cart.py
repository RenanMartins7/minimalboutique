import requests
from flask import Blueprint, request, jsonify, session
from models import CartItem
from database import db

cart_bp = Blueprint('cart', __name__, url_prefix = '/cart')

PRODUCTS_API_URL = "http://products:5001/products"

@cart_bp.route('/', methods = ['POST'])
def add_to_cart():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Usuário não encontrado'}), 401


    data = request.json
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    try:
        reserve_response = requests.post(f"{PRODUCTS_API_URL}/{product_id}/reserve", json={'quantity': quantity})
        if reserve_response.status_code != 200:
            error_data = reserve_response.json()
            return jsonify({"error": error_data.get("error", "Não foi possível reservar o produto")}), reserve_response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Erro de comunicação com o serviço de produtos', 'details': str(e)}), 503

    item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()

    if item:
        item.quantity += quantity 
    
    else: 
        item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(item)
    
    db.session.commit()
    return jsonify({"message": "Item adicionado ao carrinho"}), 201


@cart_bp.route('/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({"error": "Item não encontrado"}), 404

    product_id = item.product_id
    quantity_to_release = item.quantity
    db.session.delete(item)
    db.session.commit()

    try:
        requests.post(f"{PRODUCTS_API_URL}/{product_id}/release", json={'quantity': quantity_to_release})
    
    except requests.exceptions.RequestException as e:
        print(f"ERRO CRÍTICO: Falha ao liberar estoque para product_id {product_id}. Detalhes: {e}")
    return jsonify({"message": "Item removido"}), 200

@cart_bp.route('/clear', methods=['POST'])
def clear_cart():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id é obrigatório"}), 400
    
    try:
        CartItem.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({"message": "Carrinho limpo com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Falha ao limpar o carrinho", "details": str(e)}), 500

@cart_bp.route('/', methods = ['GET'])
def get_cart():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Usuário não encontrado'}), 401

    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    result = []
    for item in cart_items:
        try:
            product_response = requests.get(f'http://products:5001/products/{item.product_id}')
            if product_response.status_code == 200:
                product_data = product_response.json()
                result.append({
                    "id" : item.id,
                    "product_id": item.product_id,
                    "product_name": product_data.get('name'),
                    "quantity": item.quantity,
                    "price": product_data.get('price')
                })
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Erro ao buscar dados do produto {item.product_id}'}), 503

    return jsonify(result)

