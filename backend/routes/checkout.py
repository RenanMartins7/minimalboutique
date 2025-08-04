from flask import Blueprint, jsonify, session
from models import CartItem, Order
from database import db


checkout_bp = Blueprint('checkout', __name__, url_prefix = '/checkout')

@checkout_bp.route('/', methods = ['POST'])
def checkout():

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error', 'Faça o login para finalizar a sua compra'})
    
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return jsonify({"error":"Carrinho Vazio"}), 400

    total = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(user_id=user_id, total=total)
    db.session.add(order)

    for item in cart_items:
        db.session.delete(item)
    
    db.session.commit()

    return jsonify({"message": "Compra finalizada", "total": total}), 200


# from flask import Blueprint, jsonify

# checkout_bp = Blueprint('checkout', __name__, url_prefix='/checkout')

# @checkout_bp.route('/', methods=['POST'])
# def checkout():
#     return jsonify({"message": "Pedido realizado com sucesso"})

