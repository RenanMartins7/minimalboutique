from flask import Blueprint, jsonify, request
from models import Order, OrderItem
from database import db
import requests

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

# Endpoint de criação permanece o mesmo
@orders_bp.route('/', methods=['POST'])
def create_order():
    data = request.json
    user_id = data.get('user_id')
    total = data.get('total')
    items = data.get('items')

    if not all([user_id, total, items]):
        return jsonify({'error': 'Dados incompletos para criar o pedido'}), 400

    order = Order(user_id=user_id, total=total)
    db.session.add(order)
    db.session.flush() 

    for item_data in items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data['product_id'],
            quantity=item_data['quantity'],
            price=item_data['price']
        )
        db.session.add(order_item)

    db.session.commit()
    return jsonify({'message': 'Pedido criado com sucesso', 'order_id': order.id}), 201

# Endpoint de busca modificado
@orders_bp.route('/', methods=['GET'])
def get_orders():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id é obrigatório'}), 400

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()
    result = []

    for order in orders:
        items_data = []
        for item in order.items:
            try:
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
                items_data.append({'product_name': 'Erro ao carregar produto', 'quantity': item.quantity, 'price': item.price})
                
        result.append({'id': order.id, 'total': order.total, 'items': items_data})

    return jsonify(result)