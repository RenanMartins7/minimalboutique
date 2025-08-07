from flask import Blueprint, jsonify, session
from models import Order
from database import db

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
                items_data.append({
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price
                })
            except Exception as e:
                print(f'Erro ao processar item do pedido #{order.id}:', e)
        result.append({
            'id': order.id,
            'total': order.total,
            'items': items_data
        })

    return jsonify(result)