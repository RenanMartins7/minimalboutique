from flask import Blueprint, jsonify, session
from models import Order
from database import db
import requests

orders_bp = Blueprint('orders', __name__, url_prefix = '/orders')

@orders_bp.route('/', methods=['GET'])
def get_orders():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error':'Usuário não encontrado'}), 401

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()
    result = []

    for order in orders:
        items_data = []
        for item in order.items:
            try:
                # Faz uma chamada de API para o serviço 'products' para cada item
                product_response = requests.get(f'http://products:5001/products/{item.product_id}')
                product_name = "Produto Desconhecido"
                if product_response.status_code == 200:
                    product_data = product_response.json()
                    product_name = product_data.get('name', 'Nome não encontrado')

                items_data.append({
                    'product_name': product_name,
                    'quantity': item.quantity,
                    'price': item.price
                })
            except requests.exceptions.RequestException as e:
                print(f"ERRO ao buscar produto {item.product_id} para o pedido #{order.id}: {e}")
                # Adiciona o item mesmo com erro para não quebrar a visualização do pedido
                items_data.append({
                    'product_name': 'Erro ao carregar produto',
                    'quantity': item.quantity,
                    'price': item.price
                })
                
        result.append({
            'id': order.id,
            'total': order.total,
            'items': items_data
        })

    return jsonify(result)