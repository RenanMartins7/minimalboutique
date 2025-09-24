from flask import Blueprint, jsonify, request
from models import Order, OrderItem
from database import db
import requests
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

# Endpoint de criação permanece o mesmo
@orders_bp.route('/', methods=['POST'])
def create_order():

    span = trace.get_current_span()

    data = request.json
    user_id = data.get('user_id')
    total = data.get('total')
    items = data.get('items')

    if not all([user_id, total, items]):
        return jsonify({'error': 'Dados incompletos para criar o pedido'}), 400
    
    span.set_attribute("user.id", user_id)
    span.set_attribute("total", total)
    span.set_attribute("number.of.items", len(items))

    order = Order(user_id=user_id, total=total)
    db.session.add(order)
    db.session.flush() 
    span.set_attribute("order.id", order.id)

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

    span = trace.get_current_span()

    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id é obrigatório'}), 400
    span.set_attribute("user.id", user_id)

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()
    span.set_attribute("number.of.orders", len(orders))
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
                
        result.append({'id': order.id, 'total': order.total, 'status':order.status, 'items': items_data})

    return jsonify(result)

@orders_bp.route('/<int:order_id>/confirm_payment', methods=['POST'])
def confirm_payment(order_id):
    span = trace.get_current_span()

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error":"Pedido não encontrado"}), 404
    span.set_attribute("order.id", order.id)
    
    order.status = 'paid'
    span.set_attribute("payment.status", "paid")
    db.session.commit()

    return jsonify({"message":"Pagamento do pedido confirmado com sucesso"}), 200

@orders_bp.route('/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    span = trace.get_current_span()
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
    span.set_attribute("order.id", order.id)
    
    if order.status != 'pending':
        return jsonify({"error": "Apenas pedidos pendentes podem ser cancelados"}), 400
    
    for item in order.items:
        try:
            requests.post(f"http://products:5001/products/{item.product_id}/release", json={'quantity' : item.quantity})
        except requests.exceptions.RequestException as e:
            print(f"ERRO CRÍTICO: Falha ao liberar estoque para product_id {item.product_id}. Detalhes: {e}")
    
    db.session.delete(order)
    db.session.commit()

    return jsonify({"message": "Pedido cancelado com sucesso"}), 200
